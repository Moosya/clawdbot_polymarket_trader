#!/usr/bin/env python3
"""
Check resolved markets and update signal outcomes
Calculates signal accuracy and edge
"""
import sqlite3
import sys
import requests
import time
from pathlib import Path
from datetime import datetime

# Detect base directory and database location
if Path("/opt/polymarket/data/trading.db").exists():
    DB_PATH = Path("/opt/polymarket/data/trading.db")
    BASE_DIR = Path("/opt/polymarket")
elif Path("/workspace/polymarket_runtime/data/trading.db").exists():
    DB_PATH = Path("/workspace/polymarket_runtime/data/trading.db")
    BASE_DIR = Path("/workspace")
else:
    DB_PATH = Path("/workspace/data/trading.db")
    BASE_DIR = Path("/workspace")
CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

def get_market_outcome(market_slug):
    """
    Fetch market outcome from Polymarket API
    
    Returns:
        dict with keys: resolved, outcome (YES/NO/CANCELLED), final_price
    """
    try:
        # Try CLOB API first
        response = requests.get(f"{CLOB_API}/markets/{market_slug}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Check if market is closed/resolved
            if data.get("closed", False) or data.get("active", True) == False:
                # Get outcome from resolution
                tokens = data.get("tokens", [])
                if tokens:
                    # Find winning token
                    for token in tokens:
                        if token.get("winner", False):
                            outcome = token.get("outcome", "").upper()
                            # Get last price or 1.0 for winner
                            final_price = 1.0 if token.get("winner") else 0.0
                            return {
                                "resolved": True,
                                "outcome": outcome,
                                "final_price": final_price
                            }
                    
                    # If no winner flag, check if market is closed
                    if data.get("closed"):
                        # Market closed but outcome unclear - might be cancelled
                        return {
                            "resolved": True,
                            "outcome": "CANCELLED",
                            "final_price": None
                        }
            
            # Market still active
            return {"resolved": False, "outcome": None, "final_price": None}
        
        # Market not found or error
        return {"resolved": False, "outcome": None, "final_price": None}
        
    except Exception as e:
        print(f"⚠️  Error fetching market {market_slug}: {e}", file=sys.stderr)
        return {"resolved": False, "outcome": None, "final_price": None}

def calculate_signal_correctness(recommendation, outcome, final_price, entry_price):
    """
    Determine if signal was correct based on recommendation and outcome
    
    Returns:
        tuple: (signal_correct: bool, edge: float)
    """
    if outcome == "CANCELLED":
        return None, 0.0
    
    # Parse recommendation
    action, side = recommendation.split("_")  # e.g. BUY_YES -> (BUY, YES)
    
    # Calculate edge (potential profit)
    if action == "BUY":
        if side == "YES":
            # Bought YES - correct if market resolved YES
            correct = (outcome == "YES")
            edge = final_price - entry_price  # profit if bought at entry
        else:  # side == "NO"
            # Bought NO - correct if market resolved NO
            correct = (outcome == "NO")
            # NO token: final_price is 1 - YES_price
            edge = final_price - entry_price
    else:  # action == "SELL"
        # Selling logic (less common in our signals)
        if side == "YES":
            correct = (outcome == "NO")
            edge = entry_price - final_price
        else:
            correct = (outcome == "YES")
            edge = entry_price - final_price
    
    return correct, edge

def update_outcomes():
    """
    Check all pending signals and update outcomes
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all pending signals
        cursor.execute("""
            SELECT signal_id, signal_type, market_slug, recommendation, 
                   entry_price, detected_at
            FROM signal_history 
            WHERE outcome_known = 0
            ORDER BY detected_at DESC
        """)
        
        pending_signals = cursor.fetchall()
        
        if not pending_signals:
            print("✅ No pending signals to check")
            return
        
        print(f"🔍 Checking {len(pending_signals)} pending signal(s)...\n")
        
        updated_count = 0
        
        for signal_id, signal_type, market_slug, recommendation, entry_price, detected_at in pending_signals:
            print(f"Checking signal {signal_id} ({market_slug})...")
            
            # Get market outcome
            outcome_data = get_market_outcome(market_slug)
            
            if outcome_data["resolved"]:
                outcome = outcome_data["outcome"]
                final_price = outcome_data["final_price"]
                
                # Calculate correctness
                signal_correct, edge = calculate_signal_correctness(
                    recommendation, outcome, final_price, entry_price
                )
                
                # Update database
                cursor.execute("""
                    UPDATE signal_history
                    SET outcome_known = 1,
                        outcome_checked_at = ?,
                        market_result = ?,
                        final_price = ?,
                        signal_correct = ?,
                        edge = ?,
                        updated_at = ?
                    WHERE signal_id = ?
                """, (
                    int(time.time()),
                    outcome,
                    final_price,
                    1 if signal_correct else 0 if signal_correct is False else None,
                    edge,
                    int(time.time()),
                    signal_id
                ))
                
                conn.commit()
                updated_count += 1
                
                result_emoji = "✅" if signal_correct else "❌" if signal_correct is False else "⚪"
                print(f"  {result_emoji} Resolved: {outcome} (edge: {edge:+.3f})")
            else:
                print(f"  ⏳ Still pending")
                
                # Update last checked time
                cursor.execute("""
                    UPDATE signal_history
                    SET outcome_checked_at = ?
                    WHERE signal_id = ?
                """, (int(time.time()), signal_id))
                conn.commit()
            
            # Rate limit
            time.sleep(0.5)
        
        conn.close()
        
        print(f"\n✅ Updated {updated_count} resolved signal(s)")
        
    except Exception as e:
        print(f"❌ Error updating outcomes: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_outcomes()

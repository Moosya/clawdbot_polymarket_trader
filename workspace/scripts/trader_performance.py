#!/usr/bin/env python3
"""
Trader Performance Library - Fixed API Integration
Uses slug-based market lookups instead of broken ID approach
"""

import sqlite3
import requests
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

TRADES_DB = '/home/clawdbot/polymarket_runtime/data/trades.db'
POLYMARKET_API = 'https://gamma-api.polymarket.com'

class TraderPerformance:
    """Calculate and track trader profitability"""
    
    def __init__(self, trades_db=TRADES_DB):
        self.trades_db = trades_db
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create cache tables if they don't exist"""
        conn = sqlite3.connect(self.trades_db)
        cur = conn.cursor()
        
        # Market resolutions cache
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_resolutions (
                market_slug TEXT PRIMARY KEY,
                resolved BOOLEAN,
                winning_outcome TEXT,
                winning_outcome_index INTEGER,
                outcome_prices TEXT,
                resolution_date INTEGER,
                last_checked INTEGER
            )
        """)
        
        # Whale stats cache
        cur.execute("""
            CREATE TABLE IF NOT EXISTS whale_stats (
                trader TEXT PRIMARY KEY,
                trade_pnl REAL DEFAULT 0,
                trade_count INTEGER DEFAULT 0,
                trade_wins INTEGER DEFAULT 0,
                resolution_pnl REAL DEFAULT 0,
                resolution_count INTEGER DEFAULT 0,
                resolution_wins INTEGER DEFAULT 0,
                total_volume REAL DEFAULT 0,
                last_updated INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def check_market_resolution(self, market_slug: str, force=False) -> Optional[Dict]:
        """
        Check if market has resolved using slug-based API query (FIXED)
        Returns resolution info or None if not resolved
        """
        conn = sqlite3.connect(self.trades_db)
        cur = conn.cursor()
        
        # Check cache first
        if not force:
            cur.execute("""
                SELECT resolved, winning_outcome, winning_outcome_index, outcome_prices
                FROM market_resolutions
                WHERE market_slug = ? AND last_checked > ?
            """, (market_slug, int((datetime.now() - timedelta(hours=24)).timestamp())))
            
            cached = cur.fetchone()
            if cached:
                conn.close()
                if not cached[0]:
                    return None
                return {
                    'resolved': True,
                    'winning_outcome': cached[1],
                    'winning_outcome_index': cached[2],
                    'outcome_prices': eval(cached[3])
                }
        
        # Query API by slug
        try:
            response = requests.get(
                f"{POLYMARKET_API}/markets",
                params={'slug': market_slug},
                timeout=5
            )
            
            if response.status_code != 200:
                conn.close()
                return None
            
            data = response.json()
            
            if not data or len(data) == 0:
                # Market not found, cache negative
                cur.execute("""
                    INSERT OR REPLACE INTO market_resolutions 
                    (market_slug, resolved, last_checked)
                    VALUES (?, 0, ?)
                """, (market_slug, int(datetime.now().timestamp())))
                conn.commit()
                conn.close()
                return None
            
            market = data[0]  # API returns array
            
            is_closed = market.get('closed', False)
            outcome_prices = eval(market.get('outcomePrices', '[]'))
            
            if not is_closed or len(outcome_prices) < 2:
                # Not resolved yet
                cur.execute("""
                    INSERT OR REPLACE INTO market_resolutions 
                    (market_slug, resolved, last_checked)
                    VALUES (?, 0, ?)
                """, (market_slug, int(datetime.now().timestamp())))
                conn.commit()
                conn.close()
                return None
            
            # Determine winner
            if float(outcome_prices[0]) > 0.98:
                winning_index = 0
            elif float(outcome_prices[1]) > 0.98:
                winning_index = 1
            else:
                # Not clearly resolved
                conn.close()
                return None
            
            winning_outcome = eval(market.get('outcomes', '[]'))[winning_index]
            
            result = {
                'resolved': True,
                'winning_outcome': winning_outcome,
                'winning_outcome_index': winning_index,
                'outcome_prices': outcome_prices
            }
            
            # Cache it
            cur.execute("""
                INSERT OR REPLACE INTO market_resolutions 
                (market_slug, resolved, winning_outcome, winning_outcome_index, 
                 outcome_prices, resolution_date, last_checked)
                VALUES (?, 1, ?, ?, ?, ?, ?)
            """, (market_slug, winning_outcome, winning_index, 
                  str(outcome_prices), int(datetime.now().timestamp()),
                  int(datetime.now().timestamp())))
            
            conn.commit()
            conn.close()
            return result
            
        except Exception as e:
            print(f"Error checking {market_slug}: {e}")
            conn.close()
            return None
    
    def detect_candidate_resolved_markets(self, days_inactive=3) -> List[str]:
        """Find markets that likely resolved"""
        conn = sqlite3.connect(self.trades_db)
        cur = conn.cursor()
        
        cutoff = int((datetime.now() - timedelta(days=days_inactive)).timestamp())
        
        cur.execute("""
            SELECT DISTINCT marketSlug
            FROM trades
            WHERE sizeUsd >= 1000
            AND timestamp < ?
            GROUP BY marketSlug
            HAVING MAX(timestamp) < ?
        """, (cutoff, cutoff))
        
        candidates = [row[0] for row in cur.fetchall()]
        
        # Filter out already cached as resolved
        filtered = []
        for slug in candidates:
            cur.execute("""
                SELECT resolved FROM market_resolutions 
                WHERE market_slug = ? AND resolved = 1
            """, (slug,))
            if not cur.fetchone():
                filtered.append(slug)
        
        conn.close()
        return filtered
    
    def process_resolved_market(self, market_slug: str, resolution: Dict):
        """Calculate P&L for all whales with open positions"""
        conn = sqlite3.connect(self.trades_db)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT trader, outcome, side, price, sizeUsd
            FROM trades
            WHERE marketSlug = ? AND sizeUsd >= 1000
            ORDER BY trader, outcome, timestamp
        """, (market_slug,))
        
        trades = cur.fetchall()
        
        whale_positions = defaultdict(lambda: defaultdict(list))
        for trader, outcome, side, price, size in trades:
            whale_positions[trader][outcome].append({
                'side': side, 'price': price, 'size': size
            })
        
        for trader, outcomes in whale_positions.items():
            for outcome, trades_list in outcomes.items():
                buys = [t for t in trades_list if t['side'] == 'BUY']
                sells = [t for t in trades_list if t['side'] == 'SELL']
                
                matched = min(len(buys), len(sells))
                open_buys = buys[matched:]
                
                for buy in open_buys:
                    if outcome.lower() == resolution['winning_outcome'].lower():
                        pnl = (1.0 - buy['price']) * buy['size']
                        is_win = 1
                    else:
                        pnl = (0.0 - buy['price']) * buy['size']
                        is_win = 0
                    
                    cur.execute("""
                        INSERT INTO whale_stats (trader, resolution_pnl, resolution_count, 
                                                resolution_wins, total_volume, last_updated)
                        VALUES (?, ?, 1, ?, ?, ?)
                        ON CONFLICT(trader) DO UPDATE SET
                            resolution_pnl = resolution_pnl + ?,
                            resolution_count = resolution_count + 1,
                            resolution_wins = resolution_wins + ?,
                            total_volume = total_volume + ?,
                            last_updated = ?
                    """, (trader, pnl, is_win, buy['size'], 
                          int(datetime.now().timestamp()),
                          pnl, is_win, buy['size'],
                          int(datetime.now().timestamp())))
        
        conn.commit()
        conn.close()
    
    def update_resolutions(self, limit=50):
        """Find and process newly resolved markets"""
        print("🔍 Scanning for resolved markets...")
        candidates = self.detect_candidate_resolved_markets()
        
        if not candidates:
            print("   No new candidates found")
            return 0
        
        print(f"   Found {len(candidates)} candidates to check")
        processed = 0
        
        for i, slug in enumerate(candidates[:limit], 1):
            if i % 10 == 0:
                print(f"   Checked {i}/{min(limit, len(candidates))}...")
            
            resolution = self.check_market_resolution(slug)
            if resolution:
                print(f"   ✅ Resolved: {slug}")
                self.process_resolved_market(slug, resolution)
                processed += 1
        
        print(f"✅ Processed {processed} newly resolved markets")
        return processed
    
    def calculate_trade_pnl(self, trader: str) -> Dict:
        """Case #1: Trade P&L from BUY/SELL pairs"""
        conn = sqlite3.connect(self.trades_db)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT marketSlug, outcome, side, price, sizeUsd
            FROM trades WHERE trader = ? AND sizeUsd >= 1000
            ORDER BY marketSlug, outcome, timestamp
        """, (trader,))
        
        trades = cur.fetchall()
        conn.close()
        
        positions = defaultdict(lambda: defaultdict(list))
        for market, outcome, side, price, size in trades:
            positions[market][outcome].append({'side': side, 'price': price, 'size': size})
        
        total_pnl = 0
        closed_trades = 0
        wins = 0
        total_volume = 0
        
        for market, outcomes in positions.items():
            for outcome, trades_list in outcomes.items():
                buys = [t for t in trades_list if t['side'] == 'BUY']
                sells = [t for t in trades_list if t['side'] == 'SELL']
                
                for i in range(min(len(buys), len(sells))):
                    pnl = (sells[i]['price'] - buys[i]['price']) * min(buys[i]['size'], sells[i]['size'])
                    total_pnl += pnl
                    closed_trades += 1
                    total_volume += min(buys[i]['size'], sells[i]['size'])
                    if pnl > 0:
                        wins += 1
        
        return {
            'pnl': round(total_pnl, 2),
            'trades': closed_trades,
            'wins': wins,
            'losses': closed_trades - wins,
            'volume': round(total_volume, 2)
        }
    
    def get_trader_stats(self, trader: str) -> Dict:
        """Get complete stats (Case #1 + cached Case #2)"""
        trade_stats = self.calculate_trade_pnl(trader)
        
        conn = sqlite3.connect(self.trades_db)
        cur = conn.cursor()
        cur.execute("""
            SELECT resolution_pnl, resolution_count, resolution_wins, total_volume
            FROM whale_stats WHERE trader = ?
        """, (trader,))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            res_pnl, res_count, res_wins, res_volume = row
        else:
            res_pnl, res_count, res_wins, res_volume = 0, 0, 0, 0
        
        total_pnl = trade_stats['pnl'] + res_pnl
        total_closed = trade_stats['trades'] + res_count
        total_wins = trade_stats['wins'] + res_wins
        total_volume = trade_stats['volume'] + res_volume
        
        win_rate = total_wins / total_closed if total_closed > 0 else 0
        roi = total_pnl / total_volume if total_volume > 0 else 0
        
        return {
            'trader': trader,
            'total_pnl': round(total_pnl, 2),
            'total_closed': total_closed,
            'total_wins': total_wins,
            'total_losses': total_closed - total_wins,
            'win_rate': round(win_rate, 3),
            'roi': round(roi, 3),
            'total_volume': round(total_volume, 2),
            'trade_pnl': trade_stats['pnl'],
            'trade_count': trade_stats['trades'],
            'resolution_pnl': round(res_pnl, 2),
            'resolution_count': res_count
        }
    
    def get_trader_rankings(self, min_closed: int = 1) -> List[Tuple[str, Dict]]:
        """Get all traders ranked by total P&L"""
        conn = sqlite3.connect(self.trades_db)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT trader FROM trades WHERE sizeUsd >= 1000")
        traders = [row[0] for row in cur.fetchall()]
        conn.close()
        
        rankings = []
        for trader in traders:
            stats = self.get_trader_stats(trader)
            if stats['total_closed'] >= min_closed:
                rankings.append((trader, stats))
        
        rankings.sort(key=lambda x: x[1]['total_pnl'], reverse=True)
        return rankings
    
    def get_whale_weight(self, trader: str) -> float:
        """Get signal boost weight (0.0 to 2.0)"""
        stats = self.get_trader_stats(trader)
        
        if stats['total_closed'] < 3 or stats['total_pnl'] <= 0:
            return 0.0
        
        pnl_weight = min(stats['total_pnl'] / 50000, 2.0)
        winrate_weight = max(0, (stats['win_rate'] - 0.5) * 2)
        roi_weight = min(stats['roi'] * 2, 1.0)
        
        weight = (pnl_weight * 0.5 + winrate_weight * 0.3 + roi_weight * 0.2)
        return round(weight, 2)


if __name__ == '__main__':
    tp = TraderPerformance()
    
    # Test with one known resolved market
    print("🧪 Testing API fix with known resolved market...")
    test_slug = "will-japan-win-the-most-medals-in-the-2026-winter-olympics"
    resolution = tp.check_market_resolution(test_slug, force=True)
    
    if resolution:
        print(f"✅ API WORKING!")
        print(f"   Market: {test_slug}")
        print(f"   Resolved: {resolution['resolved']}")
        print(f"   Winner: {resolution['winning_outcome']}")
        print(f"   Prices: {resolution['outcome_prices']}")
    else:
        print(f"❌ API still broken")
    
    print()
    print("Now running full resolution scan...")
    tp.update_resolutions(limit=10)

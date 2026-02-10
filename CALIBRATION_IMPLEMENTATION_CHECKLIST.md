# Calibration UI - Implementation Checklist

Quick reference for implementing the Superforecaster Calibration panel.

## 🚀 Phase 1: MVP (4 hours)

### Backend Changes

- [ ] **Modify `scripts/calibration-tracker.py`**
  ```python
  # Add JSON output mode
  if '--json' in sys.argv:
      print(json.dumps(get_calibration_json()))
  ```
  
  Add `get_calibration_json()` function that returns:
  ```python
  {
    'status': 'ok' | 'no_data',
    'overall': {
      'brier_score': 0.142,
      'grade': '⭐ GOOD',
      'total_forecasts': 47,
      'win_rate': 0.68,
      'avg_confidence': 82
    },
    'calibration': {...},  # By bucket
    'issues': [...],       # Overconfidence warnings
    'recent_forecasts': [...] # Last 10
  }
  ```

- [ ] **Add API endpoint to `src/web/server.ts`**
  ```typescript
  app.get('/api/calibration', (req, res) => {
    try {
      const { execSync } = require('child_process');
      const output = execSync(
        'python3 /workspace/scripts/calibration-tracker.py --json',
        { encoding: 'utf-8', cwd: '/workspace' }
      );
      res.json(JSON.parse(output));
    } catch (error) {
      console.error('Calibration error:', error);
      res.status(500).json({ error: 'Calibration failed' });
    }
  });
  ```

### Frontend Changes (server.ts HTML section)

- [ ] **Add panel HTML** (after Paper Trading panel)
  ```html
  <div class="section">
    <div class="section-title">
      🧠 Superforecaster Calibration
      <span class="badge" id="cal-badge">?</span>
    </div>
    <div id="calibration-panel">
      <div class="empty">Loading calibration data...</div>
    </div>
  </div>
  ```

- [ ] **Add update function** (in `<script>` section)
  ```javascript
  async function updateCalibration() {
    try {
      const response = await fetch('/api/calibration');
      const data = await response.json();
      
      const panel = document.getElementById('calibration-panel');
      const badge = document.getElementById('cal-badge');
      
      if (data.status === 'no_data') {
        panel.innerHTML = `
          <div class="empty">
            <p>📊 Building calibration history...</p>
            <p style="color: #6b7280; font-size: 0.9em;">
              Need at least 5 closed positions to measure accuracy.
            </p>
          </div>
        `;
        badge.textContent = '0';
        return;
      }
      
      // Update badge
      badge.textContent = data.overall.total_forecasts;
      
      // Determine color
      const gradeColor = data.overall.brier_score < 0.15 ? '#059669' : 
                         data.overall.brier_score < 0.20 ? '#d97706' : '#dc2626';
      
      // Build HTML
      let html = `
        <!-- Hero Stats -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem; padding: 1rem; background: #f9fafb; border-radius: 4px;">
          <div style="text-align: center;">
            <div style="color: #6b7280; font-size: 0.875rem;">Brier Score</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: ${gradeColor};">
              ${data.overall.brier_score.toFixed(3)}
            </div>
            <div style="color: ${gradeColor}; font-size: 0.875rem; font-weight: 600;">
              ${data.overall.grade}
            </div>
          </div>
          <div style="text-align: center;">
            <div style="color: #6b7280; font-size: 0.875rem;">Forecasts</div>
            <div style="font-size: 1.75rem; font-weight: 700;">${data.overall.total_forecasts}</div>
          </div>
          <div style="text-align: center;">
            <div style="color: #6b7280; font-size: 0.875rem;">Win Rate</div>
            <div style="font-size: 1.75rem; font-weight: 700;">${(data.overall.win_rate * 100).toFixed(0)}%</div>
          </div>
          <div style="text-align: center;">
            <div style="color: #6b7280; font-size: 0.875rem;">Avg Confidence</div>
            <div style="font-size: 1.75rem; font-weight: 700;">${data.overall.avg_confidence.toFixed(0)}%</div>
          </div>
        </div>
        
        <!-- Calibration Table -->
        <div style="margin-bottom: 1rem;">
          <h3 style="font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem; color: #4b5563;">
            📊 Calibration by Confidence Level
          </h3>
          <p style="font-size: 0.8em; color: #6b7280; margin-bottom: 8px;">
            Are 75% confidence trades winning 75% of the time?
          </p>
          <table>
            <thead>
              <tr>
                <th>Confidence</th>
                <th>Trades</th>
                <th>Predicted</th>
                <th>Actual</th>
                <th>Error</th>
                <th>Brier</th>
              </tr>
            </thead>
            <tbody>
              ${Object.entries(data.calibration || {})
                .sort((a, b) => Number(a[0]) - Number(b[0]))
                .map(([conf, stats]) => {
                  const wellCal = stats.well_calibrated ? '✅' : '⚠️';
                  const predicted = (stats.predicted_win_rate * 100).toFixed(0);
                  const actual = (stats.actual_win_rate * 100).toFixed(0);
                  const error = (stats.calibration_error * 100).toFixed(0);
                  
                  return \`
                    <tr>
                      <td>\${wellCal} \${conf}%</td>
                      <td>\${stats.trades}</td>
                      <td>\${predicted}%</td>
                      <td style="font-weight: 600;">\${actual}%</td>
                      <td style="color: \${stats.well_calibrated ? '#059669' : '#d97706'}; font-weight: 600;">
                        \${error}pp
                      </td>
                      <td>\${stats.avg_brier_score.toFixed(3)}</td>
                    </tr>
                  \`;
                }).join('')}
            </tbody>
          </table>
        </div>
      `;
      
      // Overconfidence warnings
      if (data.issues && data.issues.length > 0) {
        html += `
          <div style="margin-top: 1rem; padding: 1rem; background: #fed7aa; border-left: 4px solid #d97706; border-radius: 4px;">
            <strong style="color: #92400e;">⚠️  Overconfidence Alert</strong><br>
            ${data.issues.map(issue => `
              <p style="margin: 0.5rem 0; color: #92400e;">
                • <strong>${issue.signal_type}</strong>: 
                Predicting ${issue.avg_confidence.toFixed(0)}% but winning ${issue.actual_win_rate.toFixed(0)}%
                <br>&nbsp;&nbsp;→ ${issue.recommendation}
              </p>
            `).join('')}
          </div>
        `;
      }
      
      panel.innerHTML = html;
      
    } catch (error) {
      console.error('Error updating calibration:', error);
      document.getElementById('calibration-panel').innerHTML = 
        '<div class="empty">⚠️  Error loading calibration data</div>';
    }
  }
  ```

- [ ] **Call in updateData()** (add after existing updates)
  ```javascript
  async function updateData() {
    try {
      // ... existing signal updates ...
      
      // Update calibration (separate call, less frequent)
      updateCalibration();
      
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  }
  ```

### Testing

- [ ] Run `python3 scripts/calibration-tracker.py --json` manually
- [ ] Verify JSON output is valid
- [ ] Test `/api/calibration` endpoint (curl or browser)
- [ ] Check "no data" state displays correctly
- [ ] Test with actual closed positions
- [ ] Verify mobile layout (Chrome DevTools)

### Deployment

```bash
cd /workspace/projects/polymarket
npm run build
pm2 restart polymarket-dashboard
# Visit http://localhost:3000 to verify
```

---

## 📊 Phase 2: Visual Enhancements (3 hours)

### Add Chart.js

- [ ] Install dependency
  ```bash
  cd /workspace/projects/polymarket
  npm install chart.js
  ```

- [ ] Add to HTML `<head>`
  ```html
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  ```

### Calibration Curve Chart

- [ ] Add canvas element
  ```html
  <canvas id="calibration-chart" width="400" height="300"></canvas>
  ```

- [ ] Render scatter plot
  ```javascript
  function renderCalibrationChart(calibration) {
    const ctx = document.getElementById('calibration-chart');
    
    const dataPoints = Object.entries(calibration).map(([conf, stats]) => ({
      x: stats.predicted_win_rate * 100,
      y: stats.actual_win_rate * 100,
      trades: stats.trades,
      calibrated: stats.well_calibrated
    }));
    
    new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Calibration',
          data: dataPoints,
          backgroundColor: dataPoints.map(p => 
            p.calibrated ? '#059669' : '#d97706'
          ),
          pointRadius: 8
        }, {
          label: 'Perfect Calibration',
          data: [{x: 60, y: 60}, {x: 100, y: 100}],
          type: 'line',
          borderColor: '#9ca3af',
          borderDash: [5, 5],
          pointRadius: 0
        }]
      },
      options: {
        scales: {
          x: { title: { display: true, text: 'Predicted Win Rate (%)' }},
          y: { title: { display: true, text: 'Actual Win Rate (%)' }}
        }
      }
    });
  }
  ```

### Historical Trend

- [ ] Add calibration_history table to SQLite
  ```sql
  CREATE TABLE calibration_history (
    date TEXT PRIMARY KEY,
    brier_score REAL,
    total_forecasts INTEGER,
    win_rate REAL
  );
  ```

- [ ] Daily snapshot script
  ```bash
  # scripts/daily-calibration-snapshot.sh
  #!/bin/bash
  python3 /workspace/scripts/save-calibration-snapshot.py
  ```

- [ ] Render trend line
  ```javascript
  // Mini sparkline showing last 7 days
  ```

---

## 🧪 Phase 3: Learning System (8 hours)

### Post-Mortem UI

- [ ] Add modal for editing closed position notes
- [ ] Store learnings in SQLite or markdown files
- [ ] Display in "Recent Learnings" section

### Automated Insights

- [ ] Pattern detection (e.g., "loses money on Fridays")
- [ ] Signal performance over time
- [ ] Market category breakdown

### Alerts

- [ ] Telegram notification when calibration degrades
- [ ] Weekly calibration report
- [ ] Overconfidence warnings

---

## 📝 Documentation Updates

- [ ] Update README.md with calibration section
- [ ] Link from SUPERFORECASTING.md to dashboard
- [ ] Document API endpoints
- [ ] Add screenshots to docs/

---

## ✅ Definition of Done

### MVP is complete when:
- [x] Panel displays without errors
- [x] Brier score calculates correctly
- [x] "No data" state shows appropriate message
- [x] Overconfidence warnings display
- [x] Mobile responsive (single column)
- [x] Code reviewed + tested
- [x] Deployed to production

### Phase 2 is complete when:
- [ ] Calibration curve chart renders
- [ ] Historical trend shows 7-day history
- [ ] Tooltips work on hover
- [ ] Charts are accessible (ARIA labels)

### Phase 3 is complete when:
- [ ] Post-mortem notes saved per position
- [ ] Daily snapshots running via cron
- [ ] Telegram alerts configured
- [ ] At least 1 signal threshold adjusted based on data

---

## 🐛 Troubleshooting

### Python script fails
- Check Python path: `which python3`
- Test manually: `python3 scripts/calibration-tracker.py --json`
- Check SQLite database exists: `ls /workspace/polymarket_runtime/data/trading.db`

### API returns 500
- Check server logs: `pm2 logs polymarket-dashboard`
- Verify Python output is valid JSON
- Check file permissions

### "No data" never goes away
- Check closed positions: `sqlite3 /workspace/polymarket_runtime/data/trading.db "SELECT COUNT(*) FROM paper_positions WHERE status='closed'"`
- Verify positions have signal_id linked

### Brier score looks wrong
- Spot-check calculation manually
- Verify actual_outcome is 0 or 1 (not other values)
- Check PnL sign (positive = win)

---

## 📞 Need Help?

Ping @clawdbot with:
- Error logs from `pm2 logs`
- Python script output
- Screenshot of broken UI

import * as fs from 'fs';
import * as path from 'path';

export class Logger {
  private logFile: string;
  private logsDir: string;

  constructor(logsDir: string = './logs') {
    this.logsDir = logsDir;
    
    // Create logs directory if it doesn't exist
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }

    this.logFile = path.join(logsDir, 'bot.jsonl');
  }

  private writeLog(level: string, message: string, data?: any) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...(data && { data }),
    };

    // Write to file (JSON Lines format)
    fs.appendFileSync(this.logFile, JSON.stringify(logEntry) + '\n');

    // Also console log
    const emoji = level === 'error' ? '❌' : level === 'warn' ? '⚠️' : level === 'success' ? '✅' : 'ℹ️';
    console.log(`${emoji} ${message}`);
    if (data) {
      console.log(JSON.stringify(data, null, 2));
    }
  }

  info(message: string, data?: any) {
    this.writeLog('info', message, data);
  }

  success(message: string, data?: any) {
    this.writeLog('success', message, data);
  }

  warn(message: string, data?: any) {
    this.writeLog('warn', message, data);
  }

  error(message: string, data?: any) {
    this.writeLog('error', message, data);
  }

  scan(scanNumber: number, stats: {
    tradeableMarkets: number;
    marketsChecked: number;
    opportunities: number;
    duration: number;
    closestMarkets?: any[];
  }) {
    this.writeLog('scan', `Scan #${scanNumber} complete`, {
      scanNumber,
      ...stats,
    });
  }
}

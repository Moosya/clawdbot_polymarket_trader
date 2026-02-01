#!/bin/bash
# Setup cron job for grandma PT reminder (weekdays 7:30 AM EST)

# This sends a Telegram message via Clawdbot
# Cron: 30 12 * * 1-5 (12:30 UTC = 7:30 AM EST)

echo "Setting up grandma PT reminder cron job..."

# Create the reminder script
cat > ~/grandma-reminder.sh << 'EOFSCRIPT'
#!/bin/bash
# Send reminder via Telegram
# This assumes Clawdbot has a CLI or API to send messages

MESSAGE="🔔 Good morning! Time to call grandma about PT appointments."

# Option 1: If clawdbot has a CLI
# clawdbot message send --to telegram:YOUR_CHAT_ID "$MESSAGE"

# Option 2: Create a file that triggers during heartbeat
echo "{\"timestamp\":\"$(date -Iseconds)\",\"message\":\"$MESSAGE\"}" > /home/clawdbot/clawd/reminder-trigger.json

EOFSCRIPT

chmod +x ~/grandma-reminder.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "30 12 * * 1-5 ~/grandma-reminder.sh") | crontab -

echo "✅ Cron job installed!"
echo "Next reminder: Next weekday at 7:30 AM EST"
crontab -l | grep grandma-reminder

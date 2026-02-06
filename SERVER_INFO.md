# Server & Configuration Info

## Server Details
- **IP:** 174.138.55.80
- **Hostname:** openclaw124onubuntu-s-2vcpu-4gb-120gb-intel-nyc3-01
- **OS:** Ubuntu 24.04.3 LTS
- **Location:** DigitalOcean NYC3

## Clawdbot Configuration
- **Main config:** `/opt/clawdbot.env`
- **User config:** `/home/clawdbot/.clawdbot/clawdbot.json`
- **Gateway Token:** 29620252814f917c83ca4175b081a075b8b6259223d129d8de342a29c7518790
- **Dashboard URL:** https://174.138.55.80?token=29620252814f917c83ca4175b081a075b8b6259223d129d8de342a29c7518790

## Useful Commands
```bash
# Configuration
clawdbot config get <path>    # Get config value
clawdbot config set <path> <value>  # Set config value
clawdbot config unset <path>  # Remove config value

# Service Management
systemctl restart clawdbot
systemctl status clawdbot
journalctl -u clawdbot -f

# Helper Scripts
/opt/restart-clawdbot.sh
/opt/status-clawdbot.sh
/opt/update-clawdbot.sh
/opt/clawdbot-cli.sh
/opt/clawdbot-tui.sh
```

## Email Account (Krabby)
- **Email:** dreis.assistant@gmail.com
- **App Password:** dfjn oaaq pqup opjm
- **Purpose:** Dedicated email for Krabby to send/receive emails

## SSH Access
```bash
ssh root@174.138.55.80
# Or with port forwarding for local dashboard access:
ssh -L 3000:localhost:3000 root@174.138.55.80
```

## Projects
- **Polymarket Bot:** `/root/clawdbot_polymarket_trader`

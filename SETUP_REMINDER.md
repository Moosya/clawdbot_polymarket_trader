# Setup Grandma PT Reminder

## Using Clawdbot Cron

Run these commands on the droplet:

### 1. Telegram Reminder
```bash
clawdbot cron add \
  --schedule "30 12 * * 1-5" \
  --task "Send Telegram message: '🔔 Good morning! Reminder to call Maria (grandma) about her Rutherford Physical Therapy appointment. Phone: (201) 636-2256. Appointments are typically at 8:30 AM EST.'" \
  --label "grandma-pt-telegram"
```

### 2. Email Reminder
```bash
clawdbot cron add \
  --schedule "30 12 * * 1-5" \
  --task "Send email to stiles.mesas_3r@icloud.com with subject 'Maria PT Reminder' and message: '🔔 Good morning! Reminder to call Maria (grandma) about her Rutherford Physical Therapy appointment. Phone: (201) 636-2256. Appointments are typically at 8:30 AM EST.'" \
  --label "grandma-pt-email"
```

**Schedule:** Every weekday (Mon-Fri) at 7:30 AM EST (12:30 UTC)

**Destinations:**
- 📱 Telegram
- 📧 stiles.mesas_3r@icloud.com

## Verify

```bash
clawdbot cron list
```

## Remove (if needed)

```bash
clawdbot cron remove grandma-pt-telegram
clawdbot cron remove grandma-pt-email
```

---

**Status:** Ready to set up (run the commands above on the droplet)

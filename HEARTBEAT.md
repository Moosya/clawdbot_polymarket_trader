# HEARTBEAT.md

## Active Tasks

### Test Reminders (Temporary)
- Check `TEST_REMINDERS.json` for pending reminders
- Send to Telegram + Email when trigger time is reached
- Mark as "sent" after delivery

### Maria PT Reminders (Production)
- Check `REMINDERS.md` 
- Weekdays at 7:30 AM EST: Send Maria PT appointment reminder
- Telegram + Email to stiles.mesas_3r@icloud.com

### Skill Discovery (Daily)
- Check ClawdHub/MoltDirectory/crustipedia.com for new useful skills
- Look for skills relevant to current projects (trading, automation, data analysis)
- Alert Andrei if something interesting appears
- Track last check in `memory/skill-discovery-log.md`

### ClawdHub Skills TODO (Weekly Check)
- Review `TODO_CLAWDHUB_SKILLS.md` 
- Remind Andrei about pending skill installations (~every 3-5 days)
- Priority: Security tools first (prompt-guard, dont-hack-me)

### DigitalOcean SMTP Ticket (Active)
- Monitor: https://cloudsupport.digitalocean.com/s/case-detail?recordId=500QP00001GhXFBYA3
- Check every few heartbeats (3-4 times per day)
- Looking for: Approval to enable outbound SMTP ports (25, 465, 587)
- Alert Andrei when status changes
- Once approved: Update Himalaya config and test email sending

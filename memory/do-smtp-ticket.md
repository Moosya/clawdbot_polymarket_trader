# DigitalOcean SMTP Ticket Tracking

**Ticket URL:** https://cloudsupport.digitalocean.com/s/case-detail?recordId=500QP00001GhXFBYA3

**Submitted:** 2026-02-06 ~01:25 UTC

**Request:** Enable outbound SMTP ports (25, 465, 587) for droplet 174.138.55.80

**Reason:** Personal AI assistant needs to send reminder emails via Gmail SMTP

**Status History:**
- 2026-02-06 01:28 UTC - Ticket submitted, monitoring started

**Next Steps When Approved:**
1. Test SMTP connection: `telnet smtp.gmail.com 587`
2. Update Himalaya config if needed (currently set for port 465)
3. Send test email to stiles.mesas_3r@icloud.com
4. Update Maria PT reminder system to use email

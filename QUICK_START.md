# Quick Start Guide
## SmartLead Campaign Lead Tracker - Google Sheets Integration

---

## ✅ Setup Complete!

The tracker has been configured with:
- **SmartLead API Key:** Configured ✓
- **Google Sheet ID:** `1vVAhwz7-V8WRON7Are0kMLMwTHO1OTaHv7P8c0fLEyo` ✓
- **Google Credentials:** `google_credentials.json` ✓
- **Cron Schedule:** Daily at 11:30 AM IST (06:00 UTC) ✓

---

## 🚀 Quick Commands

### Install Dependencies
```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
pip3 install -r requirements.txt
```

### Test Script Manually
```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
python3 smartlead_campaign_lead_tracker.py
```

### Run with Helper Script
```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
./run_tracker.sh
```

### Set Up Cron Job
```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
./setup_cron.sh
```

### Check Cron Job Status
```bash
crontab -l
```

### View Logs
```bash
# Today's cron log
tail -f logs/cron_$(date +%Y%m%d).log

# All logs
ls -lh logs/
```

---

## 📊 Google Sheet

**Sheet URL:** https://docs.google.com/spreadsheets/d/1vVAhwz7-V8WRON7Are0kMLMwTHO1OTaHv7P8c0fLEyo/edit

**Service Account Email:** `gsheets-vps-db@hyperke-zenith.iam.gserviceaccount.com`

**Important:** Ensure the service account has **Editor** access to the sheet.

---

## 📝 What the Script Does

1. Fetches all active campaigns from SmartLead API
2. Counts leads by status (STARTED, INPROGRESS, COMPLETED, etc.)
3. Groups data by client
4. Updates Google Sheet with:
   - Campaign details
   - Lead counts by status
   - Client information
   - Timestamp

**Runs:** Daily at 11:30 AM IST (06:00 UTC)

---

## 🔍 Troubleshooting

### Script fails with "Permission denied"
- Check service account has Editor access to Google Sheet
- Verify `google_credentials.json` exists and has 600 permissions

### Script fails with "Sheet not found"
- Verify Sheet ID is correct
- Check sheet exists and is accessible

### Cron job not running
- Check cron service: `systemctl status cron`
- View cron logs: `grep CRON /var/log/syslog`
- Verify cron job: `crontab -l`

### Dependencies missing
```bash
pip3 install -r requirements.txt
```

---

## 📚 Documentation

- **Full Setup Guide:** `GOOGLE_SHEETS_SETUP.md`
- **Script:** `smartlead_campaign_lead_tracker.py`
- **Cron Setup:** `setup_cron.sh`
- **Run Script:** `run_tracker.sh`

---

## 🔐 Security Notes

- API key is embedded in script (as requested)
- Credentials file has 600 permissions (owner read/write only)
- Never commit credentials to version control
- Service account has Editor access (required for writing)

---

## ✨ Next Steps

1. **Test the script:** Run `python3 smartlead_campaign_lead_tracker.py`
2. **Verify Google Sheet:** Check that data appears correctly
3. **Set up cron:** Run `./setup_cron.sh`
4. **Monitor logs:** Check `logs/` directory daily

---

**Ready to go!** The tracker will automatically update your Google Sheet every day at 11:30 AM IST.

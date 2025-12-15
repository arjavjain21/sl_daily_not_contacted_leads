# Google Sheets Setup Guide
## SmartLead Campaign Lead Tracker

This guide walks you through setting up the SmartLead Campaign Lead Tracker to update a Google Sheet daily via cron job.

---

## Overview

The tracker fetches all active SmartLead campaigns, counts leads by status, and updates a Google Sheet daily at **11:30 AM IST (06:00 UTC)**. The sheet is view-only for account managers, with the service account having editor access.

---

## Prerequisites

- Python 3.7 or higher
- Google Cloud Project with Google Sheets API enabled
- Google Service Account with credentials JSON file
- SmartLead API key
- Google Sheet created and shared with service account

---

## Step 1: Google Cloud Project Setup

### 1.1 Create or Select a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID (e.g., `hyperke-zenith`)

### 1.2 Enable Google Sheets API

1. Navigate to **APIs & Services** > **Library**
2. Search for "Google Sheets API"
3. Click on it and click **Enable**

---

## Step 2: Create Service Account

### 2.1 Create Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Enter a name (e.g., `gsheets-vps-db`)
4. Click **Create and Continue**
5. Skip role assignment (optional)
6. Click **Done**

### 2.2 Generate Credentials JSON

1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key** > **Create New Key**
4. Select **JSON** format
5. Click **Create** - the JSON file will download automatically
6. Save this file securely (it contains private keys)

**Note:** The credentials JSON file has already been saved as `google_credentials.json` in the script directory.

---

## Step 3: Create Google Sheet

### 3.1 Create New Sheet

1. Go to [Google Sheets](https://sheets.google.com/)
2. Create a new blank spreadsheet
3. Name it appropriately (e.g., "SmartLead Campaign Tracker")

### 3.2 Get Sheet ID

The Sheet ID is in the URL:
```
https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit
```

For example, if your URL is:
```
https://docs.google.com/spreadsheets/d/1vVAhwz7-V8WRON7Are0kMLMwTHO1OTaHv7P8c0fLEyo/edit
```

Then your Sheet ID is: `1vVAhwz7-V8WRON7Are0kMLMwTHO1OTaHv7P8c0fLEyo`

### 3.3 Share Sheet with Service Account

1. Click **Share** button in the top right
2. Enter the service account email (found in credentials JSON as `client_email`)
   - Example: `gsheets-vps-db@hyperke-zenith.iam.gserviceaccount.com`
3. Give it **Editor** access (required for writing data)
4. Uncheck "Notify people" (service accounts don't need notifications)
5. Click **Share**

**Important:** The service account must have **Editor** access, not just Viewer access.

---

## Step 4: Configure the Script

### 4.1 Update Configuration in Script

The script has been pre-configured with:
- ✅ SmartLead API key: `2fbf4f7d-44af-4ff1-8e25-5655f5483fd0_94zyakr`
- ✅ Google Sheet ID: `1vVAhwz7-V8WRON7Are0kMLMwTHO1OTaHv7P8c0fLEyo`
- ✅ Google credentials file: `google_credentials.json`

If you need to change these, edit `smartlead_campaign_lead_tracker.py`:

```python
# SmartLead API Configuration
API_KEY = "your_api_key_here"

# Google Sheets Configuration
GOOGLE_SHEET_ID = "your_sheet_id_here"

# Google Service Account Credentials
GOOGLE_CREDENTIALS_FILE = "google_credentials.json"
```

### 4.2 Verify Credentials File

Ensure `google_credentials.json` exists in the script directory and has correct permissions:

```bash
ls -l google_credentials.json
# Should show: -rw------- (600 permissions)
```

If permissions are incorrect:
```bash
chmod 600 google_credentials.json
```

---

## Step 5: Install Dependencies

Install required Python packages:

```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
pip3 install -r requirements.txt
```

This installs:
- `requests` - For SmartLead API calls
- `google-api-python-client` - For Google Sheets API
- `google-auth` - For Google authentication
- `google-auth-httplib2` - HTTP transport for Google auth

---

## Step 6: Test the Script

### 6.1 Manual Test

Run the script manually to verify everything works:

```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
python3 smartlead_campaign_lead_tracker.py
```

**Expected output:**
- Script fetches campaigns from SmartLead API
- Processes lead counts
- Updates Google Sheet
- Prints summary statistics

**Check Google Sheet:**
- Open your Google Sheet
- Verify data appears correctly
- Headers should be bold and frozen
- Columns should auto-resize

### 6.2 Troubleshooting

**Error: "Permission denied"**
- Ensure service account has Editor access to the sheet
- Verify service account email matches the one in credentials JSON

**Error: "Sheet not found"**
- Verify Sheet ID is correct
- Check that the sheet exists and is accessible

**Error: "Google credentials not found"**
- Ensure `google_credentials.json` exists in script directory
- Check file permissions (should be 600)

**Error: "SmartLead API key not configured"**
- Verify API_KEY is set in the script
- Test API key manually with SmartLead API

---

## Step 7: Set Up Cron Job

### 7.1 Run Setup Script

The `setup_cron.sh` script automates cron job setup:

```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
./setup_cron.sh
```

This will:
- Create a cron job for 11:30 AM IST (06:00 UTC) daily
- Set up logging to `logs/cron_YYYYMMDD.log`
- Configure proper working directory

### 7.2 Manual Cron Setup (Alternative)

If you prefer to set up cron manually:

```bash
crontab -e
```

Add this line:
```cron
0 6 * * * cd /home/ubuntu/sl_daily_not_contacted_leads && /usr/bin/python3 smartlead_campaign_lead_tracker.py >> logs/cron_$(date +\%Y\%m\%d).log 2>&1
```

**Cron Schedule Explanation:**
- `0 6 * * *` = Daily at 06:00 UTC
- 11:30 AM IST = 06:00 UTC (IST is UTC+5:30)

### 7.3 Verify Cron Job

Check if cron job is set up:

```bash
crontab -l
```

You should see the cron job listed.

### 7.4 Test Cron Job

Test the cron job by running it manually:

```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
/usr/bin/python3 smartlead_campaign_lead_tracker.py
```

---

## Step 8: Monitor and Maintain

### 8.1 Check Logs

Logs are saved to:
- **Cron logs:** `logs/cron_YYYYMMDD.log`
- **Script logs:** `smartlead_tracker_YYYYMMDD_HHMMSS.log`

View recent logs:
```bash
tail -f logs/cron_$(date +%Y%m%d).log
```

### 8.2 Verify Daily Updates

1. Check Google Sheet daily after 11:30 AM IST
2. Verify data is updated with latest campaign information
3. Check logs for any errors

### 8.3 Remove Cron Job (if needed)

To remove the cron job:

```bash
crontab -e
# Delete the line with smartlead_campaign_lead_tracker.py
```

Or use:
```bash
crontab -l | grep -v smartlead_campaign_lead_tracker.py | crontab
```

---

## Google Sheet Structure

The sheet contains the following columns:

1. **Campaign ID** - SmartLead campaign ID
2. **Campaign Name** - Campaign name
3. **Client ID** - Client ID
4. **Client Name** - Client name
5. **Client Email** - Client email address
6. **Client Company** - Client company name
7. **Campaign Status** - Campaign status (ACTIVE, etc.)
8. **Total Leads** - Total number of leads
9. **Not Yet Contacted (STARTED)** - Leads not yet contacted
10. **Already Contacted** - Leads already contacted
11. **In Progress** - Leads in progress
12. **Completed** - Completed leads
13. **Paused** - Paused leads
14. **Stopped** - Stopped leads
15. **Blocked** - Blocked leads
16. **Fetch Timestamp** - When data was fetched
17. **Error** - Any errors encountered

**Sheet Features:**
- Header row is bold and frozen
- Columns auto-resize
- Data is replaced daily (not appended)
- Sheet is view-only for account managers

---

## Security Considerations

1. **API Key Storage:** API key is embedded in script (as requested). For production, consider using environment variables or secure vaults.

2. **Credentials File:** 
   - Stored as `google_credentials.json` with 600 permissions (owner read/write only)
   - Contains private keys - keep secure
   - Never commit to version control

3. **Sheet Permissions:**
   - Service account: Editor access (required for writing)
   - Account managers: Viewer access (read-only)

4. **Log Files:**
   - Logs don't contain sensitive data
   - Rotate logs periodically to save disk space

---

## Troubleshooting

### Common Issues

**Issue: Script runs but sheet is not updated**
- Check service account has Editor access
- Verify Sheet ID is correct
- Check logs for API errors

**Issue: "Rate limit exceeded"**
- Google Sheets API has rate limits
- Script handles this automatically with retries
- If persistent, reduce MAX_WORKERS in script

**Issue: Cron job not running**
- Check cron service is running: `systemctl status cron`
- Verify cron job syntax: `crontab -l`
- Check cron logs: `grep CRON /var/log/syslog`

**Issue: Python not found in cron**
- Use full path to Python: `/usr/bin/python3`
- Or set PATH in cron job

---

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review script output for error messages
3. Verify all prerequisites are met
4. Test script manually before relying on cron

---

## Summary

✅ **Completed Setup:**
- Google Cloud Project configured
- Google Sheets API enabled
- Service Account created
- Credentials JSON saved
- Google Sheet created and shared
- Script configured with API keys
- Dependencies installed
- Cron job set up for 11:30 AM IST daily

The tracker will now automatically update your Google Sheet every day at 11:30 AM IST with the latest campaign and lead status data.

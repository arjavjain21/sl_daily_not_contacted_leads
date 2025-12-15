# SmartLead Campaign Lead Tracker

A production-ready Python script that fetches all active SmartLead campaigns, tracks lead statuses, and exports detailed reports grouped by client.

## 🎯 What It Does

1. **Fetches all campaigns** from your SmartLead account
2. **Filters for ACTIVE campaigns** only
3. **Fetches all client details** for enrichment
4. **Groups campaigns by client** (name and ID)
5. **Counts leads by status** for each campaign:
   - **Not Yet Contacted** (STARTED status) - leads that haven't been reached out to
   - **Already Contacted** - all other statuses (INPROGRESS, COMPLETED, etc.)
6. **Exports to CSV** with comprehensive details
7. **Prints summary report** with top clients

## 📊 Output

### CSV File Structure

The script generates a CSV file with the following columns:

| Column | Description |
|--------|-------------|
| Campaign ID | SmartLead campaign ID |
| Campaign Name | Full campaign name |
| Client ID | Client ID |
| Client Name | Client name |
| Client Email | Client email address |
| Client Company | Client company name |
| Campaign Status | Campaign status (ACTIVE) |
| Total Leads | Total number of leads |
| Not Yet Contacted (STARTED) | Leads with STARTED status |
| Already Contacted | Leads with any other status |
| In Progress | Leads currently being contacted |
| Completed | Leads who finished the sequence |
| Paused | Manually paused leads |
| Stopped | Stopped leads |
| Blocked | Blocked leads |
| Fetch Timestamp | When the data was fetched |
| Error | Any errors encountered (if applicable) |

### Example Output

```csv
Campaign ID,Campaign Name,Client ID,Client Name,Total Leads,Not Yet Contacted,Already Contacted
2758819,"12/10 | ECA | Refreshed Sequence",1885,"ECA",1706,286,1420
```

## 🚀 Setup

### Prerequisites

- Python 3.7+
- `requests` library

### Installation

1. **Clone or download the script:**
   ```bash
   curl -O https://your-repo/smartlead_campaign_lead_tracker.py
   ```

2. **Install dependencies:**
   ```bash
   pip install requests
   ```

3. **Set your SmartLead API key:**
   ```bash
   export SMARTLEAD_API_KEY='your_api_key_here'
   ```

   Or add to your `.bashrc` / `.zshrc`:
   ```bash
   echo 'export SMARTLEAD_API_KEY="your_api_key_here"' >> ~/.bashrc
   source ~/.bashrc
   ```

## 📖 Usage

### Basic Usage

```bash
python smartlead_campaign_lead_tracker.py
```

### What Happens

1. Script connects to SmartLead API
2. Fetches all campaigns and filters for ACTIVE
3. Fetches client details
4. Processes campaigns in parallel (20 workers by default)
5. Generates CSV report in `smartlead_reports/` directory
6. Prints summary to console

### Output Location

```
smartlead_reports/
└── campaign_lead_status_20241214_153045.csv
```

Log file:
```
smartlead_tracker_20241214_153045.log
```

## ⚙️ Configuration

You can modify these settings in the script:

```python
# Performance settings
MAX_WORKERS = 20  # Parallel threads for fetching campaign leads
BATCH_SIZE = 100  # Number of leads to fetch per request
REQUEST_TIMEOUT = 30  # Seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5  # Seconds

# Output settings
OUTPUT_DIR = "smartlead_reports"
```

## 📈 Performance

- **Parallel Processing**: Uses ThreadPoolExecutor with 20 workers by default
- **Batch Fetching**: Fetches leads in batches of 100
- **Retry Logic**: Automatic retry on 429, 500, 502, 503, 504 errors
- **Efficient Counting**: Fetches all leads once per campaign and counts locally

### Expected Execution Time

For **90 active campaigns** with ~1,500 leads each:
- **~3-5 minutes** with default settings (20 workers)
- **~10-15 minutes** with conservative settings (5 workers)

## 🔍 Example Console Output

```
2024-12-14 15:30:45 - INFO - ================================================================================
2024-12-14 15:30:45 - INFO - SmartLead Campaign Lead Tracker - Starting
2024-12-14 15:30:45 - INFO - ================================================================================
2024-12-14 15:30:45 - INFO - Fetching all campaigns...
2024-12-14 15:30:47 - INFO - ✓ Fetched 150 total campaigns
2024-12-14 15:30:47 - INFO - ✓ Filtered to 90 ACTIVE campaigns
2024-12-14 15:30:47 - INFO - Fetching all clients...
2024-12-14 15:30:48 - INFO - ✓ Fetched 25 clients
2024-12-14 15:30:48 - INFO - Processing 90 campaigns with 20 parallel workers...
2024-12-14 15:31:00 - INFO - Progress: 10/90 campaigns processed
2024-12-14 15:31:15 - INFO - Progress: 20/90 campaigns processed
...
2024-12-14 15:33:30 - INFO - ✓ Completed processing 90 campaigns
2024-12-14 15:33:30 - INFO - Exporting data to CSV: smartlead_reports/campaign_lead_status_20241214_153045.csv
2024-12-14 15:33:31 - INFO - ✓ CSV export complete

================================================================================
SUMMARY REPORT
================================================================================

Total Active Campaigns: 90
Total Clients: 25

Total Leads: 135,420
  ├─ Not Yet Contacted (STARTED): 25,786 (19.0%)
  └─ Already Contacted: 109,634 (81.0%)

--------------------------------------------------------------------------------
TOP 10 CLIENTS BY NOT YET CONTACTED LEADS
--------------------------------------------------------------------------------

ECA
  Campaigns: 8
  Total Leads: 12,450
  Not Yet Contacted: 3,890
  Already Contacted: 8,560

270M Marketing Agency
  Campaigns: 5
  Total Leads: 8,900
  Not Yet Contacted: 2,340
  Already Contacted: 6,560

...

2024-12-14 15:33:31 - INFO - ✓ Total execution time: 166.23 seconds
2024-12-14 15:33:31 - INFO - ✓ Report saved to: smartlead_reports/campaign_lead_status_20241214_153045.csv
```

## 🛠 Troubleshooting

### Error: API Key Not Set

```
ERROR: SMARTLEAD_API_KEY environment variable not set
```

**Solution:**
```bash
export SMARTLEAD_API_KEY='your_api_key_here'
```

### Error: Requests Library Not Installed

```
ERROR: 'requests' library not installed.
```

**Solution:**
```bash
pip install requests
```

### HTTP 429 - Rate Limit Error

The script automatically retries with exponential backoff. If you consistently hit rate limits:

1. Reduce `MAX_WORKERS` to 10 or 5
2. Increase `RETRY_BACKOFF` to 1.0 or 2.0

### Timeout Errors

If you see timeout errors:

1. Increase `REQUEST_TIMEOUT` to 60 or 90
2. Check your internet connection
3. Reduce `MAX_WORKERS` to reduce concurrent requests

### Memory Issues

For very large accounts (1000+ campaigns):

1. Reduce `MAX_WORKERS` to 10
2. Reduce `BATCH_SIZE` to 50
3. Process in batches (modify script to process N campaigns at a time)

## 🔒 Security Notes

- **Never commit your API key** to version control
- Store API key in environment variables or secret management system
- The script logs to a file - ensure logs are stored securely
- CSV files contain client data - handle with appropriate security measures

## 📝 Advanced Usage

### Running on a Schedule (Cron)

Add to your crontab to run daily at 9 AM:

```bash
0 9 * * * cd /path/to/script && /usr/bin/python3 smartlead_campaign_lead_tracker.py >> /var/log/smartlead_tracker.log 2>&1
```

### Integration with Other Tools

The CSV output can be:
- Imported into Google Sheets / Excel
- Loaded into a database
- Processed by BI tools (Tableau, Power BI)
- Sent via email (attach CSV)
- Posted to Slack (summary stats)

### Example: Send Summary to Slack

Add this at the end of the `main()` function:

```python
# Send to Slack
import requests

webhook_url = "YOUR_SLACK_WEBHOOK_URL"
summary_text = f"""
*SmartLead Campaign Report*
Total Active Campaigns: {len(campaign_data)}
Total Leads Not Yet Contacted: {sum(d.lead_counts.not_yet_contacted for d in campaign_data):,}
Report: {csv_path}
"""

requests.post(webhook_url, json={"text": summary_text})
```

## 🤝 Support

For issues or questions:
1. Check the log file: `smartlead_tracker_*.log`
2. Review the troubleshooting section
3. Contact Hyperke Automation Team

## 📄 License

Proprietary - Hyperke Automation Team
© 2024 All Rights Reserved

## 🔄 Version History

- **1.0.0** (2024-12-14): Initial release
  - Parallel processing of campaigns
  - CSV export with detailed lead status breakdown
  - Comprehensive error handling and logging
  - Summary report generation

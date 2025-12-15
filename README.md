# SmartLead Daily Not Contacted Leads Tracker

Automated daily tracking system for SmartLead campaign leads that haven't been contacted yet. Fetches campaign data from SmartLead API and updates Google Sheets with daily snapshots.

## Features

- **Daily Automated Tracking**: Runs automatically via cron job at 11:30 AM IST (06:00 UTC)
- **Dual Sheet System**: 
  - **"Yesterday" sheet**: Static sheet overwritten daily with latest data (leftmost position)
  - **Dated sheets**: Historical snapshots named with date format `YYYY/MM/DD` (e.g., `2025/12/14`)
- **Comprehensive Lead Status**: Tracks not yet contacted, in progress, completed, paused, stopped, and blocked leads
- **Client Grouping**: Groups campaigns by client with summary statistics
- **Parallel Processing**: Processes multiple campaigns concurrently for faster execution

## Requirements

- Python 3.7+
- Google Service Account credentials (JSON file)
- SmartLead API key
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd sl_daily_not_contacted_leads
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Set up Google Sheets credentials:
   - Follow instructions in `GOOGLE_SHEETS_SETUP.md`
   - Place `google_credentials.json` in the project directory

4. Configure the script:
   - Update `GOOGLE_SHEET_ID` in `smartlead_campaign_lead_tracker.py` with your Google Sheet ID
   - Update `API_KEY` with your SmartLead API key

## Usage

### Manual Run

```bash
bash run_tracker.sh
```

### Setup Cron Job (Automated Daily Runs)

```bash
bash setup_cron.sh
```

This sets up a cron job to run daily at 11:30 AM IST (06:00 UTC).

### View Cron Jobs

```bash
crontab -l
```

## Project Structure

```
sl_daily_not_contacted_leads/
├── smartlead_campaign_lead_tracker.py  # Main script
├── run_tracker.sh                      # Quick start script
├── setup_cron.sh                       # Cron job setup script
├── requirements.txt                    # Python dependencies
├── google_credentials.json             # Google Service Account credentials (not in repo)
├── GOOGLE_SHEETS_SETUP.md             # Google Sheets setup instructions
├── QUICK_START.md                      # Quick start guide
├── README_SMARTLEAD_TRACKER.md        # Detailed documentation
└── CHANGELOG.md                        # Change log
```

## Google Sheets Output

The script creates/updates two types of sheets:

1. **"Yesterday"** (Index 0 - Leftmost)
   - Static sheet that gets overwritten daily
   - Always shows the most recent data snapshot

2. **Dated Sheets** (Index 1+)
   - Named with date format: `YYYY/MM/DD` (e.g., `2025/12/14`)
   - Historical snapshots preserved for each day
   - Most recent dated sheet appears right after "Yesterday"

### Sheet Columns

- Campaign ID
- Campaign Name
- Client ID
- Client Name
- Client Email
- Client Company
- Campaign Status
- Total Leads
- Not Yet Contacted (STARTED)
- Already Contacted
- In Progress
- Completed
- Paused
- Stopped
- Blocked
- Fetch Timestamp
- Error

## Configuration

### Environment Variables

The script uses hardcoded configuration in `smartlead_campaign_lead_tracker.py`:

- `API_KEY`: SmartLead API key
- `GOOGLE_SHEET_ID`: Google Sheet ID
- `GOOGLE_CREDENTIALS_FILE`: Path to credentials JSON file
- `MAX_WORKERS`: Number of parallel workers (default: 10)
- `BATCH_SIZE`: Leads per API request (default: 100)

## Logging

Logs are written to:
- Console output (stdout)
- Log files: `smartlead_tracker_YYYYMMDD_HHMMSS.log`
- Cron logs: `logs/cron_YYYYMMDD.log` (when run via cron)

## Troubleshooting

See `QUICK_START.md` and `README_SMARTLEAD_TRACKER.md` for detailed troubleshooting guides.

## Security Notes

- **Never commit `google_credentials.json`** to version control
- Keep your SmartLead API key secure
- Ensure `google_credentials.json` has 600 permissions: `chmod 600 google_credentials.json`

## License

Private repository - Internal use only

## Author

Hyperke Automation Team

## Version

2.0.0 - December 2024

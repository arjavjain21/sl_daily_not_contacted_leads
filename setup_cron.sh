#!/bin/bash
#
# SmartLead Campaign Lead Tracker - Cron Job Setup Script
# ========================================================
# Sets up a daily cron job to run at 11:30 AM IST (06:00 UTC)
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/smartlead_campaign_lead_tracker.py"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/cron_$(date +%Y%m%d).log"

echo "============================================================"
echo "SmartLead Campaign Lead Tracker - Cron Job Setup"
echo "============================================================"
echo ""

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ERROR: Script not found at $SCRIPT_PATH"
    exit 1
fi

# Make script executable
chmod +x "$SCRIPT_PATH"
echo "✓ Script is executable"

# Create log directory
mkdir -p "$LOG_DIR"
echo "✓ Log directory created: $LOG_DIR"

# Find Python 3 executable
PYTHON3=$(which python3)
if [ -z "$PYTHON3" ]; then
    echo "ERROR: python3 not found in PATH"
    exit 1
fi
echo "✓ Python 3 found: $PYTHON3"

# Cron job command
# 11:30 AM IST = 06:00 UTC (IST is UTC+5:30)
# Cron format: minute hour day month weekday
CRON_TIME="0 6 * * *"  # 06:00 UTC daily

# Build cron command with logging
CRON_CMD="$CRON_TIME cd $SCRIPT_DIR && $PYTHON3 $SCRIPT_PATH >> $LOG_DIR/cron_\$(date +\\%Y\\%m\\%d).log 2>&1"

# Check if cron job already exists
CRON_JOB_EXISTS=$(crontab -l 2>/dev/null | grep -c "$SCRIPT_PATH" || true)

if [ "$CRON_JOB_EXISTS" -gt 0 ]; then
    echo ""
    echo "WARNING: A cron job for this script already exists!"
    echo ""
    echo "Current cron jobs for this script:"
    crontab -l 2>/dev/null | grep "$SCRIPT_PATH" || true
    echo ""
    read -p "Do you want to replace it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cron job setup cancelled."
        exit 0
    fi
    
    # Remove existing cron job
    crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" | crontab - 2>/dev/null || true
    echo "✓ Removed existing cron job"
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
echo "✓ Cron job added successfully"

echo ""
echo "============================================================"
echo "Cron Job Details"
echo "============================================================"
echo "Schedule: Daily at 11:30 AM IST (06:00 UTC)"
echo "Command: $PYTHON3 $SCRIPT_PATH"
echo "Working Directory: $SCRIPT_DIR"
echo "Logs: $LOG_DIR/cron_YYYYMMDD.log"
echo ""
echo "To view cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove this cron job:"
echo "  crontab -e  # Then delete the line with $SCRIPT_PATH"
echo ""
echo "To test the cron job manually:"
echo "  cd $SCRIPT_DIR && $PYTHON3 $SCRIPT_PATH"
echo ""
echo "============================================================"
echo "✓ Setup complete!"
echo "============================================================"

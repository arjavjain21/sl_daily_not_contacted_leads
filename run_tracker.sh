#!/bin/bash
#
# SmartLead Campaign Lead Tracker - Quick Start Script
# ====================================================
# This script sets up the environment and runs the tracker
# Updates Google Sheet with campaign data
#

set -e  # Exit on error

echo "============================================================"
echo "SmartLead Campaign Lead Tracker - Quick Start"
echo "============================================================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Install Python 3.7+ and try again"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python $PYTHON_VERSION found"

# Check dependencies
echo ""
echo "Checking dependencies..."
MISSING_DEPS=0

if ! python3 -c "import requests" 2>/dev/null; then
    echo "✗ requests library not installed"
    MISSING_DEPS=1
else
    echo "✓ requests library is installed"
fi

if ! python3 -c "import google.oauth2" 2>/dev/null; then
    echo "✗ google-auth library not installed"
    MISSING_DEPS=1
else
    echo "✓ google-auth library is installed"
fi

if ! python3 -c "import googleapiclient" 2>/dev/null; then
    echo "✗ google-api-python-client library not installed"
    MISSING_DEPS=1
else
    echo "✓ google-api-python-client library is installed"
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo "Installing missing dependencies..."
    pip3 install -r requirements.txt
    echo "✓ Dependencies installed"
fi

# Check for Google credentials file
echo ""
echo "Checking Google credentials..."
if [ ! -f "google_credentials.json" ]; then
    echo "✗ ERROR: google_credentials.json not found"
    echo ""
    echo "Please ensure google_credentials.json exists in the script directory."
    echo "See GOOGLE_SHEETS_SETUP.md for setup instructions."
    exit 1
else
    echo "✓ Google credentials file found"
    # Check permissions
    PERMS=$(stat -c "%a" google_credentials.json 2>/dev/null || stat -f "%OLp" google_credentials.json 2>/dev/null)
    if [ "$PERMS" != "600" ]; then
        echo "⚠ WARNING: Credentials file should have 600 permissions"
        echo "Fixing permissions..."
        chmod 600 google_credentials.json
        echo "✓ Permissions fixed"
    fi
fi

# Create output directories
echo ""
echo "Creating output directories..."
mkdir -p smartlead_reports
mkdir -p logs
echo "✓ Output directories ready"

# Run the script
echo ""
echo "============================================================"
echo "Starting SmartLead Campaign Lead Tracker..."
echo "============================================================"
echo ""

python3 smartlead_campaign_lead_tracker.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✓ SUCCESS - Google Sheet updated successfully!"
    echo "============================================================"
    echo ""
    echo "Check your Google Sheet for the updated data."
    echo "Log files are available in the logs/ directory."
    echo ""
else
    echo ""
    echo "============================================================"
    echo "✗ ERROR - Script failed. Check the log file for details."
    echo "============================================================"
    echo ""
    exit 1
fi

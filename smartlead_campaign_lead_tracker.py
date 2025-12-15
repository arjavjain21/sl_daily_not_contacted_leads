#!/usr/bin/env python3
"""
SmartLead Campaign Lead Tracker
================================
Fetches all active campaigns, groups by clients, and tracks lead statuses.
Updates Google Sheet daily with campaign data and lead statuses.

Author: Hyperke Automation Team
Version: 2.0.0
Date: December 14, 2024
"""

import os
import sys
import json
import csv
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, asdict
import logging

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: 'requests' library not installed.")
    print("Install it with: pip install requests")
    sys.exit(1)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Google API libraries not installed.")
    print("Install them with: pip install google-api-python-client google-auth google-auth-httplib2")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

# SmartLead API Configuration
API_KEY = "2fbf4f7d-44af-4ff1-8e25-5655f5483fd0_94zyakr"

BASE_URL = "https://server.smartlead.ai/api/v1"

# Google Sheets Configuration
GOOGLE_SHEET_ID = "1vVAhwz7-V8WRON7Are0kMLMwTHO1OTaHv7P8c0fLEyo"

# Google Service Account Credentials
# Option 1: Path to JSON credentials file
GOOGLE_CREDENTIALS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "google_credentials.json"
)

# Option 2: JSON string (alternative to file path)
# If using JSON string, set GOOGLE_CREDENTIALS_JSON instead of GOOGLE_CREDENTIALS_FILE
GOOGLE_CREDENTIALS_JSON = None  # Set to JSON string if not using file

# Google Sheet Range (where to write data)
GOOGLE_SHEET_RANGE = "Sheet1!A1"  # Start writing from A1

# Performance settings
MAX_WORKERS = 10  # Reduced from 20 to avoid API rate limits
BATCH_SIZE = 100  # Number of leads to fetch per request
REQUEST_TIMEOUT = 30  # Seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # Increased from 0.5 to give API more breathing room

# Output settings (for logging and optional CSV backup)
OUTPUT_DIR = "smartlead_reports"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILENAME = f"campaign_lead_status_{TIMESTAMP}.csv"

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'smartlead_tracker_{TIMESTAMP}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class LeadStatusCount:
    """Lead status counts for a campaign"""
    total_leads: int = 0
    started: int = 0  # Not yet contacted
    inprogress: int = 0
    completed: int = 0
    paused: int = 0
    stopped: int = 0
    blocked: int = 0
    
    @property
    def not_yet_contacted(self) -> int:
        """Leads with STARTED status (haven't been contacted yet)"""
        return self.started
    
    @property
    def already_contacted(self) -> int:
        """Leads that have been contacted (INPROGRESS + COMPLETED + others)"""
        return self.total_leads - self.started


@dataclass
class CampaignData:
    """Campaign data with lead counts"""
    campaign_id: int
    campaign_name: str
    client_id: int
    client_name: str
    client_email: str
    client_company: str
    status: str
    lead_counts: LeadStatusCount
    fetch_timestamp: str
    error: Optional[str] = None


# ============================================================================
# GOOGLE SHEETS CLIENT
# ============================================================================

class GoogleSheetsUpdater:
    """Google Sheets API client for updating campaign data"""
    
    def __init__(self, sheet_id: str, credentials_file: Optional[str] = None, credentials_json: Optional[str] = None):
        """
        Initialize Google Sheets client
        
        Args:
            sheet_id: Google Sheet ID
            credentials_file: Path to service account JSON file
            credentials_json: Service account JSON as string (alternative to file)
        """
        self.sheet_id = sheet_id
        self.service = None
        
        if credentials_json:
            # Load from JSON string
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        elif credentials_file and os.path.exists(credentials_file):
            # Load from file
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        else:
            raise ValueError(
                "Google credentials not found. "
                "Please provide either GOOGLE_CREDENTIALS_FILE or GOOGLE_CREDENTIALS_JSON"
            )
        
        self.service = build('sheets', 'v4', credentials=credentials)
        logger.info("✓ Google Sheets API authenticated successfully")
    
    def get_or_create_dated_sheet(self, date_str: str) -> tuple[str, int]:
        """
        Get or create a sheet with the date name (format: YYYY/MM/DD)
        and move it to index 1 (right after the "Yesterday" sheet at index 0)
        
        Args:
            date_str: Date string in format YYYY/MM/DD (e.g., "2025/12/14")
            
        Returns:
            Tuple of (sheet_name, sheet_id)
        """
        try:
            # Get all sheets
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            sheet_name = date_str
            
            # Check if sheet already exists
            sheet_id = None
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    logger.info(f"✓ Found existing sheet: {sheet_name}")
                    break
            
            # Create sheet if it doesn't exist
            if sheet_id is None:
                requests = [{
                    "addSheet": {
                        "properties": {
                            "title": sheet_name
                        }
                    }
                }]
                
                body = {'requests': requests}
                response = self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body=body
                ).execute()
                
                sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
                logger.info(f"✓ Created new sheet: {sheet_name}")
                
                # Refresh sheets list after creation
                spreadsheet = self.service.spreadsheets().get(
                    spreadsheetId=self.sheet_id
                ).execute()
                sheets = spreadsheet.get('sheets', [])
            
            # Move sheet to index 1 (right after "Yesterday" sheet at index 0)
            # Find current index of the sheet
            current_index = None
            for i, sheet in enumerate(sheets):
                if sheet['properties']['sheetId'] == sheet_id:
                    current_index = i
                    break
            
            if current_index is not None and current_index != 1:
                requests = [{
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "index": 1
                        },
                        "fields": "index"
                    }
                }]
                
                body = {'requests': requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body=body
                ).execute()
                logger.info(f"✓ Moved sheet '{sheet_name}' to index 1 (right after 'Yesterday')")
            elif current_index == 1:
                logger.info(f"✓ Sheet '{sheet_name}' is already at index 1")
            
            return sheet_name, sheet_id
            
        except HttpError as e:
            logger.error(f"Error creating/getting dated sheet: {e}")
            raise
    
    def get_or_create_yesterday_sheet(self) -> tuple[str, int]:
        """
        Get or create the "Yesterday" sheet (static sheet that gets overwritten daily)
        Position it at index 0 (leftmost position)
        
        Returns:
            Tuple of (sheet_name, sheet_id)
        """
        try:
            # Get all sheets
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            sheet_name = "Yesterday"
            
            # Check if sheet already exists
            sheet_id = None
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    logger.info(f"✓ Found existing sheet: {sheet_name}")
                    break
            
            # Create sheet if it doesn't exist
            if sheet_id is None:
                requests = [{
                    "addSheet": {
                        "properties": {
                            "title": sheet_name
                        }
                    }
                }]
                
                body = {'requests': requests}
                response = self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body=body
                ).execute()
                
                sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
                logger.info(f"✓ Created new sheet: {sheet_name}")
                
                # Refresh sheets list after creation
                spreadsheet = self.service.spreadsheets().get(
                    spreadsheetId=self.sheet_id
                ).execute()
                sheets = spreadsheet.get('sheets', [])
            
            # Move sheet to index 0 (leftmost position)
            # Find current index of the sheet
            current_index = None
            for i, sheet in enumerate(sheets):
                if sheet['properties']['sheetId'] == sheet_id:
                    current_index = i
                    break
            
            if current_index is not None and current_index > 0:
                requests = [{
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "index": 0
                        },
                        "fields": "index"
                    }
                }]
                
                body = {'requests': requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body=body
                ).execute()
                logger.info(f"✓ Moved sheet '{sheet_name}' to leftmost position (index 0)")
            elif current_index == 0:
                logger.info(f"✓ Sheet '{sheet_name}' is already at leftmost position")
            
            return sheet_name, sheet_id
            
        except HttpError as e:
            logger.error(f"Error creating/getting Yesterday sheet: {e}")
            raise
    
    def clear_sheet(self, range_name: str = "Sheet1") -> bool:
        """
        Clear all data from the sheet
        
        Args:
            range_name: Sheet name or range to clear
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            logger.info(f"✓ Cleared sheet: {range_name}")
            return True
        except HttpError as e:
            logger.error(f"Error clearing sheet: {e}")
            return False
    
    def update_sheet(self, values: List[List[Any]], range_name: str = "Sheet1!A1", value_input_option: str = "USER_ENTERED") -> bool:
        """
        Update Google Sheet with data
        
        Args:
            values: 2D list of values to write
            range_name: A1 notation range (e.g., "Sheet1!A1")
            value_input_option: "USER_ENTERED" or "RAW"
            
        Returns:
            True if successful, False otherwise
        """
        try:
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            logger.info(f"✓ Updated {updated_cells} cells in Google Sheet")
            return True
            
        except HttpError as e:
            logger.error(f"Error updating Google Sheet: {e}")
            if e.resp.status == 404:
                logger.error(f"Sheet ID {self.sheet_id} not found. Check the Sheet ID and sharing permissions.")
            elif e.resp.status == 403:
                logger.error("Permission denied. Ensure service account has editor access to the sheet.")
            return False
    
    def format_headers(self, sheet_id: int = 0) -> bool:
        """
        Format header row (bold, freeze first row)
        
        Args:
            sheet_id: Sheet ID to format (default: 0 for first sheet)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {
                                    "bold": True
                                },
                                "backgroundColor": {
                                    "red": 0.9,
                                    "green": 0.9,
                                    "blue": 0.9
                                }
                            }
                        },
                        "fields": "userEnteredFormat(textFormat,backgroundColor)"
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {
                                "frozenRowCount": 1
                            }
                        },
                        "fields": "gridProperties.frozenRowCount"
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 17  # 17 columns
                        }
                    }
                }
            ]
            
            body = {
                'requests': requests
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body=body
            ).execute()
            
            logger.info("✓ Formatted header row (bold, frozen, auto-resized)")
            return True
            
        except HttpError as e:
            logger.warning(f"Error formatting headers (non-critical): {e}")
            return False


# ============================================================================
# HTTP SESSION WITH RETRY LOGIC
# ============================================================================

def create_session() -> requests.Session:
    """Create a requests session with retry logic"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


# ============================================================================
# API FUNCTIONS
# ============================================================================

def make_api_request(
    session: requests.Session,
    endpoint: str,
    params: Optional[Dict] = None,
    method: str = "GET"
) -> Optional[Dict]:
    """
    Make an API request with error handling
    
    Args:
        session: Requests session
        endpoint: API endpoint (without base URL)
        params: Query parameters
        method: HTTP method
        
    Returns:
        Response JSON or None if error
    """
    url = f"{BASE_URL}{endpoint}"
    
    if params is None:
        params = {}
    
    params['api_key'] = API_KEY
    
    try:
        response = session.request(
            method=method,
            url=url,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error for {endpoint}: {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout for {endpoint}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {endpoint}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {endpoint}: {e}")
        return None


def fetch_all_campaigns(session: requests.Session) -> List[Dict]:
    """Fetch all campaigns"""
    logger.info("Fetching all campaigns...")
    
    campaigns = make_api_request(session, "/campaigns", params={"include_tags": "true"})
    
    if campaigns is None:
        logger.error("Failed to fetch campaigns")
        return []
    
    # Handle both list and dict responses
    if isinstance(campaigns, list):
        campaign_list = campaigns
    elif isinstance(campaigns, dict) and 'data' in campaigns:
        campaign_list = campaigns['data']
    else:
        logger.error(f"Unexpected campaigns response format: {type(campaigns)}")
        return []
    
    logger.info(f"✓ Fetched {len(campaign_list)} total campaigns")
    return campaign_list


def fetch_all_clients(session: requests.Session) -> Dict[int, Dict]:
    """Fetch all clients and return as a dictionary keyed by client_id"""
    logger.info("Fetching all clients...")
    
    clients = make_api_request(session, "/client/")
    
    if clients is None:
        logger.warning("Failed to fetch clients, will use campaign data only")
        return {}
    
    # Handle both list and dict responses
    if isinstance(clients, list):
        client_list = clients
    elif isinstance(clients, dict) and 'data' in clients:
        client_list = clients['data']
    else:
        logger.warning(f"Unexpected clients response format: {type(clients)}")
        return {}
    
    client_map = {
        client['id']: {
            'name': client.get('name', 'Unknown'),
            'email': client.get('email', 'N/A'),
            'company_name': client.get('company_name', 'N/A')
        }
        for client in client_list
    }
    
    logger.info(f"✓ Fetched {len(client_map)} clients")
    return client_map


def fetch_campaign_leads_paginated(
    session: requests.Session,
    campaign_id: int,
    status_filter: Optional[str] = None
) -> List[Dict]:
    """
    Fetch all leads for a campaign with pagination
    
    Args:
        session: Requests session
        campaign_id: Campaign ID
        status_filter: Optional status filter (STARTED, INPROGRESS, etc.)
        
    Returns:
        List of all leads
    """
    all_leads = []
    offset = 0
    
    params = {
        'limit': BATCH_SIZE,
        'offset': offset
    }
    
    if status_filter:
        params['status'] = status_filter
    
    while True:
        params['offset'] = offset
        
        response = make_api_request(
            session,
            f"/campaigns/{campaign_id}/leads",
            params=params
        )
        
        if response is None:
            logger.error(f"Failed to fetch leads for campaign {campaign_id} at offset {offset}")
            break
        
        # Extract leads from response
        leads = response.get('data', [])
        # Convert to int in case API returns string
        total_leads = int(response.get('total_leads', 0)) if response.get('total_leads') else 0
        
        if not leads:
            break
        
        all_leads.extend(leads)
        
        # Check if we've fetched all leads
        if len(all_leads) >= total_leads or len(leads) < BATCH_SIZE:
            break
        
        offset += BATCH_SIZE
        
        # Add delay to avoid rate limiting
        # Longer delay if we're fetching a lot of data
        if len(all_leads) > 1000:
            time.sleep(0.3)
        elif len(all_leads) > 500:
            time.sleep(0.2)
        else:
            time.sleep(0.1)
    
    return all_leads


def count_leads_by_status(
    session: requests.Session,
    campaign_id: int
) -> LeadStatusCount:
    """
    Count leads by status for a campaign
    
    Strategy: Fetch all leads once and count by status locally
    This is more efficient than multiple filtered API calls
    
    Args:
        session: Requests session
        campaign_id: Campaign ID
        
    Returns:
        LeadStatusCount object with all counts
    """
    logger.debug(f"Counting leads for campaign {campaign_id}")
    
    # Fetch all leads for this campaign
    all_leads = fetch_campaign_leads_paginated(session, campaign_id)
    
    counts = LeadStatusCount(total_leads=len(all_leads))
    
    # Count by status
    for lead in all_leads:
        status = lead.get('status', '').upper()
        
        if status == 'STARTED':
            counts.started += 1
        elif status == 'INPROGRESS':
            counts.inprogress += 1
        elif status == 'COMPLETED':
            counts.completed += 1
        elif status == 'PAUSED':
            counts.paused += 1
        elif status == 'STOPPED':
            counts.stopped += 1
        elif status == 'BLOCKED':
            counts.blocked += 1
    
    logger.debug(
        f"Campaign {campaign_id}: {counts.total_leads} total, "
        f"{counts.started} not contacted, {counts.already_contacted} contacted"
    )
    
    return counts


def process_single_campaign(
    session: requests.Session,
    campaign: Dict,
    client_map: Dict[int, Dict],
    fetch_timestamp: str
) -> CampaignData:
    """
    Process a single campaign to get lead counts
    
    Args:
        session: Requests session
        campaign: Campaign dict
        client_map: Client information map
        fetch_timestamp: Timestamp of this fetch operation
        
    Returns:
        CampaignData object
    """
    campaign_id = campaign['id']
    client_id = campaign.get('client_id')
    
    # Get client info
    client_info = client_map.get(client_id, {})
    client_name = campaign.get('client_name') or client_info.get('name', 'Unknown')
    client_email = client_info.get('email', 'N/A')
    client_company = client_info.get('company_name', 'N/A')
    
    try:
        # Count leads by status
        lead_counts = count_leads_by_status(session, campaign_id)
        
        return CampaignData(
            campaign_id=campaign_id,
            campaign_name=campaign.get('name', 'Unknown'),
            client_id=client_id or 0,
            client_name=client_name,
            client_email=client_email,
            client_company=client_company,
            status=campaign.get('status', 'UNKNOWN'),
            lead_counts=lead_counts,
            fetch_timestamp=fetch_timestamp
        )
        
    except Exception as e:
        logger.error(f"Error processing campaign {campaign_id}: {e}")
        return CampaignData(
            campaign_id=campaign_id,
            campaign_name=campaign.get('name', 'Unknown'),
            client_id=client_id or 0,
            client_name=client_name,
            client_email=client_email,
            client_company=client_company,
            status=campaign.get('status', 'UNKNOWN'),
            lead_counts=LeadStatusCount(),
            fetch_timestamp=fetch_timestamp,
            error=str(e)
        )


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_all_campaigns(
    campaigns: List[Dict],
    client_map: Dict[int, Dict],
    fetch_timestamp: str
) -> tuple[List[CampaignData], Dict[str, float]]:
    """
    Process all campaigns in parallel to get lead counts
    
    Args:
        campaigns: List of campaign dicts
        client_map: Client information map
        fetch_timestamp: Timestamp of this fetch operation
        
    Returns:
        Tuple of (List of CampaignData objects, timing metrics dict)
    """
    results = []
    total = len(campaigns)
    process_start_time = time.time()
    
    logger.info(f"Processing {total} campaigns with {MAX_WORKERS} parallel workers...")
    
    # Create a session for each worker
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all campaigns for processing
        future_to_campaign = {
            executor.submit(
                process_single_campaign,
                create_session(),  # Each thread gets its own session
                campaign,
                client_map,
                fetch_timestamp
            ): campaign['id']
            for campaign in campaigns
        }
        
        # Process completed futures with timing
        completed = 0
        last_progress_time = process_start_time
        campaign_times = []
        
        for future in as_completed(future_to_campaign, timeout=None):
            campaign_id = future_to_campaign[future]
            campaign_start_time = time.time()
            
            try:
                # Use timeout to prevent hanging on stuck campaigns
                result = future.result(timeout=600)  # 10 minute timeout per campaign
                results.append(result)
                completed += 1
                
                campaign_elapsed = time.time() - campaign_start_time
                campaign_times.append(campaign_elapsed)
                
                # Calculate timing metrics
                elapsed_time = time.time() - process_start_time
                avg_time_per_campaign = elapsed_time / completed if completed > 0 else 0
                remaining_campaigns = total - completed
                estimated_remaining_time = avg_time_per_campaign * remaining_campaigns
                
                # Progress reporting with timing
                current_time = time.time()
                time_since_last_progress = current_time - last_progress_time
                
                # Report every 10 campaigns, or every 30 seconds, or when complete
                if (completed % 10 == 0) or (completed == total) or (time_since_last_progress >= 30):
                    logger.info(
                        f"Progress: {completed}/{total} campaigns processed "
                        f"({completed/total*100:.1f}%) | "
                        f"Elapsed: {elapsed_time:.1f}s | "
                        f"Avg: {avg_time_per_campaign:.2f}s/campaign | "
                        f"Est. remaining: {estimated_remaining_time/60:.1f}min"
                    )
                    last_progress_time = current_time
                    
            except FutureTimeoutError:
                logger.error(f"Timeout processing campaign {campaign_id} (exceeded 10 minutes)")
                completed += 1
                campaign_elapsed = time.time() - campaign_start_time
                campaign_times.append(campaign_elapsed)
                # Create error result for timeout
                results.append(CampaignData(
                    campaign_id=campaign_id,
                    campaign_name="Unknown",
                    client_id=0,
                    client_name="Unknown",
                    client_email="N/A",
                    client_company="N/A",
                    status="UNKNOWN",
                    lead_counts=LeadStatusCount(),
                    fetch_timestamp=fetch_timestamp,
                    error="Timeout: Campaign processing exceeded 10 minutes"
                ))
            except Exception as e:
                logger.error(f"Exception processing campaign {campaign_id}: {e}", exc_info=True)
                completed += 1
                # Still add a timing entry for failed campaigns
                campaign_elapsed = time.time() - campaign_start_time
                campaign_times.append(campaign_elapsed)
    
    total_process_time = time.time() - process_start_time
    avg_time_per_campaign = total_process_time / total if total > 0 else 0
    
    # Calculate timing metrics
    timing_metrics = {
        'total_time': total_process_time,
        'avg_time_per_campaign': avg_time_per_campaign,
        'total_campaigns': total,
        'min_time': min(campaign_times) if campaign_times else 0,
        'max_time': max(campaign_times) if campaign_times else 0,
        'median_time': sorted(campaign_times)[len(campaign_times)//2] if campaign_times else 0
    }
    
    logger.info(f"✓ Completed processing {len(results)} campaigns")
    logger.info(
        f"Timing Summary: Total={total_process_time:.2f}s | "
        f"Avg={avg_time_per_campaign:.2f}s/campaign | "
        f"Min={timing_metrics['min_time']:.2f}s | "
        f"Max={timing_metrics['max_time']:.2f}s"
    )
    
    return results, timing_metrics


def export_to_google_sheets(campaign_data: List[CampaignData], sheets_client: GoogleSheetsUpdater) -> bool:
    """
    Export campaign data to Google Sheets
    
    Creates two sheets:
    1. "Yesterday" sheet - static sheet overwritten daily, positioned at index 0 (leftmost)
    2. Dated sheet with yesterday's date (YYYY/MM/DD format) - positioned at index 1 (right after "Yesterday")
    
    Args:
        campaign_data: List of CampaignData objects
        sheets_client: GoogleSheetsUpdater instance
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Exporting data to Google Sheets...")
    
    # Get yesterday's date in YYYY/MM/DD format (data is from yesterday)
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y/%m/%d")
    logger.info(f"Using yesterday's date for sheet: {date_str}")
    
    # First, get or create the "Yesterday" sheet and position it at index 0 (leftmost)
    try:
        yesterday_sheet_name, yesterday_sheet_id = sheets_client.get_or_create_yesterday_sheet()
    except Exception as e:
        logger.error(f"Failed to create/get Yesterday sheet: {e}")
        return False
    
    # Then, get or create the dated sheet and position it at index 1 (right after "Yesterday")
    try:
        dated_sheet_name, dated_sheet_id = sheets_client.get_or_create_dated_sheet(date_str)
    except Exception as e:
        logger.error(f"Failed to create/get dated sheet: {e}")
        return False
    
    # Ensure "Yesterday" sheet is still at index 0 (in case dated sheet creation moved it)
    try:
        # Refresh to get current positions
        spreadsheet = sheets_client.service.spreadsheets().get(
            spreadsheetId=sheets_client.sheet_id
        ).execute()
        sheets = spreadsheet.get('sheets', [])
        
        # Find current index of "Yesterday" sheet
        current_index = None
        for i, sheet in enumerate(sheets):
            if sheet['properties']['sheetId'] == yesterday_sheet_id:
                current_index = i
                break
        
        # Move to index 0 if not already there
        if current_index is not None and current_index > 0:
            requests = [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": yesterday_sheet_id,
                        "index": 0
                    },
                    "fields": "index"
                }
            }]
            body = {'requests': requests}
            sheets_client.service.spreadsheets().batchUpdate(
                spreadsheetId=sheets_client.sheet_id,
                body=body
            ).execute()
            logger.info(f"✓ Repositioned 'Yesterday' sheet to leftmost position (index 0)")
    except Exception as e:
        logger.warning(f"Failed to reposition Yesterday sheet (non-critical): {e}")
    
    # Prepare headers
    headers = [
        'Campaign ID',
        'Campaign Name',
        'Client ID',
        'Client Name',
        'Client Email',
        'Client Company',
        'Campaign Status',
        'Total Leads',
        'Not Yet Contacted (STARTED)',
        'Already Contacted',
        'In Progress',
        'Completed',
        'Paused',
        'Stopped',
        'Blocked',
        'Fetch Timestamp',
        'Error'
    ]
    
    # Prepare data rows
    values = [headers]
    
    for data in campaign_data:
        values.append([
            data.campaign_id,
            data.campaign_name,
            data.client_id,
            data.client_name,
            data.client_email,
            data.client_company,
            data.status,
            data.lead_counts.total_leads,
            data.lead_counts.not_yet_contacted,
            data.lead_counts.already_contacted,
            data.lead_counts.inprogress,
            data.lead_counts.completed,
            data.lead_counts.paused,
            data.lead_counts.stopped,
            data.lead_counts.blocked,
            data.fetch_timestamp,
            data.error or ''
        ])
    
    # Write to dated sheet (historical, keeps all dates)
    logger.info(f"Writing to dated sheet: {dated_sheet_name}")
    if not sheets_client.clear_sheet(dated_sheet_name):
        logger.error("Failed to clear dated sheet, attempting to write anyway...")
    
    range_name = f"{dated_sheet_name}!A1"
    if not sheets_client.update_sheet(values, range_name):
        logger.error("Failed to update dated sheet")
        return False
    
    sheets_client.format_headers(dated_sheet_id)
    logger.info(f"✓ Updated dated sheet '{dated_sheet_name}'")
    
    # Write to "Yesterday" sheet (static, overwritten daily)
    logger.info(f"Writing to static sheet: {yesterday_sheet_name}")
    if not sheets_client.clear_sheet(yesterday_sheet_name):
        logger.error("Failed to clear Yesterday sheet, attempting to write anyway...")
    
    range_name = f"{yesterday_sheet_name}!A1"
    if not sheets_client.update_sheet(values, range_name):
        logger.error("Failed to update Yesterday sheet")
        return False
    
    sheets_client.format_headers(yesterday_sheet_id)
    logger.info(f"✓ Updated static sheet '{yesterday_sheet_name}'")
    
    logger.info(f"✓ Google Sheets export complete: {len(campaign_data)} campaigns updated to both sheets")
    return True


def export_to_csv(campaign_data: List[CampaignData], filepath: str) -> None:
    """
    Export campaign data to CSV (backup/optional function)
    
    Args:
        campaign_data: List of CampaignData objects
        filepath: Output CSV file path
    """
    logger.info(f"Exporting data to CSV backup: {filepath}")
    
    # CSV headers
    headers = [
        'Campaign ID',
        'Campaign Name',
        'Client ID',
        'Client Name',
        'Client Email',
        'Client Company',
        'Campaign Status',
        'Total Leads',
        'Not Yet Contacted (STARTED)',
        'Already Contacted',
        'In Progress',
        'Completed',
        'Paused',
        'Stopped',
        'Blocked',
        'Fetch Timestamp',
        'Error'
    ]
    
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for data in campaign_data:
            writer.writerow([
                data.campaign_id,
                data.campaign_name,
                data.client_id,
                data.client_name,
                data.client_email,
                data.client_company,
                data.status,
                data.lead_counts.total_leads,
                data.lead_counts.not_yet_contacted,
                data.lead_counts.already_contacted,
                data.lead_counts.inprogress,
                data.lead_counts.completed,
                data.lead_counts.paused,
                data.lead_counts.stopped,
                data.lead_counts.blocked,
                data.fetch_timestamp,
                data.error or ''
            ])
    
    logger.info(f"✓ CSV backup export complete: {filepath}")


def print_summary(campaign_data: List[CampaignData]) -> None:
    """Print summary statistics"""
    total_campaigns = len(campaign_data)
    total_leads = sum(d.lead_counts.total_leads for d in campaign_data)
    total_not_contacted = sum(d.lead_counts.not_yet_contacted for d in campaign_data)
    total_contacted = sum(d.lead_counts.already_contacted for d in campaign_data)
    
    # Group by client
    clients = {}
    for data in campaign_data:
        client_name = data.client_name
        if client_name not in clients:
            clients[client_name] = {
                'campaigns': 0,
                'total_leads': 0,
                'not_contacted': 0,
                'contacted': 0
            }
        
        clients[client_name]['campaigns'] += 1
        clients[client_name]['total_leads'] += data.lead_counts.total_leads
        clients[client_name]['not_contacted'] += data.lead_counts.not_yet_contacted
        clients[client_name]['contacted'] += data.lead_counts.already_contacted
    
    print("\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)
    print(f"\nTotal Active Campaigns: {total_campaigns}")
    print(f"Total Clients: {len(clients)}")
    print(f"\nTotal Leads: {total_leads:,}")
    
    # Only show percentages if we have leads
    if total_leads > 0:
        print(f"  ├─ Not Yet Contacted (STARTED): {total_not_contacted:,} ({total_not_contacted/total_leads*100:.1f}%)")
        print(f"  └─ Already Contacted: {total_contacted:,} ({total_contacted/total_leads*100:.1f}%)")
    else:
        print(f"  ├─ Not Yet Contacted (STARTED): {total_not_contacted:,}")
        print(f"  └─ Already Contacted: {total_contacted:,}")
        print("\n⚠️  WARNING: No leads found in any campaigns. This could indicate:")
        print("    - API issues fetching lead data")
        print("    - All campaigns are empty")
        print("    - API rate limiting occurred")
        print("\nCheck the log file for detailed errors.")
    
    print("\n" + "-"*80)
    print("TOP 10 CLIENTS BY NOT YET CONTACTED LEADS")
    print("-"*80)
    
    # Sort clients by not contacted leads
    sorted_clients = sorted(
        clients.items(),
        key=lambda x: x[1]['not_contacted'],
        reverse=True
    )[:10]
    
    for client_name, stats in sorted_clients:
        print(f"\n{client_name}")
        print(f"  Campaigns: {stats['campaigns']}")
        print(f"  Total Leads: {stats['total_leads']:,}")
        print(f"  Not Yet Contacted: {stats['not_contacted']:,}")
        print(f"  Already Contacted: {stats['contacted']:,}")
    
    print("\n" + "="*80 + "\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    start_time = time.time()
    fetch_timestamp = datetime.now().isoformat()
    
    logger.info("="*80)
    logger.info("SmartLead Campaign Lead Tracker - Starting")
    logger.info("="*80)
    
    # Validate Google Sheets configuration
    if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID == "YOUR_GOOGLE_SHEET_ID_HERE":
        logger.error("Google Sheet ID not configured")
        logger.error("Please edit this script and set GOOGLE_SHEET_ID")
        return 1
    
    # Initialize Google Sheets client
    try:
        if GOOGLE_CREDENTIALS_JSON:
            sheets_client = GoogleSheetsUpdater(
                GOOGLE_SHEET_ID,
                credentials_json=GOOGLE_CREDENTIALS_JSON
            )
        else:
            sheets_client = GoogleSheetsUpdater(
                GOOGLE_SHEET_ID,
                credentials_file=GOOGLE_CREDENTIALS_FILE
            )
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {e}")
        logger.error("Please check your Google credentials configuration")
        return 1
    
    # Create output directory for logs and optional CSV backup
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create session
    session = create_session()
    
    try:
        # Step 1: Fetch all campaigns
        all_campaigns = fetch_all_campaigns(session)
        if not all_campaigns:
            logger.error("No campaigns found. Exiting.")
            return 1
        
        # Step 2: Filter for ACTIVE campaigns only
        active_campaigns = [c for c in all_campaigns if c.get('status') == 'ACTIVE']
        logger.info(f"✓ Filtered to {len(active_campaigns)} ACTIVE campaigns")
        
        if not active_campaigns:
            logger.warning("No active campaigns found. Exiting.")
            return 0
        
        # Step 3: Fetch all clients
        client_map = fetch_all_clients(session)
        
        # Step 4: Process all active campaigns in parallel
        campaign_data, timing_metrics = process_all_campaigns(
            active_campaigns,
            client_map,
            fetch_timestamp
        )
        
        # Step 5: Sort by client name, then campaign name
        campaign_data.sort(key=lambda x: (x.client_name, x.campaign_name))
        
        # Step 6: Export to Google Sheets
        if not export_to_google_sheets(campaign_data, sheets_client):
            logger.error("Failed to export to Google Sheets")
            # Create CSV backup on failure
            csv_path = os.path.join(OUTPUT_DIR, CSV_FILENAME)
            export_to_csv(campaign_data, csv_path)
            logger.info(f"Created CSV backup at: {csv_path}")
            return 1
        
        # Step 7: Print summary
        print_summary(campaign_data)
        
        # Calculate total execution time
        total_elapsed_time = time.time() - start_time
        
        # Print detailed timing information
        logger.info("="*80)
        logger.info("EXECUTION TIMING SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Campaigns Processed: {timing_metrics['total_campaigns']}")
        logger.info(f"Campaign Processing Time: {timing_metrics['total_time']:.2f} seconds ({timing_metrics['total_time']/60:.2f} minutes)")
        logger.info(f"Average Time per Campaign: {timing_metrics['avg_time_per_campaign']:.2f} seconds")
        logger.info(f"Fastest Campaign: {timing_metrics['min_time']:.2f} seconds")
        logger.info(f"Slowest Campaign: {timing_metrics['max_time']:.2f} seconds")
        logger.info(f"Median Campaign Time: {timing_metrics['median_time']:.2f} seconds")
        logger.info(f"Total Execution Time (including API calls & Google Sheets): {total_elapsed_time:.2f} seconds ({total_elapsed_time/60:.2f} minutes)")
        logger.info("")
        logger.info(f"Estimated Time for Future Runs:")
        logger.info(f"  - For {timing_metrics['total_campaigns']} campaigns: ~{timing_metrics['total_time']/60:.1f} minutes")
        logger.info(f"  - Per campaign average: ~{timing_metrics['avg_time_per_campaign']:.2f} seconds")
        logger.info("="*80)
        logger.info(f"✓ Data updated in Google Sheet: {GOOGLE_SHEET_ID}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
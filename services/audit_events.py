import streamlit as st
import pandas as pd
import requests
import logging
import re
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dateutil.parser import isoparse
from CheckmarxPythonSDK.CxOne.auditTrailAPI import get_audit_events_for_tenant
from Utils.utils import get_auth_headers

logger = logging.getLogger(__name__)

def fetch_events_from_link(url: str, headers: dict) -> list:
    """Fetch events from a link URL and normalize to common format."""
    try:
        response = requests.get(url, headers=headers)
        if response.ok:
            raw_events = response.json()
            # Link responses are lists of dicts with camelCase keys
            # Normalize to our standard format
            normalized = []
            for event in raw_events if isinstance(raw_events, list) else []:
                normalized.append(normalize_event_dict(event))
            return normalized
        else:
            logger.error(f"Failed to fetch link {url}: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching link {url}: {e}")
        return []

def normalize_sdk_event(event) -> dict:
    """Normalize an SDK AuditEvent object to standard dict format."""
    normalized = {}
    
    # Extract known attributes from SDK object
    attr_list = ['event_date', 'event_type', 'audit_resource', 'action_type', 
                 'action_user_id', 'tenant_id', 'resource_id', 'resource_name', 'data']
    
    for attr in attr_list:
        if hasattr(event, attr):
            value = getattr(event, attr)
            if attr == 'data' and isinstance(value, dict):
                # Handle nested data structure
                normalized['details_id'] = value.get('id', 'NA')
                normalized['details_status'] = value.get('status', 'NA')
                normalized['details_username'] = value.get('username', 'NA')
                normalized['data_raw'] = str(value)[:500]
            else:
                normalized[attr] = value if value not in [None, ''] else 'NA'
    
    # Get any additional attributes from __dict__
    if hasattr(event, '__dict__'):
        for k, v in vars(event).items():
            if k not in normalized and k != 'data':
                normalized[k] = v if v not in [None, ''] else 'NA'
    
    return normalized

def normalize_event_dict(event: dict) -> dict:
    """Normalize a raw event dict (from link response) to standard format."""
    normalized = {}
    
    # Map camelCase to snake_case for common fields
    field_mapping = {
        'eventDate': 'event_date',
        'eventType': 'event_type',
        'auditResource': 'audit_resource',
        'actionType': 'action_type',
        'actionUserId': 'action_user_id',
        'tenantId': 'tenant_id',
        'resourceId': 'resource_id',
        'resourceName': 'resource_name',
    }
    
    for camel_key, snake_key in field_mapping.items():
        if camel_key in event:
            normalized[snake_key] = event[camel_key]
    
    # Handle nested "data" structure (extract useful fields)
    if 'data' in event and isinstance(event['data'], dict):
        data = event['data']
        normalized['details_id'] = data.get('id', 'NA')
        normalized['details_status'] = data.get('status', 'NA')
        normalized['details_username'] = data.get('username', 'NA')
        # Include full data as string for reference
        normalized['data_raw'] = str(data)[:500]  # Truncate for display
    
    # Copy any remaining fields we didn't explicitly map
    for key, value in event.items():
        # Simple camelCase to snake_case conversion
        snake_key = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', key)
        snake_key = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_key).lower()
        if snake_key not in normalized and key != 'data':
            normalized[snake_key] = value if value not in [None, ''] else 'NA'
    
    return normalized

def fetch_audit_events(start_date: str, end_date: str, limit: int = 200, fetch_links: bool = True, thread_count: int = 4):
    """Fetch audit events for a given date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Max number of events to return (default 200)
        fetch_links: Whether to fetch events from links (historical data)
        thread_count: Number of threads for fetching links
    
    Returns:
        dict with 'events' list and metadata
    """
    # Get initial response
    result = get_audit_events_for_tenant(
        date_from=start_date, 
        date_to=end_date, 
        offset=0, 
        limit=limit
    )
    
    # Extract events (today's events from SDK objects)
    all_events = []
    if hasattr(result, 'events') and result.events:
        for event in result.events:
            event_dict = normalize_sdk_event(event)
            all_events.append(event_dict)
    
    # Fetch events from links (historical daily files)
    links_fetched = 0
    if fetch_links and hasattr(result, 'links') and result.links:
        headers = get_auth_headers()
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            future_to_link = {}
            for link in result.links:
                url = link.url if hasattr(link, 'url') else str(link)
                future_to_link[executor.submit(fetch_events_from_link, url, headers)] = url
            
            for future in as_completed(future_to_link):
                try:
                    link_events = future.result()
                    if isinstance(link_events, list):
                        all_events.extend(link_events)
                        links_fetched += 1
                except Exception as e:
                    logger.error(f"Error processing link: {e}")
    
    # Add formatted date for Excel
    for event in all_events:
        if 'event_date' in event and event['event_date']:
            try:
                parsed_dt = isoparse(str(event['event_date']))
                event['formatted_date'] = parsed_dt.strftime("%m/%d/%Y %H:%M")
            except:
                event['formatted_date'] = event['event_date']
    
    return {
        'events': all_events,
        'total_events': len(all_events),
        'links_fetched': links_fetched,
        'total_links': len(result.links) if hasattr(result, 'links') and result.links else 0
    }

def to_excel(df: pd.DataFrame) -> BytesIO:
    """Convert DataFrame to Excel bytes."""
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output

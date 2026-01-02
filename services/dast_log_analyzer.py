import re
from collections import defaultdict
from typing import Optional


def parse_dast_log_line(line: str) -> Optional[dict]:
    """Parse a CxOne DAST (ZAP) log line into components."""
    # Pattern: YYYY-MM-DD HH:MM:SS,mmm [thread] LEVEL  ClassName - Message
    pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[([^\]]+)\] (\w+)\s+(\S+) - (.*)$'
    
    match = re.match(pattern, line)
    if match:
        return {
            'timestamp': match.group(1),
            'thread': match.group(2).strip(),
            'level': match.group(3),
            'class': match.group(4),
            'message': match.group(5).strip()
        }
    return None


def extract_dast_scan_info(lines: list) -> dict:
    """Extract DAST scan information from the log."""
    scan_info = {}
    
    for line in lines:
        # ZAP version and start info
        if 'ZAP' in line and 'started' in line:
            # ZAP D-2025-12-23 started 31/12/2025, 19:02:04 with home: ... cores: 4 maxMemory: 6 GB
            match = re.search(r'ZAP (\S+) started', line)
            if match:
                scan_info['zap_version'] = match.group(1)
            
            match = re.search(r'cores: (\d+)', line)
            if match:
                scan_info['cores'] = match.group(1)
            
            match = re.search(r'maxMemory: (\d+\s*\w+)', line)
            if match:
                scan_info['max_memory'] = match.group(1)
        
        # Target URL
        if 'Scanning' in line and 'node(s) from' in line:
            match = re.search(r'from (\S+)', line)
            if match:
                scan_info['target_url'] = match.group(1)
        
        # Final status
        if 'Automation plan succeeded' in line:
            scan_info['status'] = 'Succeeded'
        elif 'Automation plan failed' in line:
            scan_info['status'] = 'Failed'
        
        # ZAP terminated
        if 'ZAP' in line and 'terminated' in line:
            scan_info['completed'] = True
    
    return scan_info


def extract_jobs(lines: list) -> list:
    """Extract job execution information."""
    jobs = []
    current_job = None
    
    for line in lines:
        # Job started
        if 'Job' in line and 'started' in line:
            match = re.search(r'Job (\S+) started', line)
            if match:
                current_job = {'name': match.group(1), 'status': 'running'}
        
        # Job finished
        if 'Job' in line and 'finished' in line:
            match = re.search(r'Job (\S+) finished, time taken: (\S+)', line)
            if match:
                job = {
                    'name': match.group(1),
                    'duration': match.group(2),
                    'status': 'completed'
                }
                jobs.append(job)
        
        # Job added URLs (openapi)
        if 'Job' in line and 'added' in line and 'URLs' in line:
            match = re.search(r'added (\d+) URLs', line)
            if match and jobs:
                jobs[-1]['urls_added'] = int(match.group(1))
    
    return jobs


def extract_scan_rules(lines: list) -> dict:
    """Extract scan rule information."""
    passive_rules = []
    active_rules = []
    
    for line in lines:
        # Passive scan rules
        if 'Loaded passive scan rule:' in line:
            match = re.search(r'Loaded passive scan rule: (.+)$', line)
            if match:
                passive_rules.append(match.group(1).strip())
        
        # Active scan rules (host/plugin completed)
        if 'completed host/plugin' in line:
            match = re.search(r'\| (\w+) in ([\d.]+)s with (\d+) message\(s\) sent and (\d+) alert\(s\) raised', line)
            if match:
                active_rules.append({
                    'name': match.group(1),
                    'duration': float(match.group(2)),
                    'messages_sent': int(match.group(3)),
                    'alerts_raised': int(match.group(4))
                })
    
    return {
        'passive_rules': passive_rules,
        'active_rules': active_rules
    }


def extract_addons(lines: list) -> list:
    """Extract installed add-ons."""
    addons = []
    
    for line in lines:
        if 'Installed add-ons:' in line:
            # Parse the add-ons list
            match = re.search(r'\[\[(.+)\]\]', line)
            if match:
                addon_str = match.group(1)
                # Extract id and version pairs
                addon_matches = re.findall(r'id=(\w+), version=([\d.]+)', addon_str)
                for addon_id, version in addon_matches:
                    addons.append({'id': addon_id, 'version': version})
    
    return addons


def analyze_dast_log(content: str) -> dict:
    """Analyze the full DAST log and extract metrics."""
    lines = content.split('\n')
    
    parsed_lines = []
    errors = []
    warnings = []
    
    for line in lines:
        parsed = parse_dast_log_line(line)
        if parsed:
            parsed_lines.append(parsed)
            
            if parsed['level'] == 'ERROR':
                errors.append(parsed)
            elif parsed['level'] == 'WARN':
                warnings.append(parsed)
    
    # Extract various info
    scan_info = extract_dast_scan_info(lines)
    jobs = extract_jobs(lines)
    scan_rules = extract_scan_rules(lines)
    addons = extract_addons(lines)
    
    # Calculate totals
    total_messages = sum(r['messages_sent'] for r in scan_rules['active_rules'])
    total_alerts = sum(r['alerts_raised'] for r in scan_rules['active_rules'])
    
    # Get timestamps for duration
    first_timestamp = None
    last_timestamp = None
    for parsed in parsed_lines:
        if first_timestamp is None:
            first_timestamp = parsed['timestamp']
        last_timestamp = parsed['timestamp']
    
    return {
        'total_lines': len(lines),
        'parsed_lines': len(parsed_lines),
        'errors': errors,
        'warnings': warnings,
        'scan_info': scan_info,
        'jobs': jobs,
        'passive_rules': scan_rules['passive_rules'],
        'active_rules': scan_rules['active_rules'],
        'addons': addons,
        'total_messages': total_messages,
        'total_alerts': total_alerts,
        'first_timestamp': first_timestamp,
        'last_timestamp': last_timestamp
    }


def filter_dast_log_lines(lines: list, text_filter: str = None, level_filter: list = None) -> list:
    """Filter log lines by text and/or level."""
    filtered = lines
    
    if text_filter:
        filtered = [l for l in filtered if text_filter.lower() in l.lower()]
    
    if level_filter:
        filtered = [l for l in filtered if any(f"] {level} " in l for level in level_filter)]
    
    return filtered


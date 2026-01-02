import re
from collections import defaultdict
from typing import Optional


def normalize_filepath(filepath: str) -> str:
    """
    Normalize a file path by removing the temp directory prefix and scan UUID.
    Returns the relative project path.
    """
    # Normalize slashes
    path = filepath.replace('\\', '/')
    
    # Match any prefix followed by a UUID, capture everything after
    # UUID pattern: 8-4-4-4-12 hex characters
    match = re.search(r'.*?[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/(.+)$', path, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Fallback: return the original path with normalized slashes
    return path


def parse_log_line(line: str) -> Optional[dict]:
    """Parse a CxOne engine log line into components."""
    # Pattern: DD/MM/YYYY HH:MM:SS,mmm [Thread] LEVEL  Available memory: XXX Used memory: XXX Elapsed Time: HH:MM:SS.nnn [Phase] - Message
    pattern = r'^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2},\d{3}) \[([^\]]+)\] (\w+)\s+Available memory: (\d+) Used memory: (\d+) Elapsed Time: ([\d:.]+) \[([^\]]+)\] - (.*)$'
    
    match = re.match(pattern, line)
    if match:
        return {
            'timestamp': match.group(1),
            'thread': match.group(2),
            'level': match.group(3),
            'available_memory': int(match.group(4)),
            'used_memory': int(match.group(5)),
            'elapsed_time': match.group(6),
            'phase': match.group(7),
            'message': match.group(8).strip()
        }
    return None


def parse_query_info(message: str) -> Optional[dict]:
    """Extract query info from a query message."""
    # Pattern: {Language: XXX, PackageTypeName: Cx, GroupName: XXX, QueryName: XXX}
    pattern = r"Language: (\w+), PackageTypeName: (\w+), GroupName: ([\w_]+), QueryName: ([\w_]+)"
    match = re.search(pattern, message)
    if match:
        return {
            'language': match.group(1),
            'package': match.group(2),
            'group': match.group(3),
            'query': match.group(4)
        }
    
    # Also match "Begin running query XXX.Cx.XXX.XXX"
    begin_pattern = r"Begin running query ([\w.]+)"
    match = re.search(begin_pattern, message)
    if match:
        parts = match.group(1).split('.')
        if len(parts) >= 4:
            return {
                'language': parts[0],
                'package': parts[1],
                'group': parts[2],
                'query': parts[3] if len(parts) > 3 else parts[2]
            }
    return None


def extract_scan_info(lines: list) -> dict:
    """Extract scan information from the log."""
    scan_info = {}
    
    # Basic info from first lines
    for line in lines[:50]:
        if 'Product version:' in line:
            scan_info['version'] = line.split('Product version:')[1].strip()
        if 'HostName:' in line:
            scan_info['hostname'] = line.split('HostName:')[1].strip()
        if 'Processor Count:' in line:
            scan_info['processors'] = line.split('Processor Count:')[1].strip()
        if 'OS:' in line and line.strip().startswith('OS:'):
            scan_info['os'] = line.split('OS:')[1].strip()
    
    # Check for incremental scan info (search entire log)
    scan_info['is_incremental'] = False
    scan_info['incremental_files_changed'] = None
    scan_info['incremental_skipped'] = False
    
    for line in lines:
        if 'in Incremental Scan State' in line:
            scan_info['is_incremental'] = True
        
        if 'Incremental Scan: number of files changed:' in line:
            # Extract number: "Incremental Scan: number of files changed: 0."
            match = re.search(r'number of files changed:\s*(\d+)', line)
            if match:
                scan_info['incremental_files_changed'] = int(match.group(1))
                if scan_info['incremental_files_changed'] == 0:
                    scan_info['incremental_skipped'] = True
    
    return scan_info


def analyze_log(content: str) -> dict:
    """Analyze the full log and extract metrics."""
    lines = content.split('\n')
    
    parsed_lines = []
    errors = []
    warnings = []
    queries_run = []
    files_processed = set()  # Use set for unique files
    phases = defaultdict(int)
    memory_timeline = []
    
    for line in lines:
        parsed = parse_log_line(line)
        if parsed:
            parsed_lines.append(parsed)
            phases[parsed['phase']] += 1
            
            # Track memory
            memory_timeline.append({
                'elapsed': parsed['elapsed_time'],
                'used': parsed['used_memory'],
                'available': parsed['available_memory']
            })
            
            # Collect errors/warnings
            if parsed['level'] == 'ERROR':
                errors.append(parsed)
            elif parsed['level'] == 'WARN':
                warnings.append(parsed)
            
            # Track queries
            if parsed['phase'] == 'Queries':
                if 'Finish running query' in parsed['message']:
                    query_info = parse_query_info(parsed['message'])
                    if query_info:
                        queries_run.append(query_info)
            
            # Track file processing
            if 'Finished processing file' in parsed['message']:
                file_match = re.search(r'file: (.+)$', parsed['message'])
                if file_match:
                    files_processed.add(normalize_filepath(file_match.group(1).strip()))
    
    return {
        'total_lines': len(lines),
        'parsed_lines': len(parsed_lines),
        'errors': errors,
        'warnings': warnings,
        'queries_run': queries_run,
        'files_processed': list(files_processed),  # Convert set to list
        'phases': dict(phases),
        'memory_timeline': memory_timeline,
        'scan_info': extract_scan_info(lines)
    }


def group_queries_by_language(queries: list) -> dict:
    """Group queries by language."""
    by_language = defaultdict(list)
    for q in queries:
        by_language[q['language']].append(q)
    return dict(by_language)


def group_queries_by_group(queries: list) -> dict:
    """Group queries by group name."""
    by_group = defaultdict(list)
    for q in queries:
        by_group[q['group']].append(q['query'])
    return dict(by_group)


def filter_log_lines(lines: list, text_filter: str = None, level_filter: list = None) -> list:
    """Filter log lines by text and/or level."""
    filtered = lines
    
    if text_filter:
        filtered = [l for l in filtered if text_filter.lower() in l.lower()]
    
    if level_filter:
        filtered = [l for l in filtered if any(f"] {level} " in l for level in level_filter)]
    
    return filtered


def get_peak_memory(memory_timeline: list) -> int:
    """Get peak memory usage from timeline."""
    if not memory_timeline:
        return 0
    return max(m['used'] for m in memory_timeline)


def get_total_elapsed_time(memory_timeline: list) -> str:
    """Get total elapsed time from the last entry in the timeline."""
    if not memory_timeline:
        return "N/A"
    return memory_timeline[-1]['elapsed']


def format_elapsed_time(elapsed: str) -> str:
    """Format elapsed time string for display (HH:MM:SS.nnn -> HH:MM:SS)."""
    if not elapsed or elapsed == "N/A":
        return "N/A"
    # Remove nanoseconds for cleaner display
    parts = elapsed.split('.')
    return parts[0] if parts else elapsed


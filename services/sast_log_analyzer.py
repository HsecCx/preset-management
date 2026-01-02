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


def parse_sast_log_line(line: str) -> Optional[dict]:
    """Parse a CxSAST scan log line into components."""
    # Format: DD/MM/YYYY HH:MM:SS,mmm [thread] LEVEL  Available memory: X Used memory: Y Elapsed Time: ... [Phase] - Message
    pattern = r'^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2},\d{3}) \[([^\]]+)\] (\w+)\s+Available memory: (\d+) Used memory: (\d+) Elapsed Time: ([\d:.]+) \[([^\]]+)\] - (.*)$'
    
    match = re.match(pattern, line)
    if match:
        return {
            'timestamp': match.group(1),
            'thread': match.group(2).strip(),
            'level': match.group(3),
            'available_memory': int(match.group(4)),
            'used_memory': int(match.group(5)),
            'elapsed_time': match.group(6),
            'phase': match.group(7),
            'message': match.group(8).strip()
        }
    return None


def extract_sast_scan_info(lines: list) -> dict:
    """Extract CxSAST scan information from the log."""
    scan_info = {}
    
    full_text = '\n'.join(lines[:500])  # Only check first 500 lines for header info
    
    # Product version
    match = re.search(r'Product version: (.+)', full_text)
    if match:
        scan_info['version'] = match.group(1).strip()
    
    # Available memory
    match = re.search(r'Available memory: (\d+)Mb', full_text)
    if match:
        scan_info['available_memory_mb'] = int(match.group(1))
    
    # OS
    match = re.search(r'OS: (.+)', full_text)
    if match:
        scan_info['os'] = match.group(1).strip()
    
    # Hostname
    match = re.search(r'HostName: (.+)', full_text)
    if match:
        scan_info['hostname'] = match.group(1).strip()
    
    # FQDN
    match = re.search(r'FQDN: (.+)', full_text)
    if match:
        scan_info['fqdn'] = match.group(1).strip()
    
    # Processor count
    match = re.search(r'Processor Count: (\d+)', full_text)
    if match:
        scan_info['processors'] = int(match.group(1))
    
    # Platform
    if '64Bit platform' in full_text:
        scan_info['platform'] = '64-bit'
    elif '32Bit platform' in full_text:
        scan_info['platform'] = '32-bit'
    
    # CLR Version
    match = re.search(r'CLR Version: (.+)', full_text)
    if match:
        scan_info['clr_version'] = match.group(1).strip()
    
    # Project info
    match = re.search(r"ProjectId='(\d+)',ProjectName='([^']+)'", full_text)
    if match:
        scan_info['project_id'] = match.group(1)
        scan_info['project_name'] = match.group(2)
    
    # SAST Engine version
    match = re.search(r'Product: Checkmarx SAST Engine\s*-\s*Main Version: ([\d.]+)', full_text, re.MULTILINE)
    if match:
        scan_info['sast_version'] = match.group(1)
    
    # Incremental scan detection (search entire log)
    scan_info['is_incremental'] = False
    scan_info['incremental_files_changed'] = None
    scan_info['incremental_skipped'] = False
    
    full_log = '\n'.join(lines)
    
    # Check for incremental scan indicators
    if 'in Incremental Scan State' in full_log:
        scan_info['is_incremental'] = True
    
    # Check for "Starting regular scan" vs incremental
    if 'Starting regular scan' in full_log:
        # Check if IncrementalFiles.cx exists - indicates incremental capability
        if 'IncrementalFiles.cx exists:True' in full_log:
            scan_info['is_incremental'] = True
    
    # Check for incremental files changed count
    for line in lines:
        if 'Incremental Scan: number of files changed:' in line:
            match = re.search(r'number of files changed:\s*(\d+)', line)
            if match:
                scan_info['incremental_files_changed'] = int(match.group(1))
                scan_info['is_incremental'] = True
                if scan_info['incremental_files_changed'] == 0:
                    scan_info['incremental_skipped'] = True
        
        # Alternative pattern: "Incremental scan detected X changed files"
        if 'changed files' in line.lower() and 'incremental' in line.lower():
            match = re.search(r'(\d+)\s*changed files', line, re.IGNORECASE)
            if match:
                scan_info['incremental_files_changed'] = int(match.group(1))
                scan_info['is_incremental'] = True
                if scan_info['incremental_files_changed'] == 0:
                    scan_info['incremental_skipped'] = True
    
    return scan_info


def extract_languages(lines: list) -> dict:
    """Extract language information from the log."""
    languages = {}
    lines_of_code = 0
    scanned_loc = 0
    
    for line in lines:
        # Languages scanned: JavaScript=82, VbScript=24, Python=24
        if 'Languages that will be scanned:' in line or 'source files were identified:' in line:
            matches = re.findall(r'(\w+)=(\d+)', line)
            for lang, count in matches:
                languages[lang] = int(count)
        
        # Total lines of code
        if 'lines of code' in line.lower():
            match = re.search(r'(\d+) lines of code', line)
            if match:
                lines_of_code = int(match.group(1))
        
        # Actually scanned LOC
        if 'Actually scanned lines of code:' in line:
            match = re.search(r'Actually scanned lines of code: (\d+)', line)
            if match:
                scanned_loc = int(match.group(1))
    
    return {
        'languages': languages,
        'total_loc': lines_of_code,
        'scanned_loc': scanned_loc
    }


def extract_phases(lines: list) -> list:
    """Extract engine phases from the log."""
    phases = []
    
    for line in lines:
        # Engine Phase (Start): Parsing VBScript
        if 'Engine Phase (Start):' in line:
            match = re.search(r'Engine Phase \(Start\): (.+)', line)
            if match:
                phase_name = match.group(1).strip()
                timestamp = line[:23] if len(line) > 23 else ''
                phases.append({
                    'name': phase_name,
                    'type': 'start',
                    'timestamp': timestamp
                })
        elif 'Engine Phase ( End ):' in line:
            match = re.search(r'Engine Phase \( End \): (.+)', line)
            if match:
                phase_name = match.group(1).strip()
                timestamp = line[:23] if len(line) > 23 else ''
                phases.append({
                    'name': phase_name,
                    'type': 'end',
                    'timestamp': timestamp
                })
    
    return phases


def extract_queries(lines: list) -> list:
    """Extract query execution information from the log."""
    queries = []
    in_queries_section = False
    
    for line in lines:
        # Detect start of queries summary section
        # Format: ---------------------------General Queries Summary------------------------------Status-...
        if 'General Queries Summary' in line and 'End General Queries Summary' not in line:
            in_queries_section = True
            continue
        elif 'End General Queries Summary' in line:
            in_queries_section = False
            continue
        
        if in_queries_section:
            # Skip empty lines
            stripped = line.strip()
            if not stripped:
                continue
            
            # Parse query lines
            # Format: Language.QueryName_hash  status  results  duration  ...
            # Example: JavaScript.NodeJS_Find_All_Passwords_42989a4f  success  56  00:00:00.328  ...
            match = re.match(r'^(\w+)\.([^\s]+)\s+(success|failure|error)\s+(\d+)\s+([\d:.]+)', stripped)
            if match:
                queries.append({
                    'language': match.group(1),
                    'name': match.group(2),
                    'status': match.group(3),
                    'results': int(match.group(4)),
                    'duration': match.group(5)
                })
    
    return queries


def extract_files_processed(lines: list) -> list:
    """Extract files that were processed, with normalized paths."""
    files = set()
    
    for line in lines:
        # Try both "Started processing file:" and "Finished processing file:"
        # to capture all files mentioned in the log
        if 'Started processing file:' in line:
            match = re.search(r'Started processing file:\s*(.+?)(?:\s*$)', line)
            if match:
                filepath = match.group(1).strip()
                if filepath:
                    files.add(normalize_filepath(filepath))
        elif 'Finished processing file:' in line:
            match = re.search(r'Finished processing file:\s*(.+?)(?:\s*$)', line)
            if match:
                filepath = match.group(1).strip()
                if filepath:
                    files.add(normalize_filepath(filepath))
    
    return list(files)


def extract_errors_warnings(lines: list) -> tuple:
    """Extract errors and warnings from the log."""
    errors = []
    warnings = []
    
    for line in lines:
        parsed = parse_sast_log_line(line)
        if parsed:
            if parsed['level'] == 'ERROR':
                errors.append(parsed)
            elif parsed['level'] == 'WARN':
                warnings.append(parsed)
    
    return errors, warnings


def extract_memory_timeline(lines: list) -> list:
    """Extract memory usage over time."""
    timeline = []
    
    for line in lines:
        parsed = parse_sast_log_line(line)
        if parsed:
            timeline.append({
                'elapsed_time': parsed['elapsed_time'],
                'available_memory': parsed['available_memory'],
                'used_memory': parsed['used_memory']
            })
    
    return timeline


def get_total_elapsed_time(lines: list) -> str:
    """Get the total elapsed time from the last log line."""
    for line in reversed(lines):
        parsed = parse_sast_log_line(line)
        if parsed:
            return parsed['elapsed_time']
    return "00:00:00"


def get_peak_memory(memory_timeline: list) -> int:
    """Get peak used memory from timeline."""
    if not memory_timeline:
        return 0
    return max(m['used_memory'] for m in memory_timeline)


def extract_query_totals(lines: list) -> dict:
    """Extract query totals from the summary line."""
    totals = {
        'total_results': 0,
        'total_query_time': '00:00:00'
    }
    
    for line in lines:
        if line.strip().startswith('Total:'):
            # Parse: Total:  179481  00:00:17.603  ...
            parts = line.split()
            if len(parts) >= 3:
                try:
                    totals['total_results'] = int(parts[1])
                    totals['total_query_time'] = parts[2]
                except (ValueError, IndexError):
                    pass
    
    return totals


def analyze_sast_log(content: str) -> dict:
    """Analyze the full CxSAST log and extract metrics."""
    lines = content.split('\n')
    
    # Extract all information
    scan_info = extract_sast_scan_info(lines)
    language_info = extract_languages(lines)
    phases = extract_phases(lines)
    queries = extract_queries(lines)
    files_processed = extract_files_processed(lines)
    errors, warnings = extract_errors_warnings(lines)
    memory_timeline = extract_memory_timeline(lines)
    query_totals = extract_query_totals(lines)
    total_elapsed = get_total_elapsed_time(lines)
    
    # Count queries by language
    queries_by_language = defaultdict(list)
    for q in queries:
        queries_by_language[q['language']].append(q)
    
    # Count successful vs failed queries
    successful_queries = sum(1 for q in queries if q['status'] == 'success')
    failed_queries = sum(1 for q in queries if q['status'] != 'success')
    
    return {
        'total_lines': len(lines),
        'scan_info': scan_info,
        'languages': language_info['languages'],
        'total_loc': language_info['total_loc'],
        'scanned_loc': language_info['scanned_loc'],
        'phases': phases,
        'queries': queries,
        'queries_by_language': dict(queries_by_language),
        'successful_queries': successful_queries,
        'failed_queries': failed_queries,
        'query_totals': query_totals,
        'files_processed': files_processed,
        'errors': errors,
        'warnings': warnings,
        'memory_timeline': memory_timeline,
        'peak_memory': get_peak_memory(memory_timeline),
        'total_elapsed_time': total_elapsed
    }


def filter_sast_log_lines(lines: list, text_filter: str = None, level_filter: list = None) -> list:
    """Filter log lines by text and/or level."""
    filtered = lines
    
    if text_filter:
        filtered = [l for l in filtered if text_filter.lower() in l.lower()]
    
    if level_filter:
        filtered = [l for l in filtered if any(f"] {level} " in l for level in level_filter)]
    
    return filtered


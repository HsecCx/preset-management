"""
Log Comparator Service
Compares two scan logs (CxOne or CxSAST) and extracts differences.
"""
from services.log_analyzer import analyze_log as analyze_cxone_log
from services.sast_log_analyzer import analyze_sast_log


def detect_log_type(content: str) -> str:
    """
    Detect whether a log is CxOne SAST, CxSAST on-prem, or other format.
    
    Returns:
        'cxone_sast' - CxOne cloud SAST engine (runs on Kubernetes/Unix)
        'cxsast' - CxSAST on-prem (runs on Windows)
        'cxone' - CxOne generic log format
    """
    # Check first 150 lines for signature patterns
    sample = '\n'.join(content.split('\n')[:150])
    
    # Check for CxOne cloud SAST engine (Kubernetes-based)
    # These logs have SAST engine format but run on Unix/Kubernetes
    is_sast_engine_format = (
        'Available memory:' in sample and 
        'Used memory:' in sample and 
        'Elapsed Time:' in sample
    )
    
    if is_sast_engine_format:
        # Distinguish CxOne cloud vs CxSAST on-prem
        is_cxone_cloud = (
            'sast-engine-worker' in sample.lower() or  # Kubernetes pod name
            'OS: Unix' in sample or
            'OS: Linux' in sample or
            '/app/Engine' in sample or  # Container path
            'kubernetes.io' in sample or  # K8s secrets mount
            '/usr/share/dotnet' in sample  # Linux dotnet path
        )
        
        if is_cxone_cloud:
            return 'cxone_sast'
        else:
            return 'cxsast'
    
    # CxSAST on-prem specific patterns
    if 'Checkmarx Engine Service' in sample:
        return 'cxsast'
    
    # CxOne generic patterns
    if 'CxOne' in sample or 'cx-one' in sample.lower():
        return 'cxone'
    if 'ast-sast' in sample.lower():
        return 'cxone'
    if 'INFO  QueryResolver' in sample:
        return 'cxone'
    if 'Starting Query:' in sample:
        return 'cxone'
    
    # Default to CxOne if unclear
    return 'cxone'


def normalize_analysis(analysis: dict, log_type: str) -> dict:
    """Normalize analysis results to a common format for comparison."""
    if log_type in ('cxsast', 'cxone_sast'):
        # Both CxSAST on-prem and CxOne cloud SAST use the same log format
        scan_info = analysis.get('scan_info', {})
        queries = analysis.get('queries', [])
        
        # Build query dict: name -> results
        query_dict = {}
        for q in queries:
            full_name = f"{q['language']}.{q['name']}"
            query_dict[full_name] = {
                'results': q['results'],
                'duration': q['duration'],
                'status': q['status']
            }
        
        # Determine display label
        if log_type == 'cxone_sast':
            label = 'CxOne SAST'
        else:
            label = 'CxSAST (On-Prem)'
        
        # Build scan mode string
        if scan_info.get('incremental_skipped'):
            scan_mode = 'Incremental (Skipped - 0 changes)'
        elif scan_info.get('is_incremental'):
            files_changed = scan_info.get('incremental_files_changed')
            if files_changed is not None:
                scan_mode = f'Incremental ({files_changed} files changed)'
            else:
                scan_mode = 'Incremental'
        else:
            scan_mode = 'Full Scan'
        
        return {
            'log_type': label,
            'project_name': scan_info.get('project_name', 'Unknown'),
            'total_time': analysis.get('total_elapsed_time', '00:00:00'),
            'files_count': len(analysis.get('files_processed', [])),
            'files': set(analysis.get('files_processed', [])),
            'queries_count': len(queries),
            'queries': query_dict,
            'total_results': analysis.get('query_totals', {}).get('total_results', 0),
            'errors_count': len(analysis.get('errors', [])),
            'errors': analysis.get('errors', []),
            'languages': analysis.get('languages', {}),
            'loc': analysis.get('scanned_loc', 0),
            'peak_memory': analysis.get('peak_memory', 0),
            'is_incremental': scan_info.get('is_incremental', False),
            'incremental_files_changed': scan_info.get('incremental_files_changed'),
            'incremental_skipped': scan_info.get('incremental_skipped', False),
            'scan_mode': scan_mode,
        }
    else:
        # Extract from CxOne generic analysis
        scan_info = analysis.get('scan_info', {})
        queries = analysis.get('queries_run', [])
        
        # Build query dict
        query_dict = {}
        for q in queries:
            full_name = f"{q.get('language', 'Unknown')}.{q.get('group', '')}.{q.get('name', 'Unknown')}"
            query_dict[full_name] = {
                'results': 0,  # CxOne log doesn't always have results per query
                'duration': '00:00:00',
                'status': 'success'
            }
        
        # Build scan mode string
        if scan_info.get('incremental_skipped'):
            scan_mode = 'Incremental (Skipped - 0 changes)'
        elif scan_info.get('is_incremental'):
            files_changed = scan_info.get('incremental_files_changed')
            if files_changed is not None:
                scan_mode = f'Incremental ({files_changed} files changed)'
            else:
                scan_mode = 'Incremental'
        else:
            scan_mode = 'Full Scan'
        
        return {
            'log_type': 'CxOne',
            'project_name': scan_info.get('project_name', scan_info.get('hostname', 'Unknown')),
            'total_time': analysis.get('total_elapsed_time', '00:00:00'),
            'files_count': len(analysis.get('files_processed', [])),
            'files': set(analysis.get('files_processed', [])),
            'queries_count': len(queries),
            'queries': query_dict,
            'total_results': 0,
            'errors_count': len(analysis.get('errors', [])),
            'errors': analysis.get('errors', []),
            'languages': {},
            'loc': 0,
            'peak_memory': 0,
            'is_incremental': scan_info.get('is_incremental', False),
            'incremental_files_changed': scan_info.get('incremental_files_changed'),
            'incremental_skipped': scan_info.get('incremental_skipped', False),
            'scan_mode': scan_mode,
        }


def analyze_and_normalize(content: str) -> dict:
    """Detect log type, analyze, and normalize for comparison."""
    log_type = detect_log_type(content)
    
    if log_type in ('cxsast', 'cxone_sast'):
        # Both use the same SAST engine log format
        analysis = analyze_sast_log(content)
    else:
        analysis = analyze_cxone_log(content)
    
    return normalize_analysis(analysis, log_type)


def compare_logs(norm1: dict, norm2: dict) -> dict:
    """Compare two normalized log analyses."""
    comparison = {
        'summary': {},
        'files_diff': {},
        'queries_diff': {},
        'errors_diff': {}
    }
    
    # Summary comparison
    comparison['summary'] = {
        'log_type': (norm1['log_type'], norm2['log_type']),
        'project_name': (norm1['project_name'], norm2['project_name']),
        'scan_mode': (norm1.get('scan_mode', 'Unknown'), norm2.get('scan_mode', 'Unknown')),
        'total_time': (norm1['total_time'], norm2['total_time']),
        'files_count': (norm1['files_count'], norm2['files_count']),
        'queries_count': (norm1['queries_count'], norm2['queries_count']),
        'total_results': (norm1['total_results'], norm2['total_results']),
        'errors_count': (norm1['errors_count'], norm2['errors_count']),
        'loc': (norm1['loc'], norm2['loc']),
        'peak_memory': (norm1['peak_memory'], norm2['peak_memory']),
    }
    
    # Files diff - compare by filename but display full relative path
    files1 = norm1['files']
    files2 = norm2['files']
    
    # Map filename -> full relative path for display
    def get_filename(path):
        return path.replace('\\', '/').split('/')[-1]
    
    files1_by_name = {get_filename(f): f for f in files1}
    files2_by_name = {get_filename(f): f for f in files2}
    
    files1_names = set(files1_by_name.keys())
    files2_names = set(files2_by_name.keys())
    
    # Return full relative paths, not just filenames
    comparison['files_diff'] = {
        'only_in_1': sorted([files1_by_name[n] for n in (files1_names - files2_names)]),
        'only_in_2': sorted([files2_by_name[n] for n in (files2_names - files1_names)]),
        'in_both': sorted([files1_by_name[n] for n in (files1_names & files2_names)]),
    }
    
    # Queries diff
    queries1 = set(norm1['queries'].keys())
    queries2 = set(norm2['queries'].keys())
    
    # For queries in both, compare results
    queries_changed = []
    for q in queries1 & queries2:
        r1 = norm1['queries'][q]['results']
        r2 = norm2['queries'][q]['results']
        if r1 != r2:
            queries_changed.append({
                'name': q,
                'results_1': r1,
                'results_2': r2,
                'diff': r2 - r1
            })
    
    comparison['queries_diff'] = {
        'only_in_1': sorted(queries1 - queries2),
        'only_in_2': sorted(queries2 - queries1),
        'in_both': len(queries1 & queries2),
        'results_changed': sorted(queries_changed, key=lambda x: abs(x['diff']), reverse=True),
    }
    
    # Errors comparison (just counts and messages)
    comparison['errors_diff'] = {
        'errors_1': [e.get('message', str(e))[:100] for e in norm1['errors'][:10]],
        'errors_2': [e.get('message', str(e))[:100] for e in norm2['errors'][:10]],
    }
    
    return comparison


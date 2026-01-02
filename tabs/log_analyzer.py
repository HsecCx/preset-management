import streamlit as st
import pandas as pd
from collections import defaultdict
from services.log_analyzer import (
    analyze_log,
    group_queries_by_language,
    group_queries_by_group,
    filter_log_lines,
    get_peak_memory,
    get_total_elapsed_time,
    format_elapsed_time
)
from services.dast_log_analyzer import (
    analyze_dast_log,
    filter_dast_log_lines
)
from services.sast_log_analyzer import (
    analyze_sast_log,
    filter_sast_log_lines
)
from services.log_comparator import (
    detect_log_type,
    analyze_and_normalize,
    compare_logs
)


def render():
    """Render the Log Analyzer tab with subtabs."""
    st.markdown("### Log Analyzer")
    st.caption("Analyze various Checkmarx log files")
    
    # Subtabs
    sub_cxone_source, sub_cxone_dast, sub_cxsast, sub_compare, sub_other = st.tabs([
        "🔧 CxOne Source Engine",
        "🌐 CxOne DAST",
        "🏢 CxSAST Scan",
        "⚖️ Compare Logs",
        "📋 Other Logs"
    ])
    
    with sub_cxone_source:
        render_cxone_source_analyzer()
    
    with sub_cxone_dast:
        render_cxone_dast_analyzer()
    
    with sub_cxsast:
        render_cxsast_analyzer()
    
    with sub_compare:
        render_log_comparison()
    
    with sub_other:
        render_other_logs()


def render_cxone_source_analyzer():
    """Render the CxOne Source Engine Log Analyzer subtab."""
    st.markdown("#### CxOne Source Engine Log Analyzer")
    st.caption("Upload and analyze CxOne source scan engine logs (SAST, SCA, IaC)")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload an engine log file",
        type=["log", "txt"],
        key="cxone_log_file_upload"
    )
    
    if uploaded_file is not None:
        content = uploaded_file.read().decode('utf-8', errors='replace')
        
        with st.spinner("Analyzing log..."):
            analysis = analyze_log(content)
        
        render_scan_info(analysis['scan_info'])
        st.markdown("---")
        render_summary(analysis)
        st.markdown("---")
        render_detail_tabs(analysis, content)
    
    else:
        render_source_placeholder()


def render_cxone_dast_analyzer():
    """Render the CxOne DAST Log Analyzer subtab."""
    st.markdown("#### CxOne DAST Log Analyzer")
    st.caption("Upload and analyze CxOne DAST (ZAP-based) scan logs")
    
    uploaded_file = st.file_uploader(
        "Upload a DAST log file",
        type=["log", "txt"],
        key="dast_log_file_upload"
    )
    
    if uploaded_file is not None:
        content = uploaded_file.read().decode('utf-8', errors='replace')
        
        with st.spinner("Analyzing DAST log..."):
            analysis = analyze_dast_log(content)
        
        render_dast_scan_info(analysis)
        st.markdown("---")
        render_dast_summary(analysis)
        st.markdown("---")
        render_dast_detail_tabs(analysis, content)
    else:
        render_dast_placeholder()


def render_cxsast_analyzer():
    """Render the CxSAST Scan Log Analyzer subtab."""
    st.markdown("#### CxSAST Scan Log Analyzer")
    st.caption("Upload and analyze Checkmarx SAST (on-premise) scan logs")
    
    uploaded_file = st.file_uploader(
        "Upload a CxSAST scan log file",
        type=["log", "txt"],
        key="cxsast_log_file_upload"
    )
    
    if uploaded_file is not None:
        content = uploaded_file.read().decode('utf-8', errors='replace')
        
        with st.spinner("Analyzing CxSAST log..."):
            analysis = analyze_sast_log(content)
        
        render_sast_scan_info(analysis)
        st.markdown("---")
        render_sast_summary(analysis)
        st.markdown("---")
        render_sast_detail_tabs(analysis, content)
    else:
        render_sast_placeholder()


def render_other_logs():
    """Render placeholder for other log types."""
    st.markdown("#### Other Log Analyzers")
    st.info("🚧 Coming soon - Additional log analyzers")
    st.markdown("""
    Planned support:
    - CxSAST Manager logs
    - CxSAST Scan logs
    - CxOne API logs
    - Custom log formats
    """)


def render_scan_info(scan_info: dict):
    """Render scan information section."""
    if not scan_info:
        return
    
    st.markdown("#### 📋 Scan Information")
    
    # Check for incremental scan with no changes
    if scan_info.get('incremental_skipped'):
        st.warning("⚡ **Incremental Scan - No Changes Detected**\n\nThis scan ran in incremental mode and found 0 files changed. The full scan was skipped.")
    elif scan_info.get('is_incremental'):
        files_changed = scan_info.get('incremental_files_changed', 'unknown')
        st.info(f"⚡ **Incremental Scan** - {files_changed} file(s) changed")
    
    cols = st.columns(2)
    with cols[0]:
        if 'version' in scan_info:
            st.text(f"Engine Version: {scan_info['version'][:50]}...")
        if 'hostname' in scan_info:
            st.text(f"Host: {scan_info['hostname']}")
    with cols[1]:
        if 'os' in scan_info:
            st.text(f"OS: {scan_info['os']}")
        if 'processors' in scan_info:
            st.text(f"Processors: {scan_info['processors']}")


def render_summary(analysis: dict):
    """Render summary metrics."""
    st.markdown("#### 📊 Summary")
    
    # First row - main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        elapsed = get_total_elapsed_time(analysis['memory_timeline'])
        st.metric("Total Time", format_elapsed_time(elapsed))
    with col2:
        st.metric("Errors", len(analysis['errors']), delta_color="inverse")
    with col3:
        st.metric("Warnings", len(analysis['warnings']), delta_color="off")
    with col4:
        st.metric("Queries Run", len(analysis['queries_run']))
    
    # Second row
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Files Processed", len(analysis['files_processed']))
    with col6:
        peak_memory = get_peak_memory(analysis['memory_timeline'])
        st.metric("Peak Memory (MB)", f"{peak_memory:,}")
    with col7:
        st.metric("Total Lines", f"{analysis['total_lines']:,}")
    with col8:
        st.metric("Phases", len(analysis['phases']))


def render_detail_tabs(analysis: dict, content: str):
    """Render detail subtabs."""
    tab_errors, tab_queries, tab_phases, tab_files, tab_raw = st.tabs([
        f"🔴 Errors ({len(analysis['errors'])})",
        f"🔍 Queries ({len(analysis['queries_run'])})",
        "📈 Phases",
        f"📁 Files ({len(analysis['files_processed'])})",
        "📄 Raw Log"
    ])
    
    with tab_errors:
        render_errors_tab(analysis['errors'], analysis['warnings'])
    
    with tab_queries:
        render_queries_tab(analysis['queries_run'])
    
    with tab_phases:
        render_phases_tab(analysis['phases'])
    
    with tab_files:
        render_files_tab(analysis['files_processed'])
    
    with tab_raw:
        render_raw_tab(content)


def render_errors_tab(errors: list, warnings: list):
    """Render errors and warnings tab."""
    if errors:
        st.markdown("#### Errors")
        for err in errors:
            st.error(f"**[{err['elapsed_time']}]** {err['message']}")
    else:
        st.success("✅ No errors found")
    
    if warnings:
        st.markdown("#### Warnings")
        for warn in warnings[:20]:
            st.warning(f"**[{warn['elapsed_time']}]** {warn['message']}")
        if len(warnings) > 20:
            st.caption(f"... and {len(warnings) - 20} more warnings")


def render_queries_tab(queries_run: list):
    """Render queries analysis tab."""
    if not queries_run:
        st.info("No query execution data found")
        return
    
    by_language = group_queries_by_language(queries_run)
    
    st.markdown("#### Queries by Language")
    for lang, queries in sorted(by_language.items()):
        with st.expander(f"{lang} ({len(queries)} queries)"):
            by_group = group_queries_by_group(queries)
            
            for group, query_names in sorted(by_group.items()):
                st.markdown(f"**{group}** ({len(query_names)})")
                unique_names = sorted(set(query_names))
                display_names = unique_names[:10]
                st.caption(", ".join(display_names) + ("..." if len(unique_names) > 10 else ""))


def render_phases_tab(phases: dict):
    """Render phases breakdown tab."""
    if not phases:
        st.info("No phase data found")
        return
    
    st.markdown("#### Log Entries by Phase")
    phase_df = pd.DataFrame([
        {'Phase': k, 'Count': v} 
        for k, v in sorted(phases.items(), key=lambda x: -x[1])
    ])
    st.dataframe(phase_df, use_container_width=True, hide_index=True)
    st.bar_chart(phase_df.set_index('Phase'))


def render_files_tab(files_processed: list):
    """Render processed files tab."""
    if not files_processed:
        st.info("No file processing data found")
        return
    
    st.markdown("#### Processed Files")
    
    file_filter = st.text_input("Filter files", placeholder="e.g., .js, routes", key="file_filter")
    
    filtered_files = files_processed
    if file_filter:
        filtered_files = [f for f in filtered_files if file_filter.lower() in f.lower()]
    
    st.caption(f"Showing {len(filtered_files)} of {len(files_processed)} files")
    
    for f in filtered_files[:100]:
        st.text(f"📄 {f}")
    
    if len(filtered_files) > 100:
        st.caption(f"... and {len(filtered_files) - 100} more files")


def render_raw_tab(content: str):
    """Render raw log tab with filters."""
    st.markdown("#### Raw Log")
    
    col1, col2 = st.columns(2)
    with col1:
        filter_text = st.text_input(
            "Search",
            placeholder="Enter search term...",
            key="raw_log_filter"
        )
    with col2:
        log_level = st.multiselect(
            "Filter by level",
            options=["ERROR", "WARN", "INFO", "DEBUG"],
            default=[],
            key="raw_log_level"
        )
    
    lines = content.split('\n')
    filtered_lines = filter_log_lines(lines, filter_text, log_level if log_level else None)
    
    max_lines = st.slider("Max lines", 50, 500, 100, key="raw_max_lines")
    
    st.caption(f"Showing {min(len(filtered_lines), max_lines)} of {len(filtered_lines)} filtered lines")
    st.code('\n'.join(filtered_lines[:max_lines]), language="log")


def render_source_placeholder():
    """Render placeholder when no file is uploaded."""
    st.info("📂 Upload a CxOne source engine log file to begin analysis")
    
    st.markdown("#### What this analyzer provides:")
    st.markdown("""
    - **Scan Information**: Engine version, host, OS, processors
    - **Incremental Scan Detection**: Shows if scan was skipped due to no changes
    - **Total Time**: Complete scan duration
    - **Error/Warning Detection**: Quickly identify issues
    - **Query Analysis**: See which queries ran, grouped by language
    - **Phase Breakdown**: Understand time spent in each scan phase
    - **File Processing**: View all files analyzed
    - **Memory Tracking**: Monitor memory usage
    """)


# ============================================================================
# DAST Log Analyzer Functions
# ============================================================================

def render_dast_scan_info(analysis: dict):
    """Render DAST scan information."""
    scan_info = analysis.get('scan_info', {})
    
    st.markdown("#### 🌐 DAST Scan Information")
    
    # Status banner
    status = scan_info.get('status', 'Unknown')
    if status == 'Succeeded':
        st.success("✅ Automation plan succeeded!")
    elif status == 'Failed':
        st.error("❌ Automation plan failed!")
    
    cols = st.columns(3)
    with cols[0]:
        if 'zap_version' in scan_info:
            st.text(f"ZAP Version: {scan_info['zap_version']}")
        if 'target_url' in scan_info:
            st.text(f"Target: {scan_info['target_url']}")
    with cols[1]:
        if 'cores' in scan_info:
            st.text(f"Cores: {scan_info['cores']}")
        if 'max_memory' in scan_info:
            st.text(f"Max Memory: {scan_info['max_memory']}")
    with cols[2]:
        if analysis.get('first_timestamp'):
            st.text(f"Started: {analysis['first_timestamp'][:19]}")
        if analysis.get('last_timestamp'):
            st.text(f"Ended: {analysis['last_timestamp'][:19]}")


def render_dast_summary(analysis: dict):
    """Render DAST summary metrics."""
    st.markdown("#### 📊 Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Add-ons Loaded", len(analysis.get('addons', [])))
    with col2:
        st.metric("Passive Rules", len(analysis.get('passive_rules', [])))
    with col3:
        st.metric("Active Rules", len(analysis.get('active_rules', [])))
    with col4:
        st.metric("Jobs Executed", len(analysis.get('jobs', [])))
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Total Messages", analysis.get('total_messages', 0))
    with col6:
        st.metric("Alerts Raised", analysis.get('total_alerts', 0))
    with col7:
        st.metric("Errors", len(analysis.get('errors', [])), delta_color="inverse")
    with col8:
        st.metric("Warnings", len(analysis.get('warnings', [])), delta_color="off")


def render_dast_detail_tabs(analysis: dict, content: str):
    """Render DAST detail tabs."""
    tab_jobs, tab_rules, tab_addons, tab_issues, tab_raw = st.tabs([
        f"📋 Jobs ({len(analysis.get('jobs', []))})",
        f"🛡️ Scan Rules ({len(analysis.get('active_rules', []))})",
        f"🧩 Add-ons ({len(analysis.get('addons', []))})",
        f"⚠️ Issues ({len(analysis.get('errors', [])) + len(analysis.get('warnings', []))})",
        "📄 Raw Log"
    ])
    
    with tab_jobs:
        render_dast_jobs_tab(analysis.get('jobs', []))
    
    with tab_rules:
        render_dast_rules_tab(analysis)
    
    with tab_addons:
        render_dast_addons_tab(analysis.get('addons', []))
    
    with tab_issues:
        render_dast_issues_tab(analysis.get('errors', []), analysis.get('warnings', []))
    
    with tab_raw:
        render_dast_raw_tab(content)


def render_dast_jobs_tab(jobs: list):
    """Render jobs execution tab."""
    if not jobs:
        st.info("No job data found")
        return
    
    st.markdown("#### Job Execution Timeline")
    
    for job in jobs:
        cols = st.columns([3, 2, 1])
        with cols[0]:
            st.markdown(f"**{job['name']}**")
        with cols[1]:
            st.text(f"Duration: {job['duration']}")
        with cols[2]:
            if job.get('urls_added'):
                st.text(f"+{job['urls_added']} URLs")
    
    # Create DataFrame for display
    df = pd.DataFrame(jobs)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_dast_rules_tab(analysis: dict):
    """Render scan rules tab."""
    st.markdown("#### Active Scan Rules")
    
    active_rules = analysis.get('active_rules', [])
    if active_rules:
        df = pd.DataFrame(active_rules)
        df = df.sort_values('duration', ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Bar chart of durations
        st.markdown("##### Rule Duration (seconds)")
        chart_df = df.head(15).set_index('name')[['duration']]
        st.bar_chart(chart_df)
    else:
        st.info("No active scan rules executed")
    
    st.markdown("---")
    st.markdown("#### Passive Scan Rules")
    
    passive_rules = analysis.get('passive_rules', [])
    if passive_rules:
        st.caption(f"{len(passive_rules)} passive rules loaded")
        with st.expander("View all passive rules"):
            for rule in passive_rules:
                st.text(f"• {rule}")
    else:
        st.info("No passive scan rules found")


def render_dast_addons_tab(addons: list):
    """Render add-ons tab."""
    if not addons:
        st.info("No add-ons data found")
        return
    
    st.markdown("#### Installed ZAP Add-ons")
    st.caption(f"{len(addons)} add-ons installed")
    
    # Create DataFrame
    df = pd.DataFrame(addons)
    df = df.sort_values('id')
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Search/filter
    search = st.text_input("Search add-ons", placeholder="e.g., spider, sql", key="addon_search")
    if search:
        filtered = [a for a in addons if search.lower() in a['id'].lower()]
        st.caption(f"Found {len(filtered)} matching add-ons")
        for addon in filtered:
            st.text(f"• {addon['id']} (v{addon['version']})")


def render_dast_issues_tab(errors: list, warnings: list):
    """Render errors and warnings tab."""
    st.markdown("#### Errors")
    if errors:
        for err in errors:
            st.error(f"**[{err['timestamp'][:19]}]** [{err['class']}] {err['message'][:200]}")
    else:
        st.success("✅ No errors found")
    
    st.markdown("---")
    st.markdown("#### Warnings")
    if warnings:
        # Group similar warnings
        warning_groups = {}
        for warn in warnings:
            key = warn['message'][:80]
            if key not in warning_groups:
                warning_groups[key] = []
            warning_groups[key].append(warn)
        
        for msg, group in warning_groups.items():
            with st.expander(f"⚠️ {msg}... ({len(group)} occurrences)"):
                for warn in group[:5]:
                    st.caption(f"[{warn['timestamp'][:19]}] {warn['message']}")
                if len(group) > 5:
                    st.caption(f"... and {len(group) - 5} more")
    else:
        st.success("✅ No warnings found")


def render_dast_raw_tab(content: str):
    """Render raw DAST log tab."""
    st.markdown("#### Raw Log")
    
    col1, col2 = st.columns(2)
    with col1:
        filter_text = st.text_input(
            "Search",
            placeholder="Enter search term...",
            key="dast_raw_log_filter"
        )
    with col2:
        log_level = st.multiselect(
            "Filter by level",
            options=["ERROR", "WARN", "INFO"],
            default=[],
            key="dast_raw_log_level"
        )
    
    lines = content.split('\n')
    filtered_lines = filter_dast_log_lines(lines, filter_text, log_level if log_level else None)
    
    max_lines = st.slider("Max lines", 50, 500, 100, key="dast_raw_max_lines")
    
    st.caption(f"Showing {min(len(filtered_lines), max_lines)} of {len(filtered_lines)} filtered lines")
    st.code('\n'.join(filtered_lines[:max_lines]), language="log")


def render_dast_placeholder():
    """Render placeholder when no DAST file is uploaded."""
    st.info("📂 Upload a CxOne DAST log file to begin analysis")
    
    st.markdown("#### What this analyzer provides:")
    st.markdown("""
    - **Scan Status**: Success/failure of the automation plan
    - **ZAP Information**: Version, cores, memory allocation
    - **Target URL**: The scanned application URL
    - **Jobs Executed**: passiveScan-config, openapi, activeScan, report, etc.
    - **Active Scan Rules**: Execution time and alerts per rule
    - **Passive Scan Rules**: List of loaded passive rules
    - **Add-ons**: All installed ZAP extensions
    - **Error/Warning Detection**: JSON parsing issues, etc.
    - **Messages & Alerts**: Total requests sent and vulnerabilities found
    """)


# ============================================================================
# CxSAST Log Analyzer Functions
# ============================================================================

def render_sast_scan_info(analysis: dict):
    """Render CxSAST scan information."""
    scan_info = analysis.get('scan_info', {})
    
    st.markdown("#### 🏢 CxSAST Scan Information")
    
    # Check for incremental scan info
    if scan_info.get('incremental_skipped'):
        st.warning("⚡ **Incremental Scan - No Changes Detected**\n\nThis scan ran in incremental mode and found 0 files changed. The full scan was skipped.")
    elif scan_info.get('is_incremental'):
        files_changed = scan_info.get('incremental_files_changed', 'unknown')
        st.info(f"⚡ **Incremental Scan** - {files_changed} file(s) changed")
    
    # Project info banner
    if 'project_name' in scan_info:
        st.success(f"📁 **Project**: {scan_info['project_name']} (ID: {scan_info.get('project_id', 'N/A')})")
    
    cols = st.columns(3)
    with cols[0]:
        if 'version' in scan_info:
            st.text(f"Engine: {scan_info['version'][:40]}...")
        if 'hostname' in scan_info:
            st.text(f"Host: {scan_info['hostname']}")
        if 'fqdn' in scan_info:
            st.text(f"FQDN: {scan_info['fqdn']}")
    with cols[1]:
        if 'os' in scan_info:
            st.text(f"OS: {scan_info['os'][:30]}...")
        if 'platform' in scan_info:
            st.text(f"Platform: {scan_info['platform']}")
        if 'processors' in scan_info:
            st.text(f"Processors: {scan_info['processors']}")
    with cols[2]:
        if 'available_memory_mb' in scan_info:
            st.text(f"Available Memory: {scan_info['available_memory_mb']:,} MB")
        if 'clr_version' in scan_info:
            st.text(f"CLR Version: {scan_info['clr_version']}")
        if 'sast_version' in scan_info:
            st.text(f"SAST Version: {scan_info['sast_version']}")


def render_sast_summary(analysis: dict):
    """Render CxSAST summary metrics."""
    st.markdown("#### 📊 Summary")
    
    # First row - main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Time", analysis.get('total_elapsed_time', '00:00:00'))
    with col2:
        st.metric("Queries Run", len(analysis.get('queries', [])))
    with col3:
        st.metric("Total Results", analysis.get('query_totals', {}).get('total_results', 0))
    with col4:
        st.metric("Languages", len(analysis.get('languages', {})))
    
    # Second row
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Files Processed", len(analysis.get('files_processed', [])))
    with col6:
        st.metric("Lines of Code", f"{analysis.get('scanned_loc', 0):,}")
    with col7:
        st.metric("Peak Memory (MB)", f"{analysis.get('peak_memory', 0):,}")
    with col8:
        st.metric("Errors", len(analysis.get('errors', [])), delta_color="inverse")
    
    # Languages breakdown
    languages = analysis.get('languages', {})
    if languages:
        st.markdown("##### Languages Detected")
        lang_cols = st.columns(len(languages) if len(languages) <= 6 else 6)
        for i, (lang, count) in enumerate(languages.items()):
            with lang_cols[i % 6]:
                st.metric(lang, f"{count} files")


def render_sast_detail_tabs(analysis: dict, content: str):
    """Render CxSAST detail tabs."""
    queries = analysis.get('queries', [])
    files = analysis.get('files_processed', [])
    errors = analysis.get('errors', [])
    warnings = analysis.get('warnings', [])
    phases = analysis.get('phases', [])
    
    tab_queries, tab_phases, tab_files, tab_issues, tab_raw = st.tabs([
        f"🔍 Queries ({len(queries)})",
        f"📈 Phases ({len(phases)})",
        f"📁 Files ({len(files)})",
        f"⚠️ Issues ({len(errors) + len(warnings)})",
        "📄 Raw Log"
    ])
    
    with tab_queries:
        render_sast_queries_tab(analysis)
    
    with tab_phases:
        render_sast_phases_tab(phases)
    
    with tab_files:
        render_sast_files_tab(files)
    
    with tab_issues:
        render_sast_issues_tab(errors, warnings)
    
    with tab_raw:
        render_sast_raw_tab(content)


def render_sast_queries_tab(analysis: dict):
    """Render CxSAST queries tab."""
    queries = analysis.get('queries', [])
    queries_by_language = analysis.get('queries_by_language', {})
    
    if not queries:
        st.info("No query data found in the log")
        return
    
    st.markdown("#### Query Execution Summary")
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Successful", analysis.get('successful_queries', 0))
    with col2:
        st.metric("Failed", analysis.get('failed_queries', 0), delta_color="inverse")
    with col3:
        st.metric("Query Time", analysis.get('query_totals', {}).get('total_query_time', '00:00:00'))
    
    st.markdown("---")
    st.markdown("#### Queries by Language")
    
    for lang, lang_queries in sorted(queries_by_language.items()):
        # Calculate stats for this language
        results_count = sum(q['results'] for q in lang_queries)
        with_results = sum(1 for q in lang_queries if q['results'] > 0)
        
        with st.expander(f"**{lang}** ({len(lang_queries)} queries, {results_count:,} results)"):
            # Show queries with results first
            queries_with_results = [q for q in lang_queries if q['results'] > 0]
            if queries_with_results:
                st.markdown("##### Queries with Results")
                df = pd.DataFrame(queries_with_results)
                df = df.sort_values('results', ascending=False)
                st.dataframe(df[['name', 'status', 'results', 'duration']], 
                           use_container_width=True, hide_index=True)
            
            # Summary of queries without results
            no_results = len(lang_queries) - len(queries_with_results)
            if no_results > 0:
                st.caption(f"+ {no_results} queries with 0 results")


def render_sast_phases_tab(phases: list):
    """Render CxSAST phases tab."""
    if not phases:
        st.info("No phase data found")
        return
    
    st.markdown("#### Engine Phases")
    
    # Group by phase name to show start/end
    phase_pairs = {}
    for p in phases:
        name = p['name']
        if name not in phase_pairs:
            phase_pairs[name] = {}
        phase_pairs[name][p['type']] = p['timestamp']
    
    for name, times in phase_pairs.items():
        cols = st.columns([3, 2, 2])
        with cols[0]:
            st.markdown(f"**{name}**")
        with cols[1]:
            if 'start' in times:
                st.text(f"Start: {times['start'][:19] if times['start'] else 'N/A'}")
        with cols[2]:
            if 'end' in times:
                st.text(f"End: {times['end'][:19] if times['end'] else 'N/A'}")


def render_sast_files_tab(files: list):
    """Render CxSAST files tab."""
    if not files:
        st.info("No file processing data found")
        return
    
    st.markdown("#### Processed Files")
    st.caption(f"Total: {len(files)} files")
    
    # File filter
    file_filter = st.text_input("Filter files", placeholder="e.g., .js, routes", key="sast_file_filter")
    
    filtered_files = files
    if file_filter:
        filtered_files = [f for f in files if file_filter.lower() in f.lower()]
    
    st.caption(f"Showing {len(filtered_files)} of {len(files)} files")
    
    # Group by extension
    by_extension = defaultdict(list)
    for f in filtered_files:
        ext = f.split('.')[-1] if '.' in f else 'no extension'
        by_extension[ext].append(f)
    
    for ext, ext_files in sorted(by_extension.items(), key=lambda x: -len(x[1])):
        with st.expander(f".{ext} ({len(ext_files)} files)"):
            for f in ext_files[:50]:
                st.text(f"📄 {f}")
            if len(ext_files) > 50:
                st.caption(f"... and {len(ext_files) - 50} more")


def render_sast_issues_tab(errors: list, warnings: list):
    """Render CxSAST errors and warnings tab."""
    st.markdown("#### Errors")
    if errors:
        for err in errors[:20]:
            st.error(f"**[{err.get('elapsed_time', 'N/A')}]** [{err.get('phase', 'Unknown')}] {err.get('message', '')[:200]}")
        if len(errors) > 20:
            st.caption(f"... and {len(errors) - 20} more errors")
    else:
        st.success("✅ No errors found")
    
    st.markdown("---")
    st.markdown("#### Warnings")
    if warnings:
        # Group similar warnings
        warning_groups = defaultdict(list)
        for warn in warnings:
            key = warn.get('message', '')[:60]
            warning_groups[key].append(warn)
        
        for msg, group in list(warning_groups.items())[:10]:
            with st.expander(f"⚠️ {msg}... ({len(group)} occurrences)"):
                for warn in group[:5]:
                    st.caption(f"[{warn.get('elapsed_time', 'N/A')}] {warn.get('message', '')}")
                if len(group) > 5:
                    st.caption(f"... and {len(group) - 5} more")
        
        if len(warning_groups) > 10:
            st.caption(f"... and {len(warning_groups) - 10} more warning types")
    else:
        st.success("✅ No warnings found")


def render_sast_raw_tab(content: str):
    """Render raw CxSAST log tab."""
    st.markdown("#### Raw Log")
    
    col1, col2 = st.columns(2)
    with col1:
        filter_text = st.text_input(
            "Search",
            placeholder="Enter search term...",
            key="sast_raw_log_filter"
        )
    with col2:
        log_level = st.multiselect(
            "Filter by level",
            options=["ERROR", "WARN", "INFO"],
            default=[],
            key="sast_raw_log_level"
        )
    
    lines = content.split('\n')
    filtered_lines = filter_sast_log_lines(lines, filter_text, log_level if log_level else None)
    
    max_lines = st.slider("Max lines", 50, 500, 100, key="sast_raw_max_lines")
    
    st.caption(f"Showing {min(len(filtered_lines), max_lines)} of {len(filtered_lines)} filtered lines")
    st.code('\n'.join(filtered_lines[:max_lines]), language="log")


def render_sast_placeholder():
    """Render placeholder when no CxSAST file is uploaded."""
    st.info("📂 Upload a CxSAST scan log file to begin analysis")
    
    st.markdown("#### What this analyzer provides:")
    st.markdown("""
    - **Scan Information**: Engine version, host, OS, processors, project details
    - **Language Detection**: Files and lines of code per language
    - **Query Analysis**: All queries run with results count and duration
    - **Phase Timeline**: Parsing, Resolving, Querying phases with timing
    - **File Processing**: View all files analyzed with filtering
    - **Memory Tracking**: Peak memory usage during scan
    - **Error/Warning Detection**: Issues encountered during scan
    - **Total Results**: Aggregated vulnerability findings count
    """)


# ============================================================================
# Log Comparison Functions
# ============================================================================

def render_log_comparison():
    """Render the log comparison tab."""
    st.markdown("#### ⚖️ Scan Log Comparison")
    st.caption("Compare two scan logs (CxOne or CxSAST) side by side")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 📄 Log File 1 (Baseline)")
        file1 = st.file_uploader(
            "Upload first log file",
            type=["log", "txt"],
            key="compare_log_1"
        )
    
    with col2:
        st.markdown("##### 📄 Log File 2 (Compare)")
        file2 = st.file_uploader(
            "Upload second log file",
            type=["log", "txt"],
            key="compare_log_2"
        )
    
    if file1 is not None and file2 is not None:
        content1 = file1.read().decode('utf-8', errors='replace')
        content2 = file2.read().decode('utf-8', errors='replace')
        
        with st.spinner("Analyzing and comparing logs..."):
            # Detect and analyze
            type1 = detect_log_type(content1)
            type2 = detect_log_type(content2)
            
            norm1 = analyze_and_normalize(content1)
            norm2 = analyze_and_normalize(content2)
            
            comparison = compare_logs(norm1, norm2)
        
        # Show detected types
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ Detected: **{norm1['log_type']}**")
        with col2:
            st.success(f"✅ Detected: **{norm2['log_type']}**")
        
        st.markdown("---")
        render_comparison_summary(comparison, norm1, norm2)
        st.markdown("---")
        render_comparison_details(comparison, norm1, norm2)
    
    elif file1 is not None or file2 is not None:
        st.info("📤 Upload both log files to compare them")
    else:
        render_comparison_placeholder()


def render_comparison_summary(comparison: dict, norm1: dict, norm2: dict):
    """Render the comparison summary."""
    st.markdown("#### 📊 Summary Comparison")
    
    summary = comparison['summary']
    queries_diff = comparison.get('queries_diff', {})
    
    # Create comparison table
    metrics = [
        ("Project", summary['project_name'][0], summary['project_name'][1], "", False),
        ("Scan Mode", summary.get('scan_mode', ('Unknown', 'Unknown'))[0], 
         summary.get('scan_mode', ('Unknown', 'Unknown'))[1], "", False),
        ("Total Time", summary['total_time'][0], summary['total_time'][1], "", False),
        ("Files Scanned", summary['files_count'][0], summary['files_count'][1], 
         _calc_diff(summary['files_count'][0], summary['files_count'][1]), False),
        ("Queries Run", summary['queries_count'][0], summary['queries_count'][1],
         _calc_diff(summary['queries_count'][0], summary['queries_count'][1]), False),
        ("Total Results", summary['total_results'][0], summary['total_results'][1],
         _calc_diff(summary['total_results'][0], summary['total_results'][1]), True),  # Drillable
        ("Lines of Code", f"{summary['loc'][0]:,}", f"{summary['loc'][1]:,}",
         _calc_diff(summary['loc'][0], summary['loc'][1]), False),
        ("Peak Memory (MB)", f"{summary['peak_memory'][0]:,}", f"{summary['peak_memory'][1]:,}",
         _calc_diff(summary['peak_memory'][0], summary['peak_memory'][1]), False),
        ("Errors", summary['errors_count'][0], summary['errors_count'][1],
         _calc_diff(summary['errors_count'][0], summary['errors_count'][1], invert=True), False),
    ]
    
    # Display as columns
    col_metric, col_log1, col_log2, col_diff = st.columns([2, 2, 2, 1])
    with col_metric:
        st.markdown("**Metric**")
    with col_log1:
        st.markdown("**Log 1 (Baseline)**")
    with col_log2:
        st.markdown("**Log 2 (Compare)**")
    with col_diff:
        st.markdown("**Diff**")
    
    for metric, val1, val2, diff, drillable in metrics:
        col_metric, col_log1, col_log2, col_diff = st.columns([2, 2, 2, 1])
        with col_metric:
            st.text(metric)
        with col_log1:
            st.text(str(val1))
        with col_log2:
            st.text(str(val2))
        with col_diff:
            if diff:
                st.text(diff)
    
    # Drillable section for Total Results - always show if we have query data
    has_query_data = (
        queries_diff.get('results_changed') or 
        queries_diff.get('only_in_1') or 
        queries_diff.get('only_in_2') or
        norm1.get('queries') or 
        norm2.get('queries')
    )
    if has_query_data:
        with st.expander("🔍 **Drill Down: Total Results Breakdown** (click to expand)"):
            render_results_breakdown(queries_diff, norm1, norm2)


def _calc_diff(val1, val2, invert=False):
    """Calculate difference string."""
    if not isinstance(val1, (int, float)) or not isinstance(val2, (int, float)):
        return ""
    diff = val2 - val1
    if diff == 0:
        return "="
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff}"


def render_results_breakdown(queries_diff: dict, norm1: dict, norm2: dict):
    """Render detailed breakdown of result differences."""
    results_changed = queries_diff.get('results_changed', [])
    only_in_1 = queries_diff.get('only_in_1', [])
    only_in_2 = queries_diff.get('only_in_2', [])
    
    # Categorize changes
    increased = [q for q in results_changed if q['diff'] > 0]
    decreased = [q for q in results_changed if q['diff'] < 0]
    
    # Calculate totals
    total_increased = sum(q['diff'] for q in increased)
    total_decreased = sum(q['diff'] for q in decreased)
    
    # Results from removed queries (only in log 1)
    removed_results = sum(norm1['queries'].get(q, {}).get('results', 0) for q in only_in_1)
    # Results from new queries (only in log 2)
    added_results = sum(norm2['queries'].get(q, {}).get('results', 0) for q in only_in_2)
    
    # Summary metrics
    st.markdown("##### Impact Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔺 Increased", f"+{total_increased}", f"{len(increased)} queries")
    with col2:
        st.metric("🔻 Decreased", f"{total_decreased}", f"{len(decreased)} queries")
    with col3:
        st.metric("🆕 New Queries", f"+{added_results}", f"{len(only_in_2)} queries")
    with col4:
        st.metric("🗑️ Removed Queries", f"-{removed_results}", f"{len(only_in_1)} queries")
    
    st.markdown("---")
    
    # Detailed tables
    if increased:
        with st.expander(f"🔺 Queries with Increased Results ({len(increased)} queries, +{total_increased} results)"):
            df = pd.DataFrame(increased)
            df = df.sort_values('diff', ascending=False)
            df = df.rename(columns={
                'name': 'Query',
                'results_1': 'Log 1 Results',
                'results_2': 'Log 2 Results',
                'diff': 'Change'
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    if decreased:
        with st.expander(f"🔻 Queries with Decreased Results ({len(decreased)} queries, {total_decreased} results)"):
            df = pd.DataFrame(decreased)
            df = df.sort_values('diff', ascending=True)
            df = df.rename(columns={
                'name': 'Query',
                'results_1': 'Log 1 Results',
                'results_2': 'Log 2 Results',
                'diff': 'Change'
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    if only_in_2:
        with st.expander(f"🆕 New Queries in Log 2 ({len(only_in_2)} queries, +{added_results} results)"):
            new_query_data = []
            for q in only_in_2:
                results = norm2['queries'].get(q, {}).get('results', 0)
                new_query_data.append({'Query': q, 'Results': results})
            if new_query_data:
                df = pd.DataFrame(new_query_data)
                df = df.sort_values('Results', ascending=False)
                st.dataframe(df, use_container_width=True, hide_index=True)
    
    if only_in_1:
        with st.expander(f"🗑️ Removed Queries from Log 1 ({len(only_in_1)} queries, -{removed_results} results)"):
            removed_query_data = []
            for q in only_in_1:
                results = norm1['queries'].get(q, {}).get('results', 0)
                removed_query_data.append({'Query': q, 'Results': results})
            if removed_query_data:
                df = pd.DataFrame(removed_query_data)
                df = df.sort_values('Results', ascending=False)
                st.dataframe(df, use_container_width=True, hide_index=True)


def render_comparison_details(comparison: dict, norm1: dict, norm2: dict):
    """Render detailed comparison tabs."""
    files_diff = comparison['files_diff']
    queries_diff = comparison['queries_diff']
    errors_diff = comparison['errors_diff']
    
    # Count differences
    files_diff_count = len(files_diff['only_in_1']) + len(files_diff['only_in_2'])
    queries_diff_count = len(queries_diff['only_in_1']) + len(queries_diff['only_in_2'])
    results_changed = len(queries_diff['results_changed'])
    
    tab_files, tab_queries, tab_errors = st.tabs([
        f"📁 Files Diff ({files_diff_count})",
        f"🔍 Queries Diff ({queries_diff_count + results_changed})",
        f"🔴 Errors"
    ])
    
    with tab_files:
        render_files_comparison(files_diff)
    
    with tab_queries:
        render_queries_comparison(queries_diff)
    
    with tab_errors:
        render_errors_comparison(errors_diff)


def render_files_comparison(files_diff: dict):
    """Render file differences."""
    st.markdown("#### File Differences")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Only in Log 1", len(files_diff['only_in_1']))
    with col2:
        st.metric("Only in Log 2", len(files_diff['only_in_2']))
    with col3:
        st.metric("In Both", len(files_diff['in_both']))
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 🔴 Only in Log 1 (Removed)")
        if files_diff['only_in_1']:
            for f in files_diff['only_in_1'][:50]:
                st.text(f"- {f}")
            if len(files_diff['only_in_1']) > 50:
                st.caption(f"... and {len(files_diff['only_in_1']) - 50} more")
        else:
            st.success("No files removed")
    
    with col2:
        st.markdown("##### 🟢 Only in Log 2 (Added)")
        if files_diff['only_in_2']:
            for f in files_diff['only_in_2'][:50]:
                st.text(f"+ {f}")
            if len(files_diff['only_in_2']) > 50:
                st.caption(f"... and {len(files_diff['only_in_2']) - 50} more")
        else:
            st.success("No files added")


def render_queries_comparison(queries_diff: dict):
    """Render query differences."""
    st.markdown("#### Query Differences")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Only in Log 1", len(queries_diff['only_in_1']))
    with col2:
        st.metric("Only in Log 2", len(queries_diff['only_in_2']))
    with col3:
        st.metric("In Both", queries_diff['in_both'])
    
    st.markdown("---")
    
    # Queries with changed results
    if queries_diff['results_changed']:
        st.markdown("##### 📊 Results Changed")
        df = pd.DataFrame(queries_diff['results_changed'])
        df = df.rename(columns={
            'name': 'Query',
            'results_1': 'Log 1',
            'results_2': 'Log 2',
            'diff': 'Difference'
        })
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 🔴 Only in Log 1")
        if queries_diff['only_in_1']:
            with st.expander(f"Show {len(queries_diff['only_in_1'])} queries"):
                for q in queries_diff['only_in_1'][:100]:
                    st.text(f"- {q}")
                if len(queries_diff['only_in_1']) > 100:
                    st.caption(f"... and {len(queries_diff['only_in_1']) - 100} more")
        else:
            st.success("No queries removed")
    
    with col2:
        st.markdown("##### 🟢 Only in Log 2")
        if queries_diff['only_in_2']:
            with st.expander(f"Show {len(queries_diff['only_in_2'])} queries"):
                for q in queries_diff['only_in_2'][:100]:
                    st.text(f"+ {q}")
                if len(queries_diff['only_in_2']) > 100:
                    st.caption(f"... and {len(queries_diff['only_in_2']) - 100} more")
        else:
            st.success("No queries added")


def render_errors_comparison(errors_diff: dict):
    """Render error comparison."""
    st.markdown("#### Errors Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Log 1 Errors")
        if errors_diff['errors_1']:
            for err in errors_diff['errors_1']:
                st.error(err)
        else:
            st.success("✅ No errors")
    
    with col2:
        st.markdown("##### Log 2 Errors")
        if errors_diff['errors_2']:
            for err in errors_diff['errors_2']:
                st.error(err)
        else:
            st.success("✅ No errors")


def render_comparison_placeholder():
    """Render placeholder for comparison tab."""
    st.info("📂 Upload two scan log files to compare them")
    
    st.markdown("#### What this comparison provides:")
    st.markdown("""
    - **Auto-Detection**: Automatically detects CxOne vs CxSAST log format
    - **Summary Comparison**: Side-by-side metrics (time, files, queries, results)
    - **File Differences**: See which files were added/removed between scans
    - **Query Differences**: Compare query results, find new/removed queries
    - **Error Comparison**: View errors from both logs side by side
    
    **Use Cases:**
    - Compare scans before/after code changes
    - Compare incremental vs full scans
    - Debug why results differ between environments
    - Track scan performance over time
    """)

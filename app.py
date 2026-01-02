import streamlit as st
from Utils.utils import setup_cxone_config_path

# Page config (must be first Streamlit command)
st.set_page_config(
    page_title="CxOne Manager",
    page_icon="🛡️",
    layout="centered"
)

# Import UI and services
from ui.styles import apply_styles
from ui.components import render_header, render_connection_status, render_disconnected_message
from services.connection import init_session_state, test_and_connect

# Import tabs
from tabs import presets, projects, scans, audit, log_analyzer

# Apply styles
apply_styles()

# Initialize session state
init_session_state()

# Setup config
config_path = setup_cxone_config_path()

# Render header
render_header()

# Render connection status and handle connect button
if render_connection_status(error_message=st.session_state.error_message):
    with st.spinner("Connecting..."):
        test_and_connect()
    st.rerun()

# Main content with tabs
if st.session_state.connected:
    st.markdown("---")
    
    # Create tabs
    tab_presets, tab_projects, tab_scans, tab_audit, tab_logs = st.tabs([
        "📋 Presets",
        "📁 Projects",
        "🔍 Scans",
        "📝 Audit",
        "📄 Log Analyzer"
    ])
    
    with tab_presets:
        presets.render()
    
    with tab_projects:
        projects.render()
    
    with tab_scans:
        scans.render()
    
    with tab_audit:
        audit.render()
    
    with tab_logs:
        log_analyzer.render()

else:
    render_disconnected_message(config_path)

import streamlit as st

def render():
    """Render the Projects tab."""
    st.markdown("### Projects")
    
    # Subtabs for Projects
    proj_list, proj_details, proj_settings = st.tabs([
        "📋 List",
        "🔍 Details", 
        "⚙️ Settings"
    ])
    
    with proj_list:
        render_list()
    
    with proj_details:
        render_details()
    
    with proj_settings:
        render_settings()

def render_list():
    """Render the project list subtab."""
    st.markdown("#### All Projects")
    st.info("🚧 Coming soon - List all projects")

def render_details():
    """Render the project details subtab."""
    st.markdown("#### Project Details")
    st.info("🚧 Coming soon - View project details")

def render_settings():
    """Render the project settings subtab."""
    st.markdown("#### Project Settings")
    st.info("🚧 Coming soon - Manage project settings")


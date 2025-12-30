import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from services.audit_events import fetch_audit_events, to_excel

def render():
    """Render the Audit tab with subtabs."""
    st.markdown("### Audit")
    
    # Subtabs
    sub_events, sub_events_scans = st.tabs([
        "📋 Audit Events",
        "📋🔍 Audit Events and Scans"
    ])
    
    with sub_events:
        render_audit_events()
    
    with sub_events_scans:
        render_audit_events_and_scans()

def render_audit_events():
    """Render the Audit Events subtab."""
    st.markdown("#### Audit Events")
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            max_value=datetime.now(),
            key="audit_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            max_value=datetime.now(),
            key="audit_end_date"
        )
    
    # Options
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        fetch_links = st.checkbox("Fetch historical data (links)", value=True, key="audit_fetch_links")
    with col_opt2:
        thread_count = st.number_input("Threads", min_value=1, max_value=10, value=4, key="audit_threads")
    
    # Fetch button
    if st.button("🔍 Fetch Audit Events", use_container_width=True, key="audit_fetch_btn"):
        with st.spinner("Fetching audit events..." + (" (including historical data)" if fetch_links else "")):
            try:
                result = fetch_audit_events(
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    fetch_links=fetch_links,
                    thread_count=thread_count
                )
                st.session_state.audit_events = result
                st.session_state.audit_events_ready = True
            except Exception as e:
                st.exception(e)
    
    # Display results
    if st.session_state.get('audit_events_ready') and st.session_state.get('audit_events'):
        result = st.session_state.audit_events
        
        st.markdown("---")
        
        # Stats
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Total Events", result.get('total_events', 0))
        with col_s2:
            st.metric("Links Fetched", f"{result.get('links_fetched', 0)} / {result.get('total_links', 0)}")
        with col_s3:
            st.metric("Date Range", f"{start_date} to {end_date}")
        
        st.markdown("#### 📊 Events")
        
        events = result.get('events', [])
        if events:
            df = pd.DataFrame(events)
            
            # Reorder columns if possible
            preferred_order = ['formatted_date', 'event_date', 'event_type', 'action_type', 'audit_resource', 'action_user_id']
            existing_cols = [c for c in preferred_order if c in df.columns]
            other_cols = [c for c in df.columns if c not in preferred_order]
            df = df[existing_cols + other_cols]
            
            st.dataframe(df, use_container_width=True)
            st.caption(f"{len(df)} events")
            
            # Download button
            excel_data = to_excel(df)
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_data,
                file_name=f"audit_events_{start_date}_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="audit_download_btn"
            )
        else:
            st.info("No events found for the selected date range.")
        
        # Debug expander
        # with st.expander("🔍 Debug Info"):
        #     st.json({k: str(v)[:500] if isinstance(v, list) else v for k, v in result.items()})

def render_audit_events_and_scans():
    """Render the Audit Events and Scans subtab."""
    st.markdown("#### Audit Events and Scans")
    st.info("🚧 Coming soon - Audit Events and Scans features")

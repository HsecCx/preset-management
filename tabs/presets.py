import streamlit as st
import pandas as pd
from services.presets import get_preset_data, to_excel, fetch_presets

def render():
    """Render the Presets tab with subtabs."""
    st.markdown("### Presets")
    
    # Lazy load presets if not already loaded
    if not st.session_state.presets:
        with st.spinner("Loading presets..."):
            fetch_presets()
    
    st.caption(f"{len(st.session_state.presets)} presets available")
    
    # Subtabs
    sub_export, sub_manage = st.tabs([
        "📤 Export",
        "⚙️ Manage"
    ])
    
    with sub_export:
        render_export()
    
    with sub_manage:
        render_manage()

def render_export():
    """Render the Export Presets subtab."""
    st.markdown("#### Export Preset Query IDs")
    
    selected_presets = st.multiselect(
        "Choose presets to export",
        options=st.session_state.presets,
        placeholder="Select one or more presets...",
        key="preset_select"
    )
    
    if selected_presets:
        st.markdown(f"**{len(selected_presets)}** preset(s) selected")
        
        # Limit option
        col_limit1, col_limit2 = st.columns([1, 2])
        with col_limit1:
            use_limit = st.checkbox("Limit query IDs", value=False, key="preset_limit_check")
        with col_limit2:
            limit_value = st.number_input(
                "Max IDs per preset",
                min_value=1,
                max_value=100000,
                value=100,
                disabled=not use_limit,
                key="preset_limit_value"
            )
        
        # Export button
        if st.button("📊 Generate Export", use_container_width=True, key="preset_export_btn"):
            with st.spinner("Fetching preset data..."):
                try:
                    limit = limit_value if use_limit else None
                    results = get_preset_data(selected_presets, limit=limit)
                    st.session_state.export_results = results
                    st.session_state.export_ready = True
                except Exception as e:
                    st.error(f"Export failed: {e}")
        
        # Download section
        if st.session_state.get('export_ready') and st.session_state.get('export_results'):
            results = st.session_state.export_results
            
            st.markdown("---")
            st.markdown("#### 📥 Download")
            
            # Show preview
            df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in results.items()]))
            st.dataframe(df.head(10), use_container_width=True)
            
            total_ids = sum(len(v) for v in results.values())
            st.caption(f"Showing first 10 rows • {total_ids} total query IDs")
            
            # Download button
            excel_data = to_excel(results)
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_data,
                file_name="preset_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="preset_download_btn"
            )

def render_manage():
    """Render the Manage Presets subtab."""
    st.markdown("#### Manage Presets")
    st.info("🚧 Coming soon - Preset management features")
    st.markdown("""
    Planned features:
    - View preset details
    - Create custom presets
    - Clone/modify existing presets
    """)

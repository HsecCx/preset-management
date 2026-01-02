import streamlit as st
import pandas as pd
from services.presets import (
    get_preset_data, to_excel, to_xml, fetch_presets,
    get_preset_data_with_sast_ids, to_sast_xml
)

def render():
    """Render the Presets tab with subtabs."""
    st.markdown("### Presets")
    
    # Lazy load presets if not already loaded
    if not st.session_state.presets:
        with st.spinner("Loading presets..."):
            fetch_presets()
    
    st.caption(f"{len(st.session_state.presets)} presets available")
    
    # Subtabs
    sub_export, sub_convert, sub_manage = st.tabs([
        "📤 Export",
        "🔄 Convert to CxSAST",
        "⚙️ Manage"
    ])
    
    with sub_export:
        render_export()
    
    with sub_convert:
        render_convert_to_sast()
    
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
        
        # Format and limit options
        col_format, col_limit1, col_limit2 = st.columns([1, 1, 1])
        with col_format:
            export_format = st.selectbox(
                "Export format",
                options=["Excel", "XML"],
                key="preset_export_format"
            )
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
            
            # Show preview based on format
            if export_format == "Excel":
                flat_data = {name: data['query_ids'] for name, data in results.items()}
                df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in flat_data.items()]))
                st.dataframe(df.head(10), use_container_width=True)
                
                total_ids = sum(len(data['query_ids']) for data in results.values())
                st.caption(f"Showing first 10 rows • {total_ids} total query IDs")
                
                # Download Excel
                excel_data = to_excel(results)
                st.download_button(
                    label="⬇️ Download Excel",
                    data=excel_data,
                    file_name="preset_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="preset_download_btn"
                )
            else:
                # XML preview
                xml_data = to_xml(results)
                xml_preview = xml_data.getvalue().decode('utf-8')
                xml_data.seek(0)  # Reset for download
                
                st.code(xml_preview[:2000] + ("..." if len(xml_preview) > 2000 else ""), language="xml")
                
                total_ids = sum(len(data['query_ids']) for data in results.values())
                st.caption(f"{len(results)} preset(s) • {total_ids} total query IDs")
                
                # Download XML
                st.download_button(
                    label="⬇️ Download XML",
                    data=xml_data,
                    file_name="preset_export.xml",
                    mime="application/xml",
                    use_container_width=True,
                    key="preset_download_xml_btn"
                )

def render_convert_to_sast():
    """Render the Convert to CxSAST subtab."""
    st.markdown("#### Convert Preset to CxSAST Format")
    st.caption("Export presets with legacy CxSAST query IDs for use with on-premise Checkmarx")
    
    selected_presets = st.multiselect(
        "Choose presets to convert",
        options=st.session_state.presets,
        placeholder="Select one or more presets...",
        key="convert_preset_select"
    )
    
    if selected_presets:
        st.markdown(f"**{len(selected_presets)}** preset(s) selected")
        
        # Convert button
        if st.button("🔄 Convert to CxSAST", use_container_width=True, key="convert_btn"):
            with st.spinner("Fetching preset data and mapping to CxSAST IDs..."):
                try:
                    results = get_preset_data_with_sast_ids(selected_presets)
                    st.session_state.convert_results = results
                    st.session_state.convert_ready = True
                except Exception as e:
                    st.error(f"Conversion failed: {e}")
        
        # Download section
        if st.session_state.get('convert_ready') and st.session_state.get('convert_results'):
            results = st.session_state.convert_results
            
            st.markdown("---")
            st.markdown("#### 📊 Conversion Summary")
            
            # Show stats for each preset
            for name, data in results.items():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Queries", data['total_queries'])
                with col2:
                    st.metric("Mapped to CxSAST", data['mapped_queries'])
                with col3:
                    st.metric("Unmapped", data['unmapped_queries'])
                
                if data['unmapped_queries'] > 0:
                    st.warning(f"⚠️ {data['unmapped_queries']} queries in '{name}' have no CxSAST equivalent")
            
            st.markdown("---")
            st.markdown("#### 📥 Download")
            
            # XML preview
            xml_data = to_sast_xml(results)
            xml_preview = xml_data.getvalue().decode('utf-8')
            xml_data.seek(0)  # Reset for download
            
            st.code(xml_preview[:2000] + ("..." if len(xml_preview) > 2000 else ""), language="xml")
            
            total_sast_ids = sum(len(data['sast_query_ids']) for data in results.values())
            st.caption(f"{len(results)} preset(s) • {total_sast_ids} CxSAST query IDs")
            
            # Download XML
            st.download_button(
                label="⬇️ Download CxSAST XML",
                data=xml_data,
                file_name="preset_cxsast.xml",
                mime="application/xml",
                use_container_width=True,
                key="convert_download_btn"
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

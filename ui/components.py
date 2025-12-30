import streamlit as st

def render_header():
    """Render the app header."""
    st.markdown('<p class="main-title">🛡️ CxOne Manager</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Checkmarx One API Tools</p>', unsafe_allow_html=True)

def render_connection_status(error_message: str = None):
    """Render the connection status card."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.session_state.connected:
            st.markdown('''
            <div class="status-card status-connected">
                <strong style="color: #00ff88;">● Connected</strong><br>
                <span style="color: #b0b0b0; font-size: 0.85rem;">Ready</span>
            </div>
            ''', unsafe_allow_html=True)
        else:
            error_text = error_message or "Not connected"
            st.markdown(f'''
            <div class="status-card status-disconnected">
                <strong style="color: #ff4757;">● Disconnected</strong><br>
                <span style="color: #b0b0b0; font-size: 0.85rem;">{error_text}</span>
            </div>
            ''', unsafe_allow_html=True)
    
    with col2:
        return st.button("🔌 Connect", use_container_width=True)

def render_disconnected_message(config_path: str):
    """Render the disconnected state message."""
    st.markdown("---")
    st.info(f"📁 Config file location: `{config_path}`")
    st.markdown("Please ensure your `config.ini` is properly configured and click **Connect**.")


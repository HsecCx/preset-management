import streamlit as st
from requests.exceptions import MissingSchema, ConnectionError

def test_and_connect() -> bool:
    """Test connection with a minimal API call."""
    try:
        import CheckmarxPythonSDK.CxOne.sastQueriesAuditPresetsAPI as presetsAPI
        # Minimal call just to verify connection works
        presetsAPI.get_presets(limit=1)
        st.session_state.connected = True
        st.session_state.error_message = None
        return True
    except MissingSchema:
        st.session_state.error_message = "Invalid configuration: URL is missing or malformed."
        st.session_state.connected = False
        return False
    except ConnectionError:
        st.session_state.error_message = "Connection failed: Unable to reach the server."
        st.session_state.connected = False
        return False
    except Exception as e:
        st.session_state.error_message = f"Connection failed: {str(e)}"
        st.session_state.connected = False
        return False

def init_session_state():
    """Initialize session state variables."""
    if 'connected' not in st.session_state:
        st.session_state.connected = False
    if 'presets' not in st.session_state:
        st.session_state.presets = []
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None


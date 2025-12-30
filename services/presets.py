import streamlit as st
import pandas as pd
from io import BytesIO
import CheckmarxPythonSDK.CxOne.sastQueriesAuditPresetsAPI as presetsAPI

def fetch_presets():
    """Fetch and cache preset names in session state."""
    result = presetsAPI.get_presets(limit=1000)
    st.session_state.presets = [p.name for p in result.presets]

def get_preset_data(preset_names: list, limit: int = None) -> dict:
    """Fetch preset data for selected presets."""
    result = presetsAPI.get_presets(limit=1000)
    preset_map = {p.name.lower(): p.id for p in result.presets}
    
    results = {}
    for name in preset_names:
        preset_id = preset_map.get(name.lower())
        if preset_id:
            detailed = presetsAPI.get_preset_by_id(preset_id)
            query_ids = [str(id) for id in detailed.query_ids]
            if limit:
                query_ids = query_ids[:limit]
            results[name] = query_ids
    return results

def to_excel(results: dict) -> BytesIO:
    """Convert results to Excel bytes."""
    df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in results.items()]))
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output


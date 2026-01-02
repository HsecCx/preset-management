import streamlit as st
import pandas as pd
from io import BytesIO
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging
import CheckmarxPythonSDK.CxOne.sastQueriesAuditPresetsAPI as presetsAPI
import CheckmarxPythonSDK.CxOne.sastQueriesAPI as queriesAPI

logger = logging.getLogger(__name__)

def fetch_presets():
    """Fetch and cache preset names in session state."""
    result = presetsAPI.get_presets(limit=1000)
    st.session_state.presets = [p.name for p in result.presets]
    # Cache full preset data for ID lookup
    st.session_state.preset_map = {p.name.lower(): {'id': p.id, 'name': p.name} for p in result.presets}

def get_preset_data(preset_names: list, limit: int = None) -> dict:
    """Fetch preset data for selected presets."""
    result = presetsAPI.get_presets(limit=1000)
    preset_map = {p.name.lower(): {'id': p.id, 'name': p.name} for p in result.presets}
    
    results = {}
    for name in preset_names:
        preset_info = preset_map.get(name.lower())
        if preset_info:
            detailed = presetsAPI.get_preset_by_id(preset_info['id'])
            query_ids = [str(id) for id in detailed.query_ids]
            if limit:
                query_ids = query_ids[:limit]
            results[name] = {
                'id': preset_info['id'],
                'name': preset_info['name'],
                'query_ids': query_ids
            }
    return results

def to_excel(results: dict) -> BytesIO:
    """Convert results to Excel bytes."""
    # Flatten for Excel - just query IDs with preset names as columns
    flat_data = {name: data['query_ids'] for name, data in results.items()}
    df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in flat_data.items()]))
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output

def to_xml(results: dict) -> BytesIO:
    """Convert results to XML bytes."""
    root = ET.Element("Presets")
    
    for name, data in results.items():
        preset_elem = ET.SubElement(root, "Preset")
        preset_elem.set("Id", str(data['id']))
        preset_elem.set("Name", data['name'])
        
        query_ids_elem = ET.SubElement(preset_elem, "OtherQueryIds")
        for query_id in data['query_ids']:
            query_id_elem = ET.SubElement(query_ids_elem, "OtherQueryId")
            query_id_elem.text = str(query_id)
    
    # Pretty print XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    # Remove extra blank lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    pretty_xml = '\n'.join(lines)
    
    output = BytesIO()
    output.write(pretty_xml.encode('utf-8'))
    output.seek(0)
    return output


def get_ast_to_sast_mapping() -> dict:
    """Get mapping from CxOne (AST) query IDs to CxSAST query IDs."""
    mappings = queriesAPI.get_mapping_between_ast_and_sast_query_ids()
    return {m['astId']: m['sastId'] for m in mappings} if mappings else {}


def get_preset_data_with_sast_ids(preset_names: list) -> dict:
    """
    Fetch preset data and convert query IDs to CxSAST format.
    
    Returns dict with preset data including both CxOne and CxSAST IDs.
    """
    result = presetsAPI.get_presets(limit=1000)
    preset_map = {p.name.lower(): {'id': p.id, 'name': p.name} for p in result.presets}
    
    # Get the AST -> SAST mapping
    ast_to_sast = get_ast_to_sast_mapping()
    logger.info(f"Loaded {len(ast_to_sast)} AST->SAST mappings")
    
    results = {}
    for name in preset_names:
        preset_info = preset_map.get(name.lower())
        if preset_info:
            detailed = presetsAPI.get_preset_by_id(preset_info['id'])
            
            # Convert AST IDs to SAST IDs
            sast_ids = []
            unmapped_count = 0
            for ast_id in detailed.query_ids:
                sast_id = ast_to_sast.get(str(ast_id))
                if sast_id:
                    sast_ids.append(sast_id)
                else:
                    unmapped_count += 1
            
            if unmapped_count > 0:
                logger.warning(f"Preset '{name}': {unmapped_count} queries have no CxSAST mapping")
            
            results[name] = {
                'id': preset_info['id'],
                'name': preset_info['name'],
                'sast_query_ids': sast_ids,
                'total_queries': len(detailed.query_ids),
                'mapped_queries': len(sast_ids),
                'unmapped_queries': unmapped_count
            }
    
    return results


def to_sast_xml(results: dict) -> BytesIO:
    """Convert results to CxSAST format XML with SAST query IDs."""
    root = ET.Element("Presets")
    
    for name, data in results.items():
        preset_elem = ET.SubElement(root, "Preset")
        preset_elem.set("Id", str(data['id']))
        preset_elem.set("Name", data['name'])
        
        query_ids_elem = ET.SubElement(preset_elem, "OtherQueryIds")
        for query_id in data['sast_query_ids']:
            query_id_elem = ET.SubElement(query_ids_elem, "OtherQueryId")
            query_id_elem.text = str(query_id)
    
    # Pretty print XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    # Remove extra blank lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    pretty_xml = '\n'.join(lines)
    
    output = BytesIO()
    output.write(pretty_xml.encode('utf-8'))
    output.seek(0)
    return output


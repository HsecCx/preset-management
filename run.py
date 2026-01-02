from Utils.utils import setup_cxone_config_path
from typing import List, Dict, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import logging
import sys
from requests.exceptions import MissingSchema, ConnectionError, HTTPError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
config_path = setup_cxone_config_path()

# Batch size for description API requests
DESCRIPTION_BATCH_SIZE = 100
DESCRIPTION_THREAD_COUNT = 4

import CheckmarxPythonSDK.CxOne.sastQueriesAuditPresetsAPI as presetsAPI
import CheckmarxPythonSDK.CxOne.sastQueriesAPI as queriesAPI


def test_connection() -> bool:
    """Test if the API connection works."""
    try:
        presetsAPI.get_presets(limit=1)
        return True
    except MissingSchema:
        logger.error("Invalid configuration: URL is missing or malformed. Please check your config.ini. Please review the sample config.ini.sample file for the correct format.")
        return False
    except ConnectionError:
        logger.error("Connection failed: Unable to reach the server. Please check your config.ini. Please review the sample config.ini.sample file for the correct format.")
        return False
    except HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


def get_preset_list():
    return presetsAPI.get_presets(limit=1000)

def get_preset_id_by_name(preset_name: str):
    preset_list = get_preset_list()
    for preset in preset_list.presets:
        if preset.name.lower() == preset_name.lower():
            return preset.id
    return None

def get_detailed_preset_info(preset_id: int):
    return presetsAPI.get_preset_by_id(preset_id)

def export_preset_data(preset_name: Union[str, list[str]]):
    names = [preset_name] if isinstance(preset_name, str) else preset_name
    results = {}
    for name in names:
        preset_id = get_preset_id_by_name(name)
        if preset_id is None:
            logger.warning(f"Preset '{name}' not found, skipping...")
            continue
        detailed_preset_info = get_detailed_preset_info(preset_id)
        results[name] = [str(id) for id in detailed_preset_info.query_ids]
    return results

def get_ast_to_sast_mapping() -> Dict[str, str]:
    """Get mapping from AST query IDs to SAST query IDs."""
    mappings = queriesAPI.get_mapping_between_ast_and_sast_query_ids()
    return {m['astId']: m['sastId'] for m in mappings} if mappings else {}

def get_sast_to_ast_mapping() -> Dict[str, str]:
    """Get mapping from SAST query IDs to AST query IDs."""
    mappings = queriesAPI.get_mapping_between_ast_and_sast_query_ids()
    return {m['sastId']: m['astId'] for m in mappings} if mappings else {}

def _fetch_single_batch(batch: List[str], batch_num: int, total_batches: int) -> List:
    """Fetch a single batch of descriptions. Used by thread pool."""
    logger.info(f"Fetching descriptions batch {batch_num}/{total_batches} ({len(batch)} queries)...")
    try:
        return queriesAPI.get_sast_query_description(ids=batch)
    except Exception as e:
        logger.warning(f"Failed to fetch batch {batch_num}: {e}")
        return []


def fetch_descriptions_batched(
    sast_ids: List[str], 
    batch_size: int = DESCRIPTION_BATCH_SIZE,
    thread_count: int = DESCRIPTION_THREAD_COUNT
) -> Dict[str, object]:
    """
    Fetch query descriptions in batches using multiple threads.
    
    Args:
        sast_ids: List of SAST query IDs to fetch descriptions for
        batch_size: Number of IDs to fetch per API call
        thread_count: Number of concurrent threads (default 4)
        
    Returns:
        Dict mapping SAST ID to QueryDescription object
    """
    desc_lookup = {}
    
    # Split into batches
    batches = []
    for i in range(0, len(sast_ids), batch_size):
        batches.append(sast_ids[i:i + batch_size])
    
    total_batches = len(batches)
    logger.info(f"Fetching {len(sast_ids)} descriptions in {total_batches} batches with {thread_count} threads...")
    
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = {
            executor.submit(_fetch_single_batch, batch, idx + 1, total_batches): idx
            for idx, batch in enumerate(batches)
        }
        
        for future in as_completed(futures):
            try:
                descriptions = future.result()
                for desc in descriptions:
                    desc_lookup[desc.query_id] = desc
            except Exception as e:
                batch_idx = futures[future]
                logger.warning(f"Batch {batch_idx + 1} failed: {e}")
    
    logger.info(f"Fetched {len(desc_lookup)} descriptions")
    return desc_lookup


def export_preset_with_mapping(
    preset_name: Union[str, list[str]], 
    include_descriptions: bool = True,
    batch_size: int = DESCRIPTION_BATCH_SIZE,
    thread_count: int = DESCRIPTION_THREAD_COUNT
) -> Dict[str, Dict[str, dict]]:
    """
    Export preset query IDs with their AST<->SAST mappings and descriptions.
    
    Args:
        preset_name: Single preset name or list of preset names
        include_descriptions: Whether to fetch query descriptions
        batch_size: Number of IDs to fetch per description API call
        thread_count: Number of concurrent threads for fetching descriptions
    
    Returns:
        Dict with preset names as keys, each containing a dict of:
        {
            ast_id: {
                'sast_id': str or None,
                'query_name': str or None,
                'result_description': str or None,
                'risk': str or None,
                'cause': str or None,
                'general_recommendations': str or None
            }
        }
    """
    names = [preset_name] if isinstance(preset_name, str) else preset_name
    ast_to_sast = get_ast_to_sast_mapping()
    
    results = {}
    for name in names:
        preset_id = get_preset_id_by_name(name)
        if preset_id is None:
            logger.warning(f"Preset '{name}' not found, skipping...")
            continue
        
        detailed_preset_info = get_detailed_preset_info(preset_id)
        query_ids = [str(id) for id in detailed_preset_info.query_ids]
        
        # Map each query ID to its SAST equivalent if it exists
        mapping = {}
        
        for ast_id in query_ids:
            sast_id = ast_to_sast.get(ast_id)
            mapping[ast_id] = {
                'sast_id': sast_id,
                'query_name': None,
                'result_description': None,
                'risk': None,
                'cause': None,
                'general_recommendations': None
            }
        
        # Fetch descriptions using AST IDs (the preset query IDs)
        if include_descriptions and query_ids:
            desc_lookup = fetch_descriptions_batched(query_ids, batch_size, thread_count)
            
            # Enrich mapping with descriptions (keyed by AST ID)
            for ast_id, data in mapping.items():
                if ast_id in desc_lookup:
                    desc = desc_lookup[ast_id]
                    data['query_name'] = desc.query_name
                    data['result_description'] = desc.result_description
                    data['risk'] = desc.risk
                    data['cause'] = desc.cause
                    data['general_recommendations'] = desc.general_recommendations
        
        results[name] = mapping
    
    return results

def export_mapping_to_excel(mapped_results: Dict[str, Dict[str, dict]], output_path: str = "preset_query_mapping.xlsx"):
    """
    Export preset mapping to Excel with Query Name, CxOne Query ID, and CxSAST Query ID.
    
    Creates one sheet per preset.
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for preset_name, mapping in mapped_results.items():
            rows = []
            for ast_id, data in mapping.items():
                rows.append({
                    'Query Name': data['query_name'] or '',
                    'CxOne Query ID': ast_id,
                    'CxSAST Query ID': data['sast_id'] or ''
                })
            
            df = pd.DataFrame(rows)
            # Sanitize sheet name (Excel has 31 char limit and special char restrictions)
            sheet_name = preset_name[:31].replace('/', '-').replace('\\', '-').replace('*', '-')
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            logger.info(f"Added sheet '{sheet_name}' with {len(rows)} queries")
    
    logger.info(f"Exported to {output_path}")

if __name__ == "__main__":
    if not test_connection():
        logger.error(f"Please update your config file at: {config_path}")
        sys.exit(1)
    
    preset_name = ["Checkmarx Default"]
    
    # Get preset query IDs with AST->SAST mapping and descriptions
    mapped_results = export_preset_with_mapping(preset_name, include_descriptions=True)
    
    for name, mapping in mapped_results.items():
        logger.info(f"Preset: {name}")
        logger.info(f"  Total queries: {len(mapping)}")
        
        mapped_count = sum(1 for v in mapping.values() if v['sast_id'] is not None)
        with_desc = sum(1 for v in mapping.values() if v['query_name'] is not None)
        
        logger.info(f"  With SAST mapping: {mapped_count}")
        logger.info(f"  With descriptions: {with_desc}")
        logger.info(f"  Without mapping: {len(mapping) - mapped_count}")
    
    # Export to Excel
    export_mapping_to_excel(mapped_results)
    
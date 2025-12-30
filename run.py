from Utils.utils import setup_cxone_config_path
from typing import List, Dict, Union
import pandas as pd
import logging
import sys
from requests.exceptions import MissingSchema, ConnectionError, HTTPError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
config_path = setup_cxone_config_path()

import CheckmarxPythonSDK.CxOne.sastQueriesAuditPresetsAPI as presetsAPI


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

def export_to_excel(results: Dict[str, list], output_path: str = "preset_export.xlsx"):
    df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in results.items()]))
    df.to_excel(output_path, index=False)
    logger.info(f"Exported to {output_path}")

if __name__ == "__main__":
    if not test_connection():
        logger.error(f"Please update your config file at: {config_path}")
        sys.exit(1)
    
    preset_name = ["Checkmarx Default"]
    results = export_preset_data(preset_name)
    export_to_excel(results)
    
import os


def find_project_root():
    """Find the project root by looking for marker files."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):  # Stop at filesystem root
        if os.path.exists(os.path.join(current_dir, 'README.md')) or os.path.exists(os.path.join(current_dir, 'config.ini')):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    return os.getcwd()  # Fallback to current working directory


def set_config_environment():
    project_root = find_project_root()
    os.environ['checkmarx_config_path'] = os.path.join(project_root, 'config.ini')


def mask_output_string(id_value: str, visible_chars: int = 4) -> str:
    """Mask an ID showing only the last N characters
    
    Args:
        id_value: The ID to mask
        visible_chars: Number of characters to show at the end (default: 4)
        
    Returns:
        Masked ID in format '***1234'
    """
    if not id_value or len(id_value) <= visible_chars:
        return id_value
    return f"***{id_value[-visible_chars:]}"

def setup_cxone_config_path():
    # Setup config path
    project_root = find_project_root()
    os.environ['checkmarx_config_path'] = os.path.join(project_root, 'config.ini')

    return os.environ['checkmarx_config_path']
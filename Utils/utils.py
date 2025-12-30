import os
import configparser

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
    if not os.path.exists(os.environ['checkmarx_config_path']):
        print(f"Config file not found at {os.environ['checkmarx_config_path']}. Would you like to create a new config file? (y/n)")
        if input().lower() == 'y':
            create_new_config_file()
            print(f"Config file created at {os.environ['checkmarx_config_path']}")
        else:
            print(f"Config file not found at {os.environ['checkmarx_config_path']}. Please create a new config file.")
            exit(1)
    return os.environ['checkmarx_config_path']

def create_new_config_file():
    config = configparser.ConfigParser()
    config.add_section('CxOne')
    config.set('CxOne', 'access_control_url', input('Enter the access control URL: '))
    config.set('CxOne', 'server', input('Enter the server URL: '))
    config.set('CxOne', 'tenant_name', input('Enter the tenant name: '))
    config.set('CxOne', 'grant_type', input('Enter the grant type: '))
    config.set('CxOne', 'client_id', input('Enter the client ID: '))
    config.set('CxOne', 'client_secret', input('Enter the client secret: '))
    config.set('CxOne', 'username', input('Enter the username: '))
    config.set('CxOne', 'password', input('Enter the password: '))
    config.set('CxOne', 'refresh_token', input('Enter the refresh token: '))
    with open(os.environ['checkmarx_config_path'], 'w') as configfile:
        config.write(configfile)

def validate_config(config_path: str) -> tuple[bool, list[str]]:
    """Validate that the config file has required values.
    
    Returns:
        tuple: (is_valid, list of missing/empty fields)
    """
    config = configparser.ConfigParser()
    config.read(config_path)
    
    errors = []
    
    if not config.has_section('CxOne'):
        return False, ["Missing [CxOne] section"]
    
    # Required fields for API connection
    required_fields = ['access_control_url', 'server', 'tenant_name']
    for field in required_fields:
        value = config.get('CxOne', field, fallback='').strip()
        if not value:
            errors.append(f"'{field}' is empty or missing")
    
    # Check authentication - need either client credentials OR username/password
    client_id = config.get('CxOne', 'client_id', fallback='').strip()
    client_secret = config.get('CxOne', 'client_secret', fallback='').strip()
    username = config.get('CxOne', 'username', fallback='').strip()
    password = config.get('CxOne', 'password', fallback='').strip()
    refresh_token = config.get('CxOne', 'refresh_token', fallback='').strip()
    
    has_client_creds = client_id and client_secret
    has_user_creds = username and password
    has_refresh = bool(refresh_token)
    
    if not (has_client_creds or has_user_creds or has_refresh):
        errors.append("No valid authentication: provide client_id+client_secret, username+password, or refresh_token")
    
    return len(errors) == 0, errors
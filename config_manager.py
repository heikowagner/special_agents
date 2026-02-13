"""
Configuration Manager Module
Handles loading configuration from both config files and environment variables
Environment variables take precedence over config file values
"""
import logging
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration from files and environment variables"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file (default: config.json in workspace root)
        """
        load_dotenv()
        self.config_file = Path(config_file)
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file and environment variables"""
        # Start with file config
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
        else:
            logger.warning(f"Config file not found at {self.config_file}, using environment variables only")
    
    def get_email_config(self) -> Dict[str, Any]:
        """
        Get email configuration
        Environment variables override config file values
        """
        config = {
            'imap_server': self._get_value('email', 'imap_server', 'IMAP_SERVER', 'imap.gmail.com'),
            'imap_port': int(self._get_value('email', 'imap_port', 'IMAP_PORT', 993)),
            'email_address': self._get_value('email', 'email_address', 'EMAIL_ADDRESS', None),
            'password': self._get_value('email', 'password', 'EMAIL_PASSWORD', None),
        }
        
        # Validate required fields
        if not config['email_address'] or not config['password']:
            raise ValueError("Email address and password are required in config or environment variables")
        
        return config
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration
        Environment variables override config file values
        """
        config = {
            'api_key': self._get_value('llm', 'api_key', 'OPENAI_API_KEY', None),
            'model': self._get_value('llm', 'model', 'LLM_MODEL', 'gpt-4o-mini'),
            'url': self._get_value('llm', 'url', 'LLM_URL', 'http://127.0.0.1:1234'),
        }
        
        # Validate required fields
        if not config['api_key']:
            raise ValueError("LLM API key is required in config or environment variables")
        
        return config
    
    def get_app_config(self) -> Dict[str, Any]:
        """
        Get application configuration
        Environment variables override config file values
        """
        return {
            'process_unread_only': self._get_bool_value('app', 'process_unread_only', 'PROCESS_UNREAD_ONLY', True),
            'max_emails': int(self._get_value('app', 'max_emails', 'MAX_EMAILS_TO_PROCESS', 50)),
            'enable_auto_optout': self._get_bool_value('app', 'enable_auto_optout', 'ENABLE_AUTO_OPTOUT', True),
        }
    
    def _get_value(self, section: str, key: str, env_var: str, default: Any = None) -> Any:
        """
        Get configuration value from environment variable first, then config file
        
        Args:
            section: Section in config file
            key: Key within section
            env_var: Environment variable name
            default: Default value if not found
        
        Returns:
            Configuration value
        """
        # Check environment variable first
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value
        
        # Check config file
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        
        # Return default
        return default
    
    def _get_bool_value(self, section: str, key: str, env_var: str, default: bool = False) -> bool:
        """
        Get boolean configuration value
        
        Args:
            section: Section in config file
            key: Key within section
            env_var: Environment variable name
            default: Default value if not found
        
        Returns:
            Boolean configuration value
        """
        value = self._get_value(section, key, env_var, default)
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        
        return default
    
    @staticmethod
    def create_sample_config(filepath: str = "config.json"):
        """
        Create a sample configuration file
        
        Args:
            filepath: Path where to create the sample config file
        """
        sample_config = {
            "email": {
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "email_address": "your-email@gmail.com",
                "password": "your-app-password"
            },
            "llm": {
                "api_key": "your-openai-api-key",
                "model": "gpt-4o-mini",
                "url": "http://127.0.0.1:1234"
            },
            "app": {
                "process_unread_only": True,
                "max_emails": 50,
                "enable_auto_optout": True
            }
        }
        
        config_path = Path(filepath)
        with open(config_path, 'w') as f:
            json.dump(sample_config, f, indent=2)
        
        # Make it readable only by owner for security
        config_path.chmod(0o600)
        logger.info(f"Created sample configuration file at {filepath}")
        print(f"\n✓ Sample config file created at {filepath}")
        print("⚠️  Please edit the file with your actual credentials before running the app")

import os
import yaml
from easydict import EasyDict as edict
from typing import Optional, Dict, Any

class YamlParser(edict):
    """
    A utility class to handle YAML configuration files and dictionaries, 
    allowing for easy merging and nested structure parsing.
    """

    def __init__(self, cfg_dict: Optional[Dict[str, Any]] = None, config_file: Optional[str] = None):
        """
        Initialize the YamlParser object with an optional configuration dictionary or YAML file.

        Args:
            cfg_dict (dict, optional): Initial configuration as a dictionary. Defaults to None.
            config_file (str, optional): Path to a YAML configuration file. Defaults to None.
        """
        initial_config = cfg_dict or {}

        if config_file:
            self._ensure_file_exists(config_file)
            yaml_config = self._load_yaml_file(config_file)
            initial_config.update(yaml_config)

        super().__init__(initial_config)

    def merge_from_file(self, config_file: str):
        """
        Merge additional configuration from a YAML file.

        Args:
            config_file (str): Path to the YAML file.
        """
        self._ensure_file_exists(config_file)
        new_config = self._load_yaml_file(config_file)
        self.update(new_config)

    def merge_from_dict(self, cfg_dict: Dict[str, Any]):
        """
        Merge additional configuration from a dictionary.

        Args:
            cfg_dict (dict): Dictionary to merge into the current configuration.
        """
        if not isinstance(cfg_dict, dict):
            raise ValueError("Provided configuration must be a dictionary.")
        self.update(cfg_dict)

    def get_config(self) -> Dict[str, Any]:
        """
        Retrieve the current configuration as a standard dictionary.

        Returns:
            dict: The current configuration.
        """
        return {key: (value.get_config() if isinstance(value, YamlParser) else value) for key, value in self.items()}

    @staticmethod
    def _ensure_file_exists(file_path: str):
        """
        Ensure the file exists at the given path.

        Args:
            file_path (str): Path to the file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Config file not found: {file_path}")

    @staticmethod
    def _load_yaml_file(file_path: str) -> Dict[str, Any]:
        """
        Load and parse a YAML file into a dictionary.

        Args:
            file_path (str): Path to the YAML file.

        Returns:
            dict: Parsed YAML content.
        """
        with open(file_path, 'r') as file:
            content = yaml.safe_load(file)
            if not isinstance(content, dict):
                raise ValueError(f"YAML file must contain a dictionary at the top level: {file_path}")
            # Recursively convert nested dictionaries to YamlParser instances
            return {key: YamlParser(value) if isinstance(value, dict) else value for key, value in content.items()}

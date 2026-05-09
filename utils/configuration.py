from configparser import ConfigParser, NoSectionError, NoOptionError
import logging
from utils.logging_manager import *
from utils.exceptions import ConfigException
logger = logging.getLogger(__name__)

CONFIG_FILE = "config.ini"

def load_configuration() -> ConfigParser:
    config = ConfigParser()
    try:
        config.read(CONFIG_FILE)
    except Exception as e:
        logger.error(f"Error reading configuration file {CONFIG_FILE}: {e}")
        raise ConfigException(f"Error reading configuration file {CONFIG_FILE}.")
    return config

def get_config_section(section: str) -> dict:
    config = load_configuration()
    try:
        return dict(config.items(section))
    except NoSectionError as nse:
        logger.error(f"Configuration section '{section}' not found: {nse}")
        raise ConfigException(f"Configuration section '{section}' not found.")

def get_config_option(section: str, option: str, fallback=None): # pragma: no cover
    config = load_configuration()
    try:
        return config.get(section, option)
    except NoSectionError as nse:
        logger.warning(f"Configuration section '{section}' not found: {nse}")
        return fallback
    except NoOptionError as noe:
        logger.warning(f"Configuration option '{option}' in section '{section}' not found: {noe}")
        return fallback

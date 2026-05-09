import pytest
from utils.configuration import load_configuration, get_config_section
from utils.exceptions import ConfigException


def test_load_configuration_success():
    config = load_configuration()
    assert "service" in config.sections()

def test_load_configuration_file_not_found(monkeypatch):
    monkeypatch.setattr("utils.configuration.CONFIG_FILE", "non_existent.ini")
    config = load_configuration()
    assert config.sections() == []

def test_load_configuration_permission_error(monkeypatch):
    def mock_read(file):
        raise PermissionError("Permission denied")
    monkeypatch.setattr("configparser.ConfigParser.read", mock_read)
    with pytest.raises(ConfigException):
        load_configuration()

def test_get_config_section_success():
    config_section = get_config_section("service")
    assert isinstance(config_section, dict)
    assert 'random_artists_number' in config_section
    assert 'tracks_by_artist_number' in config_section

def test_get_config_section_not_found():
    with pytest.raises(ConfigException):
        get_config_section("non_existent_section")


import pytest
from unittest.mock import patch, MagicMock
from service import DeezerService
from utils.models import GoujonPlaylistModel
from utils.exceptions import DeezerServiceError
from pydantic import BaseModel, ValidationError
import pandas as pd

@pytest.fixture
def service():
    with patch('service.api.DeezerAPI') as MockDeezerAPI:
        serv = DeezerService()
        serv.api = MagicMock()
        yield serv

def make_validation_error() -> ValidationError:
    class DummyModel(BaseModel):
        field: int

    try:
        DummyModel(field="not_an_int")
    except ValidationError as e:
        return e
    
def test_set_artist_selection_favorites(service):
    service.api.get_profile_data.return_value = {
        "TAB": {
            "artists": {
                "data": [
                    {"ART_ID": 1, "ART_NAME": "Artist 1", "ART_PICTURE": "picture1.jpg"},
                    {"ART_ID": 2, "ART_NAME": "Artist 2", "ART_PICTURE": "picture2.jpg"}
                ]
            }
        }
    }

    result = service.set_artist_selection('Favorites')
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 3)  # 2 artists, 3 columns
    assert 'ART_ID' in result.columns
    assert 'ART_NAME' in result.columns
    assert 'ART_PICTURE' in result.columns

def test_set_artist_selection_flow(service):
    service.api.get_user_flow.return_value = {
        "data": [
            {"SNG_ID": 1, "SNG_TITLE": "Song 1", "ART_ID": 1, "ART_NAME": "Artist 1", "ALB_PICTURE": "picture1.jpg", "DURATION": 200},
            {"SNG_ID": 2, "SNG_TITLE": "Song 2", "ART_ID": 2, "ART_NAME": "Artist 2", "ALB_PICTURE": "picture2.jpg", "DURATION": 180},
            {"SNG_ID": 3, "SNG_TITLE": "Song 3", "ART_ID": 2, "ART_NAME": "Artist 2", "ALB_PICTURE": "picture2.jpg", "DURATION": 220}
        ]
    }

    result = service.set_artist_selection('Flow')
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 3)  # 2 artists, 3 columns
    assert 'ART_ID' in result.columns
    assert 'ART_NAME' in result.columns
    assert 'ART_PICTURE' in result.columns

def test_set_artist_selection_validation_error(service):
    service.api.get_profile_data.side_effect = make_validation_error()
    with pytest.raises(DeezerServiceError):
        service.set_artist_selection('Favorites')

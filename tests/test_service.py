import pytest
from unittest.mock import patch, MagicMock
from service import DeezerService
from utils.models import GoujonPlaylistModel
from utils.exceptions import DeezerServiceError
import pandas as pd


@pytest.fixture
def service():
    with patch('service.api.DeezerAPI'):
        serv = DeezerService()
        serv.api = MagicMock()
        yield serv


@pytest.fixture
def playlist_to_create():
    return GoujonPlaylistModel(
        name="Test Playlist",
        public=False,
        selected_artists=pd.DataFrame([]),
        track_list=pd.DataFrame([])
    )


@pytest.fixture
def favorites_options():
    return {
        'mode': 'Favorites',
        'include_relative': False,
        'number_random_artists': 2,
        'number_tracks_by_artist': 2
    }


def make_mock_artist_data_songs(artist_id, tab=0):
    return {
        "ALBUMS": {"data": [{
            "SONGS": {"data": [
                {"SNG_ID": f"{artist_id}_01", "SNG_TITLE": f"Song 1 of {artist_id}",
                 "ART_ID": artist_id, "ART_NAME": f"Artist {artist_id}",
                 "ART_PICTURE": f"pic{artist_id}.jpg", "DURATION": "200"},
                {"SNG_ID": f"{artist_id}_02", "SNG_TITLE": f"Song 2 of {artist_id}",
                 "ART_ID": artist_id, "ART_NAME": f"Artist {artist_id}",
                 "ART_PICTURE": f"pic{artist_id}.jpg", "DURATION": "180"},
                {"SNG_ID": f"{artist_id}_03", "SNG_TITLE": f"Song 3 of {artist_id}",
                 "ART_ID": artist_id, "ART_NAME": f"Artist {artist_id}",
                 "ART_PICTURE": f"pic{artist_id}.jpg", "DURATION": "220"},
                {"SNG_ID": f"{artist_id}_04", "SNG_TITLE": f"Song 4 of {artist_id}",
                 "ART_ID": artist_id, "ART_NAME": f"Artist {artist_id}",
                 "ART_PICTURE": f"pic{artist_id}.jpg", "DURATION": "90"},
                {"SNG_ID": f"{artist_id}_05", "SNG_TITLE": f"Song 5 of {artist_id}",
                 "ART_ID": artist_id, "ART_NAME": f"Artist {artist_id}",
                 "ART_PICTURE": f"pic{artist_id}.jpg", "DURATION": "60"},
                {"SNG_ID": f"{artist_id}_06", "SNG_TITLE": f"Song 6 of {artist_id}",
                 "ART_ID": f"{artist_id}_bis", "ART_NAME": f"Artist {artist_id}",
                 "ART_PICTURE": f"pic{artist_id}.jpg", "DURATION": "90"},
            ]}
        }]}
    }

def mock_get_artist_data_related(artist_id, tab=1):
    data = [
        {"ART_ID": 4, "ART_NAME": "Artist 4", "ART_PICTURE": "picture4.jpg"},
        {"ART_ID": 5, "ART_NAME": "Artist 5", "ART_PICTURE": "picture5.jpg"},
        {"ART_ID": 6, "ART_NAME": "Artist 6", "ART_PICTURE": "picture6.jpg"},
    ]
    data = data[:4 - artist_id]  # Artist 1 has 3 related, Artist 2 has 2, Artist 3 has 1
    return {"RELATED_ARTISTS": {"data": data}}


def test_create_playlist_favorites_without_relatives(service, playlist_to_create, favorites_options):
    service.api.get_profile_data.return_value = {
        "TAB": {
            "artists": {
                "data": [
                    {"ART_ID": i, "ART_NAME": f"Artist {i}", "ART_PICTURE": f"picture{i}.jpg"}
                    for i in range(1, 6)
                ]
            }
        }
    }
    service.api.get_artist_data.side_effect = make_mock_artist_data_songs

    result = service.create_playlist(playlist_to_create, favorites_options)
    assert isinstance(result, GoujonPlaylistModel)
    assert result.selected_artists.shape[0] == 2
    assert result.track_list.shape[0] == 6  # 3 artists (2 random artists + mety-k) x 2 tracks each
    track_ids = result.track_list['SNG_ID'].apply(lambda x: x[-2:])
    assert all((track_ids != '05') & (track_ids != '06'))  # Tracks filtrées : durée < 80s ou ART_ID différent


def test_create_playlist_favorites_validation_error(service, playlist_to_create, favorites_options, validation_error):
    service.api.get_profile_data.side_effect = validation_error
    with pytest.raises(DeezerServiceError):
        service.create_playlist(playlist_to_create, favorites_options)


def test_create_playlist_with_no_tracks_found(service, playlist_to_create, validation_error):
    options = {
        'mode': 'Manual',
        'include_relative': False,
        'number_tracks_by_artist': 2
    }
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
    service.api.get_artist_data.side_effect = validation_error
    with pytest.raises(DeezerServiceError):
        service.create_playlist(playlist_to_create, options)


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
    assert result.shape == (2, 3)
    assert list(result.columns) == ['ART_ID', 'ART_NAME', 'ART_PICTURE']


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
    assert result.shape == (2, 3)
    assert list(result.columns) == ['ART_ID', 'ART_NAME', 'ART_PICTURE']


def test_set_artist_selection_validation_error(service, validation_error):
    service.api.get_profile_data.side_effect = validation_error
    with pytest.raises(DeezerServiceError):
        service.set_artist_selection('Favorites')


def test_get_related_artists_validation_error(service, validation_error):
    service.api.get_artist_data.side_effect = validation_error
    result = service._DeezerService__get_related_artists(artist_id=1)
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_add_related_artists_no_related_found(service, validation_error):
    selected_artists = pd.DataFrame({
        'ART_ID': [1],
        'ART_NAME': ['Artist 1'],
        'ART_PICTURE': ['picture1.jpg']
    })
    service.api.get_artist_data.side_effect = validation_error
    result = service._DeezerService__add_related_artists(selected_artists)
    assert isinstance(result, pd.DataFrame)
    assert result.equals(selected_artists)


def test_add_related_artists_with_related_found(service):
    selected_artists = pd.DataFrame({
        'ART_ID': [1, 2, 3],
        'ART_NAME': ['Artist 1', 'Artist 2', 'Artist 3'],
        'ART_PICTURE': ['picture1.jpg', 'picture2.jpg', 'picture3.jpg']
    })

    service.api.get_artist_data.side_effect = mock_get_artist_data_related

    result = service._DeezerService__add_related_artists(selected_artists)
    assert isinstance(result, pd.DataFrame)
    assert result.shape[0] == 5
    assert set(result['ART_ID']) == {1, 2, 3, 4, 5}

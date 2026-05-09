from service import DeezerService
from service.api import DeezerAPI
from flask import g
from datetime import datetime
from utils.models import GoujonPlaylistModel
import pandas as pd


def test_save_playlist_and_check_in_profile(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        playlist_name = f'test_integration_service_{ts}'
        playlist_to_create = GoujonPlaylistModel(
            name=playlist_name,
            public=False,
            selected_artists=pd.DataFrame({
                'ART_ID': [352227652],
                'ART_NAME': ['Mety-K'],
                'ART_PICTURE': ['9a1844bfe55e74f45d74463f80b2de60']
            }),
            track_list=pd.DataFrame({
                'SNG_ID': [3615373702],
                'SNG_TITLE': ['Stug'],
                'ART_ID': [352227652],
                'ART_NAME': ['Mety-K'],
                'ART_PICTURE': ['9a1844bfe55e74f45d74463f80b2de60']
            }),
         )
        service = DeezerService()
        api = DeezerAPI()
        service.save_playlist_on_deezer_profile(playlist_to_create)
        playlist_id = service._DeezerService__get_last_playlist_id()
        assert playlist_id is not None, "Failed to retrieve the last playlist ID"
        songs_in_playlist = api.get_playlist_songs(playlist_id)
        assert songs_in_playlist is not None, "Failed to retrieve songs from the created playlist"
        song_ids_in_playlist = [song['SNG_ID'] for song in songs_in_playlist['data']]
        assert '3615373702' in song_ids_in_playlist, "The expected song is not in the created playlist"
        api.delete_playlist(playlist_id)


import pytest
from flask import g
from service.api import DeezerAPI
from utils.exceptions import LoginException, DeezerAPIError
from datetime import datetime
from conftest import INVALID_AUTH


def test_get_user_data_has_expected_structure(flask_app, base_auth):
    """Détecte tout changement de structure côté API Deezer."""
    with flask_app.app_context():
        g.auth = base_auth
        result = DeezerAPI().get_user_data()

    assert isinstance(result, dict), "La réponse doit être un dict"
    assert "user_id" in result, "Clé 'user_id' manquante — l'API a peut-être changé"
    assert "api_token" in result, "Clé 'api_token' manquante — l'API a peut-être changé"
    assert isinstance(result["user_id"], int), "'user_id' doit être un int"
    assert isinstance(result["api_token"], str), "'api_token' doit être une str"
    assert result["user_id"] != 0, "user_id=0 signifie que les cookies sont invalides/expirés"


def test_get_user_data_with_invalid_cookies(flask_app):
    with flask_app.app_context():
        g.auth = INVALID_AUTH
        with pytest.raises(LoginException, match="User is not logged in"):
            DeezerAPI().get_user_data()


def test_get_user_data_with_valid_cookies(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        result = DeezerAPI().get_user_data()

    assert result["user_id"] == full_auth["user_id"]
    assert result["api_token"] == full_auth["api_token"]


@pytest.mark.parametrize("tab,key", [("artists", "artists"), ("playlists", "playlists")])
def test_get_profile_data_with_valid_cookies(flask_app, full_auth, tab, key):
    with flask_app.app_context():
        g.auth = full_auth
        result = DeezerAPI().get_profile_data(tab=tab)

    assert "TAB" in result, "Clé 'TAB' manquante dans la réponse"
    assert key in result["TAB"], f"Clé '{key}' manquante dans 'TAB'"
    assert isinstance(result["TAB"][key], dict), f"'{key}' doit être un dict"


def test_get_profile_data_with_invalid_cookies(flask_app):
    with flask_app.app_context():
        g.auth = INVALID_AUTH
        with pytest.raises(DeezerAPIError, match="Request Error: {'VALID_TOKEN_REQUIRED': 'Invalid CSRF token'}"):
            DeezerAPI().get_profile_data(tab='artists')


def test_get_artist_data_with_valid_artist_id(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        result = DeezerAPI().get_artist_data(artist_id='58801', tab=0)  # ID de Chinese Man

    assert "ALBUMS" in result, "Clé 'ALBUMS' manquante dans la réponse"
    assert isinstance(result["ALBUMS"], dict), "'ALBUMS' doit être un dict"
    assert "data" in result["ALBUMS"], "Clé 'data' manquante dans 'ALBUMS'"
    assert isinstance(result["ALBUMS"]["data"], list), "'data' dans 'ALBUMS' doit être une liste"
    assert len(result["ALBUMS"]["data"]) > 0, "La liste des albums ne doit pas être vide pour un artist_id valide"


def test_get_artist_data_with_invalid_artist_id(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        with pytest.raises(DeezerAPIError, match="Request Error: {'REQUEST_ERROR': 'Wrong parameters'}"):
            DeezerAPI().get_artist_data(artist_id='invalid', tab=0)


def test_get_user_flow_with_valid_cookies(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        result = DeezerAPI().get_user_flow()

    assert "data" in result, "Clé 'data' manquante dans la réponse"
    assert isinstance(result["data"], list), "'data' doit être une liste"
    assert len(result["data"]) > 0, "La liste de flow ne doit pas être vide pour des cookies valides"


def test_get_user_flow_with_invalid_cookies(flask_app):
    with flask_app.app_context():
        g.auth = INVALID_AUTH
        with pytest.raises(DeezerAPIError, match="Request Error: {'VALID_TOKEN_REQUIRED': 'Invalid CSRF token'}"):
            DeezerAPI().get_user_flow()


# get_songs pas utilisé dans le service pour l'instant, pas de test d'intégration prévu

def test_create_playlist_check_in_profile(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        playlist_name = f'test_integration_api_{ts}'
        api.create_playlist(playlist_name, "desc", False)
        playlists = api.get_profile_data(tab='playlists')
        titles = [p["TITLE"] for p in playlists["TAB"]["playlists"]["data"]]
        assert playlist_name in titles, "La playlist créée n'apparaît pas dans le profil de l'utilisateur"
        playlist_id = playlists["TAB"]["playlists"]["data"][0]["PLAYLIST_ID"]
        api.delete_playlist(playlist_id)  # Nettoyage : supprimer la playlist après le test 


def test_playlist_song_management(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        playlist_name = f'test_integration_api2_{ts}'
        api.create_playlist(playlist_name, "desc", False)
        playlists = api.get_profile_data(tab='playlists')
        playlist_id = playlists["TAB"]["playlists"]["data"][0]["PLAYLIST_ID"]
        api.add_songs_to_playlist(playlist_id, [[3135556, 0], [134831006, 0], [54519711, 0]])  # Ajouter "Harder, Better, Faster, Stronger" de Daft Punk
        songs = api.get_playlist_songs(playlist_id)
        song_ids = [s["SNG_ID"] for s in songs['data']]
        assert '134831006' in song_ids, "Une chanson ajoutée n'apparaît pas dans la playlist"
        api.update_song_order_in_playlist(playlist_id, [54519711, 3135556, 134831006])  # Réordonner les chansons
        updated_songs = api.get_playlist_songs(playlist_id)
        updated_song_ids = [s["SNG_ID"] for s in updated_songs['data']]
        assert updated_song_ids == ['54519711', '3135556', '134831006'], "L'ordre des chansons dans la playlist n'a pas été mis à jour correctement"
        api.delete_songs_from_playlist(playlist_id, [[3135556, 0]])  # Supprimer une chanson
        final_songs = api.get_playlist_songs(playlist_id)
        final_song_ids = [s["SNG_ID"] for s in final_songs['data']]
        assert final_song_ids == ['54519711', '134831006'], "Les chansons supprimées apparaissent toujours dans la playlist"
        api.delete_playlist(playlist_id)  # Nettoyage : supprimer la playlist après le test


def test_get_playlist_infos_with_valid_cookies(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        result = DeezerAPI().get_playlist_infos(playlist_id='15094101943')  # ID baseplaylistfortest

    assert "DATA" in result, "Clé 'DATA' manquante dans la réponse"
    assert isinstance(result["DATA"], dict), "'DATA' doit être un dict"
    assert "TITLE" in result["DATA"], "Clé 'TITLE' manquante dans 'DATA'"
    assert "SONGS" in result, "Clé 'SONGS' manquante dans la réponse"
    assert isinstance(result["SONGS"], dict), "'SONGS' doit être un dict"
    assert "data" in result["SONGS"], "Clé 'data' manquante dans 'SONGS'"
    assert isinstance(result["SONGS"]["data"], list), "'data' dans 'TAB' doit être une liste"
    assert len(result["SONGS"]["data"]) > 0, "La liste des playlists ne doit pas être vide pour un playlist_id valide"



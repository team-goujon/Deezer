import os
from pydantic import ValidationError
import pytest
from flask import Flask, g
from service.api import DeezerAPI
from utils.exceptions import LoginException
from datetime import datetime


@pytest.fixture
def flask_app():
    return Flask(__name__)


@pytest.fixture
def base_auth():
    """Charge les cookies depuis les variables d'environnement."""
    arl = os.environ.get("DEEZER_ARL")
    sid = os.environ.get("DEEZER_SID")
    if not arl or not sid:
        pytest.skip("DEEZER_ARL et DEEZER_SID requis pour ce test d'intégration")
    return {"arl": arl, "sid": sid, "api_token": ""}


@pytest.fixture
def full_auth():
    """Charge les cookies depuis les variables d'environnement."""
    arl = os.environ.get("DEEZER_ARL")
    sid = os.environ.get("DEEZER_SID")
    api_token = os.environ.get("DEEZER_API_TOKEN")
    user_id = os.environ.get("DEEZER_USER_ID")
    if not arl or not sid or not api_token or not user_id:
        pytest.skip("Toutes les variables d'environnement requises pour ce test d'intégration")
    return {"arl": arl, "sid": sid, "api_token": api_token, "user_id": int(user_id)}


def test_get_user_data_has_expected_structure(flask_app, base_auth):
    """Détecte tout changement de structure côté API Deezer."""
    with flask_app.app_context():
        g.auth = base_auth
        api = DeezerAPI()
        result = api.get_user_data()

    print("Résultat de get_user_data:", result)  # Affiche le résultat pour le débogage
    assert isinstance(result, dict), "La réponse doit être un dict"
    assert "user_id" in result, "Clé 'user_id' manquante — l'API a peut-être changé"
    assert "api_token" in result, "Clé 'api_token' manquante — l'API a peut-être changé"
    assert isinstance(result["user_id"], int), "'user_id' doit être un int"
    assert isinstance(result["api_token"], str), "'api_token' doit être une str"
    assert result["user_id"] != 0, "user_id=0 signifie que les cookies sont invalides/expirés"

def test_get_user_data_with_invalid_cookies(flask_app):
    """Vérifie que l'API gère correctement les cookies invalides."""
    with flask_app.app_context():
        g.auth = {"arl": "invalid", "sid": "invalid", "api_token": ""}
        api = DeezerAPI()
        with pytest.raises(LoginException, match="User is not logged in"):
            api.get_user_data()

def test_get_user_data_with_valid_cookies(flask_app, full_auth):
    """Vérifie que get_user_data fonctionne avec des cookies valides."""
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        result = api.get_user_data()

    assert result["user_id"] == full_auth["user_id"], "Le user_id retourné ne correspond pas à celui attendu"
    assert result["api_token"] == full_auth["api_token"], "Le api_token retourné ne correspond pas à celui attendu"


def test_get_profile_data_artists_with_valid_cookies(flask_app, full_auth):
    """Vérifie que get_profile_data avec tab='artists' fonctionne avec des cookies valides."""
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        result = api.get_profile_data(tab='artists')

    assert "TAB" in result, "Clé 'TAB' manquante dans la réponse"
    assert "artists" in result["TAB"], "Clé 'artists' manquante dans 'TAB'"
    assert isinstance(result["TAB"]["artists"], dict), "'artists' doit être un dict"

def test_get_profile_data_home_with_valid_cookies(flask_app, full_auth):
    """Vérifie que get_profile_data avec tab='home' fonctionne avec des cookies valides."""
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        result = api.get_profile_data(tab='home')

    assert "TAB" in result, "Clé 'TAB' manquante dans la réponse"
    assert "home" in result["TAB"], "Clé 'home' manquante dans 'TAB'"
    assert isinstance(result["TAB"]["home"], dict), "'home' doit être un dict"

def test_get_profile_data_with_invalid_cookies(flask_app):
    """Vérifie que get_profile_data gère correctement les cookies invalides."""
    with flask_app.app_context():
        g.auth = {"arl": "invalid", "sid": "invalid", "api_token": ""}
        api = DeezerAPI()
        with pytest.raises(ValidationError):
            api.get_profile_data(tab='artists')


def test_get_artist_data_with_valid_artist_id(flask_app, full_auth):
    """Vérifie que get_artist_data fonctionne avec un artist_id valide."""
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        result = api.get_artist_data(artist_id='58801', tab=0) # ID de Chinese Man

    assert "ALBUMS" in result, "Clé 'ALBUMS' manquante dans la réponse"
    assert isinstance(result["ALBUMS"], dict), "'ALBUMS' doit être un dict"
    assert "data" in result["ALBUMS"], "Clé 'data' manquante dans 'ALBUMS'"
    assert isinstance(result["ALBUMS"]["data"], list), "'data' dans 'ALBUMS' doit être une liste"
    assert len(result["ALBUMS"]["data"]) > 0, "La liste des albums ne doit pas être vide pour un artist_id valide"

def test_get_artist_data_with_invalid_artist_id(flask_app, full_auth):
    """Vérifie que get_artist_data gère correctement un artist_id invalide."""
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        with pytest.raises(ValidationError):
            api.get_artist_data(artist_id='invalid', tab=0)


def test_get_user_flow_with_valid_cookies(flask_app, full_auth):
    """Vérifie que get_user_flow fonctionne avec des cookies valides."""
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        result = api.get_user_flow()

    assert "data" in result, "Clé 'data' manquante dans la réponse"
    assert isinstance(result["data"], list), "'data' doit être une liste"
    assert len(result["data"]) > 0, "La liste de flow ne doit pas être vide pour des cookies valides"

def test_get_user_flow_with_invalid_cookies(flask_app):
    """Vérifie que get_user_flow gère correctement les cookies invalides."""
    with flask_app.app_context():
        g.auth = {"arl": "invalid", "sid": "invalid", "api_token": ""}
        api = DeezerAPI()
        with pytest.raises(ValidationError):
            api.get_user_flow()

# get_songs pas utilisé dans le service pour l'instant, pas de test d'intégration prévu

def test_create_playlist_check_in_profile(flask_app, full_auth):
    with flask_app.app_context():
        g.auth = full_auth
        api = DeezerAPI()
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        playlist_name = f'test_integration_api_{ts}'
        api.create_playlist(playlist_name, "desc", False)
        profile = api.get_profile_data(tab='home')
        titles = [p["TITLE"] for p in profile["TAB"]["home"]["playlists"]["data"]]
        assert playlist_name in titles, "La playlist créée n'apparaît pas dans le profil de l'utilisateur"


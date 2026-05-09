import os
import pytest
from flask import Flask, g
from flask_session import Session
from cachelib import SimpleCache
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from service.api import DeezerAPI

load_dotenv()

INVALID_AUTH = {"arl": "invalid", "sid": "invalid", "api_token": ""}


@pytest.fixture
def flask_app():
    app = Flask(__name__)
    app.config['SESSION_TYPE'] = 'cachelib'
    app.config['SESSION_SERIALIZATION_FORMAT'] = 'json'
    app.config['SESSION_CACHELIB'] = SimpleCache()
    Session(app)
    return app


@pytest.fixture
def mock_auth():
    return {"arl": "fake_arl", "sid": "fake_sid", "api_token": "fake_token"}


@pytest.fixture
def validation_error():
    class DummyModel(BaseModel):
        field: int

    try:
        DummyModel(field="not_an_int")
    except ValidationError as e:
        return e


@pytest.fixture
def deezer_cookies():
    """Charge les cookies depuis les variables d'environnement."""
    arl = os.environ.get("DEEZER_ARL")
    sid = os.environ.get("DEEZER_SID")
    if not arl or not sid:
        pytest.skip("DEEZER_ARL et DEEZER_SID requis pour ce test")
    return {"arl": arl, "sid": sid}


@pytest.fixture
def base_auth(deezer_cookies):
    """Retourne les cookies Deezer au format attendu par l'API."""
    arl = deezer_cookies["arl"]
    sid = deezer_cookies["sid"]
    return {"arl": arl, "sid": sid, "api_token": ""}


@pytest.fixture
def full_auth(flask_app, base_auth):
    """Récupère un auth complet (avec api_token et user_id) via l'API."""
    with flask_app.app_context():
        g.auth = base_auth
        result = DeezerAPI().get_user_data()

    api_token = result["api_token"]
    user_id = result["user_id"]
    if not api_token or not user_id:
        pytest.skip("Toutes les variables d'environnement requises pour ce test d'intégration")
    return {**base_auth, "api_token": api_token, "user_id": int(user_id)}

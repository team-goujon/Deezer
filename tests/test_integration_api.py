import os
import pytest
from flask import Flask, g
from service.api import DeezerAPI
from utils.exceptions import LoginException


@pytest.fixture
def flask_app():
    return Flask(__name__)


@pytest.fixture
def real_auth():
    """Charge les cookies depuis les variables d'environnement."""
    arl = os.environ.get("DEEZER_ARL")
    sid = os.environ.get("DEEZER_SID")
    if not arl or not sid:
        pytest.skip("DEEZER_ARL et DEEZER_SID requis pour ce test d'intégration")
    return {"arl": arl, "sid": sid, "api_token": ""}


def test_get_user_data_has_expected_structure(flask_app, real_auth):
    """Détecte tout changement de structure côté API Deezer."""
    with flask_app.app_context():
        g.auth = real_auth
        api = DeezerAPI()
        result = api.get_user_data()

    assert isinstance(result, dict), "La réponse doit être un dict"
    assert "user_id" in result, "Clé 'user_id' manquante — l'API a peut-être changé"
    assert "api_token" in result, "Clé 'api_token' manquante — l'API a peut-être changé"
    assert isinstance(result["user_id"], int), "'user_id' doit être un int"
    assert isinstance(result["api_token"], str), "'api_token' doit être une str"
    assert result["user_id"] != 0, "user_id=0 signifie que les cookies sont invalides/expirés"
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, g
from service.api import DeezerAPI
from utils.exceptions import LoginException


@pytest.fixture
def flask_app():
    return Flask(__name__)

@pytest.fixture
def mock_auth():
    return {"arl": "fake_arl", "sid": "fake_sid", "api_token": "fake_token"}

def test_get_user_data_on_success(flask_app, mock_auth):
    mock_api_response = {
        "error": {},
        "results": {
            "checkForm": "abc123",
            "USER": {"USER_ID": 42}
        }
    }
    with flask_app.app_context():
        g.auth = mock_auth
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = "non-vide"
            mock_post.return_value.json.return_value = mock_api_response

            result = DeezerAPI().get_user_data()

    assert result == {"user_id": 42, "api_token": "abc123"}


def test_get_user_data_login_exception(flask_app, mock_auth):
    mock_api_response = {
        "error": {},
        "results": {
            "checkForm": "abc123",
            "USER": {"USER_ID": 0} 
        }
    }
    with flask_app.app_context():
        g.auth = mock_auth
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = "non-vide"
            mock_post.return_value.json.return_value = mock_api_response

            with pytest.raises(LoginException):
                DeezerAPI().get_user_data()
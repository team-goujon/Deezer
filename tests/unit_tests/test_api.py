import pytest
from unittest.mock import patch
from flask import g
from service.api import DeezerAPI
from utils.exceptions import LoginException, DeezerAPIError


@pytest.fixture
def api(flask_app, mock_auth):
    """DeezerAPI prête à l'emploi dans un contexte Flask."""
    with flask_app.app_context():
        g.auth = mock_auth
        yield DeezerAPI()


def test_get_user_data_on_success(api):
    mock_api_response = {
        "error": {},
        "results": {
            "checkForm": "abc123",
            "USER": {"USER_ID": 42}
        }
    }
    with patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "non-vide"
        mock_post.return_value.json.return_value = mock_api_response
        result = api.get_user_data()

    assert result == {"user_id": 42, "api_token": "abc123"}


def test_get_user_data_login_exception(api):
    mock_api_response = {
        "error": {},
        "results": {
            "checkForm": "abc123",
            "USER": {"USER_ID": 0}
        }
    }
    with patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "non-vide"
        mock_post.return_value.json.return_value = mock_api_response
        with pytest.raises(LoginException):
            api.get_user_data()


def test_get_api_success(api):
    with patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'error': [],
            'results': {"data": "test"}
        }
        result = api._DeezerAPI__get_api("test.method", body={"key": "value"})

    assert result == {"data": "test"}


def test_get_api_error(api):
    with patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'error': ["Some error occurred"],
            'results': {}
        }
        with pytest.raises(DeezerAPIError):
            api._DeezerAPI__get_api("test.method", body={"key": "value"})


def test_get_api_empty_response(api):
    with patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = ""
        result = api._DeezerAPI__get_api("test.method", body={"key": "value"})

    assert result is None


def test_get_api_http_exception(api):
    with patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.raise_for_status.side_effect = Exception("HTTP Error")
        result = api._DeezerAPI__get_api("test.method", body={"key": "value"})

    assert result is None

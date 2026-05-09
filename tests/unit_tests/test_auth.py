import pytest
from flask import g
from service.auth import is_auth, authenticate, require_auth

@pytest.fixture
def session():
    """Fixture pour simuler une session Flask."""
    return {}

def test_is_auth_with_no_auth(session):
    session.clear()
    assert not is_auth(session)

def test_is_auth_with_auth(session):
    session['auth'] = {'arl': 'test_arl', 'sid': 'test_sid'}
    assert is_auth(session)


def test_authenticate_with_valid_cookies(monkeypatch, flask_app):
    def mock_get_user_data(self):
        return {"user_id": 42, "api_token": "abc123"}
    monkeypatch.setattr("service.api.DeezerAPI.get_user_data", mock_get_user_data)
    with flask_app.app_context():
        auth_data = authenticate("valid_arl", "valid_sid")
    assert auth_data["arl"] == "valid_arl"
    assert auth_data["sid"] == "valid_sid"
    assert auth_data["user_id"] == 42
    assert auth_data["api_token"] == "abc123"   


def test_authenticate_with_invalid_cookies(monkeypatch):
    def mock_get_user_data():
        raise Exception("Invalid cookies")
    monkeypatch.setattr("service.api.DeezerAPI.get_user_data", mock_get_user_data)
    auth_data = authenticate("invalid_arl", "invalid_sid")
    assert auth_data == {}  

def test_authenticate_with_missing_cookies():
    auth_data = authenticate("", "")
    assert auth_data == {}


def test_require_auth_decorator(flask_app):
    @flask_app.route('/login')
    def login():
        return "Login"
    
    @require_auth
    def protected_route():
        return "Protected content"

    with flask_app.test_request_context():
        # Test without auth
        result = protected_route()
        assert result.status_code == 302

        # Test with auth
        from flask import session
        session['auth'] = {"arl": "test_arl", "sid": "test_sid"}
        result = protected_route()
        assert result == "Protected content"
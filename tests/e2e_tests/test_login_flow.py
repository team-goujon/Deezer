import os
import time

import pytest
import requests


BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:5000")


@pytest.fixture(scope="session")
def live_app():
    """Wait for the already-running application before validating it."""
    deadline = time.monotonic() + 30
    last_error = None
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE_URL}/login", timeout=1)
            if response.status_code == 200:
                break
        except requests.RequestException as error:
            last_error = error
            time.sleep(1)
    else:
        pytest.fail(
            f"Application is not available at {BASE_URL}. "
            f"Start it before running e2e tests. Last error: {last_error}"
        )

    yield BASE_URL


def test_unauthenticated_user_can_reach_login_page(live_app):
    session = requests.Session()

    response = session.get(f"{live_app}/", allow_redirects=False, timeout=5)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    response = session.get(f"{live_app}/login", timeout=5)

    assert response.status_code == 200
    assert "Enter Your Deezer Cookies" in response.text
    assert "Authenticate" in response.text


def test_login_form_rejects_missing_cookies(live_app):
    response = requests.post(
        f"{live_app}/login",
        data={"arl": "", "sid": ""},
        timeout=5,
    )

    assert response.status_code == 200
    assert "Both arl and sid cookies are required" in response.text


def test_user_can_login_with_deezer_cookies(live_app, deezer_cookies):
    session = requests.Session()

    response = session.post(
        f"{live_app}/login",
        data=deezer_cookies,
        allow_redirects=True,
        timeout=10,
    )

    assert response.status_code == 200
    assert response.url == f"{live_app}/"
    assert "Playlist name:" in response.text
    assert "Generate" in response.text

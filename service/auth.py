from selenium import webdriver
from flask import g, session, redirect, url_for
from functools import wraps
from service.api import DeezerAPI
import time
import logging
logger = logging.getLogger(__name__)

LOGIN_URL = "https://account.deezer.com/fr/login/"

def is_auth(session) -> bool:
    return session.get("auth") is not None

def _authenticate_on_website():
    cookie_box = {}
    logger.info("Opening a browser for interactive Deezer login")
    driver = webdriver.Chrome()
    try:
        driver.get(LOGIN_URL)
        deadline = time.time() + 120
        poll_interval = 2
        while time.time() < deadline and not ("arl" in cookie_box and "sid" in cookie_box):
            time.sleep(poll_interval)
            for cookie in driver.get_cookies():
                name = cookie.get("name")
                if name in ("arl", "sid") and name not in cookie_box:
                    cookie_box[name] = cookie.get("value")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return cookie_box

def _authenticate_on_api():
    user_data = {}
    try:
        user_data = DeezerAPI().get_user_data()
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
    return user_data

def authenticate():
    cookie_box = _authenticate_on_website()
    g.auth = cookie_box
    user_data = _authenticate_on_api()
    return {**cookie_box, **user_data}

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_auth(session):
            logger.info("User not logged in, redirecting to login page")
            return redirect(url_for('login'))
        g.auth = session.get("auth")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

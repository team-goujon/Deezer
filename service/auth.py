from flask import g, session, redirect, url_for
from functools import wraps
from service.api import DeezerAPI
import logging

logger = logging.getLogger(__name__)

REQUIRED_COOKIES = ["arl", "sid"]

def is_auth(session) -> bool:
    return session.get("auth") is not None

def _authenticate_on_api(arl: str, sid: str) -> dict:
    try:
        auth_data = {"arl": arl, "sid": sid}
        g.auth = auth_data
        
        user_data = DeezerAPI().get_user_data()
        
        logger.info(f"Cookies validated successfully. User ID: {user_data.get('USER', {}).get('USER_ID')}")
        return {**auth_data, **user_data}
    except Exception as e:
        logger.error(f"Cookie validation failed: {e}")
        return {}

def authenticate(arl: str, sid: str) -> dict:
    if not arl or not sid:
        logger.error("Missing required cookies (arl or sid)")
        return {}
    
    return _authenticate_on_api(arl, sid)


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

import requests
import logging
from utils.logging_manager import debugging
from utils.models import data_validation
from utils.exceptions import DeezerAPIError, LoginException
from flask import g
from functools import wraps
logger = logging.getLogger(__name__)

def with_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Injecting auth={g.auth} into function: {func.__name__}")
        return func(
            *args,
            auth=g.auth,
            **kwargs
        )
    wrapper.__name__ = func.__name__
    return wrapper

class DeezerAPI:
    API_URL = "https://www.deezer.com/ajax/gw-light.php"
    
    def __init__(self):
        pass
    
    def get_user_data(self) -> dict:
        results = self.__get_api("deezer.getUserData")
        api_token = results['checkForm']
        user_id = results["USER"]["USER_ID"]
        user_data = {
            "user_id": user_id,
            "api_token": api_token
        }
        if user_id == 0:
            raise LoginException("User is not logged in. Please check your cookies.")
        return user_data

    # @debugging
    @with_auth
    def __get_api(self, method: str, body: dict = None, auth: dict = None) -> dict:
        try :
            req = requests.Session()
            req.cookies.update({
                name: auth.get(name) for name in ("arl", "sid")
            })
            req.headers.update({
                'User-Agent': 'Mozilla/5.0 (compatible)',
                'Referer': 'https://www.deezer.com/',
                'Origin': 'https://www.deezer.com',
                'Content-Type': 'application/json'
            })
            logger.info(f"Calling API method: {method} with body: {body}")
            payload = {
                "api_version": "1.0",
                "api_token": auth.get("api_token", ""),
                "input": "3",
                "method": method,
            }
            logger.debug(f"Payload for API call: {payload}")
            resp = req.post(self.API_URL, params=payload, json=body)
            resp.raise_for_status()
            logger.debug(f"Response status code: {resp.status_code}")
            if resp.text != '':
                resp_json = resp.json()
                if resp_json['error']:
                    raise DeezerAPIError(f"Request Error: {resp_json['error']}")
                return resp_json['results']
            else:
                logger.debug(f"No data returned")
                return None
        except DeezerAPIError as e:
            logger.error(f"DeezerAPIError: {e.message}")
            raise
        except Exception as e:
            logger.debug(e)
            return None
    
    @with_auth
    @data_validation
    def get_profile_data(self, auth: dict, tab: str, nb: int = 100) -> dict:
        logger.debug(f"Getting profile data for tab: {tab} with nb: {nb}")
        body = {
            'user_id': auth.get("user_id"),
            'tab': tab,
            'nb': nb
        }
        results = self.__get_api("deezer.pageProfile", body)
        return results

    @data_validation
    def get_artist_data(self, artist_id: str, tab: int = 0) -> dict:
        body = {
            "art_id": artist_id,
            "lang": "fr",
            "tab": tab
        }
        results = self.__get_api("deezer.pageArtist", body)
        return results

    @with_auth
    @data_validation
    def get_user_flow(self, auth: dict):
        body = {
            "user_id": auth.get("user_id"),
        }
        results = self.__get_api("radio.getUserRadio", body)
        logger.debug(f"User flow data retrieved: {results}")
        return results
    
    def get_songs(self, album_id: int): # pragma: no cover
        body = {
            "alb_id": album_id,
            "nb": 100,
            "start": 0
        }
        results = self.__get_api("song.getListByAlbum", body)
        return results

    def create_playlist(self, name: str, description: str, public: bool):
        body = {
            "title": name,
            "description": description,
            "status": int(not public),
            "tags": "",
            "songs": [],
            "collaborative": False
        }
        results = self.__get_api("playlist.create", body)
        pass

    def add_songs_to_playlist(self, songs_list: list, playlist_id: int):
        body = {
            "playlist_id": str(playlist_id),
            "songs": songs_list,
            "offset": -1,
            "order": 0,
            "replace": False
        }
        results = self.__get_api("playlist.addSongs", body)
        pass

    @data_validation
    def get_playlist_songs(self, playlist_id: int):
        body = {
            "playlist_id": str(playlist_id),
            "nb": 100,
            "start": 0
        }
        results = self.__get_api("playlist.getSongs", body)
        return results
    
    def delete_playlist(self, playlist_id: int):
        body = {
            "playlist_id": str(playlist_id)
        }
        results = self.__get_api("playlist.delete", body)
        pass
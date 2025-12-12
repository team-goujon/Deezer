import requests
import logging
from utils.logging_manager import debugging
from utils.models import data_validation
from utils.exceptions import DeezerAPIError, LoginException
logger = logging.getLogger(__name__)

class DeezerAPI:
    API_URL = "https://www.deezer.com/ajax/gw-light.php"
    
    def __init__(self, request):
        self.session = requests.Session()
        self.api_token = ""
        self.set_session_params(request)
        self.get_user_data()
        pass

    def set_session_params(self, request):
        self.session.cookies.update({
            name: request.cookies.get(name) for name in ("arl", "sid")
        })
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible)',
            'Referer': 'https://www.deezer.com/',
            'Origin': 'https://www.deezer.com',
            'Content-Type': 'application/json'
        })
        pass
    
    def get_user_data(self):
        results = self.__get_api("deezer.getUserData")
        self.api_token = results['checkForm']
        user_info = results["USER"]
        self.user_id = user_info["USER_ID"]
        if self.user_id == 0:
            raise LoginException("User is not logged in. Please check your cookies.")
        pass

    def __get_api(self, method: str, body: dict = None) -> dict:
        try :
            logger.info(f"Calling API method: {method} with body: {body}")
            payload = {
                "api_version": "1.0",
                "api_token": self.api_token,
                "input": "3",
                "method": method,
            }
            resp = self.session.post(self.API_URL, params=payload, json=body)
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
        except Exception as e:
            logger.debug(e)
            return None

    @data_validation
    def get_profile_data(self, tab: str, nb: int = 100) -> dict:
        body = {
            'user_id': self.user_id,
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

    @data_validation
    def get_user_flow(self):
        body = {
            "user_id": self.user_id,
        }
        results = self.__get_api("radio.getUserRadio", body)
        return results
    
    def get_songs(self, album_id: int):
        body = {
            "alb_id": album_id,
            "nb": 100,
            "start": 0
        }
        results = self.__get_api("song.getListByAlbum", body)
        return results

    @debugging
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

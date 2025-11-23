import requests
import time
from configparser import NoSectionError, NoOptionError
from selenium import webdriver
from utils.configuration import get_config_section, load_configuration
import logging
from utils.logging_manager import debugging
from utils.schema import deezer_data_validation
from utils.exceptions import DeezerAPIError, LoginException
logger = logging.getLogger(__name__)

class DeezerAPI:
    API_URL = "https://www.deezer.com/ajax/gw-light.php"
    LOGIN_URL = "https://account.deezer.com/fr/login/"

    def __init__(self):
        self.config = get_config_section("cookies")
        self.session = requests.Session()
        self.api_token = ""
        self.set_session_params()
        self.get_user_data()
        pass

    def get_cookie_box(self):
        cookie_box = {}
        try:
            for name in ['sid', 'arl']:
                cookie_box[name] = self.config[name]
            if not(cookie_box['sid'] and cookie_box['arl']):
                cookie_box = self.save_cookies()
        except NoSectionError as nse:
            logger.debug(f'NoSectionError {nse}')
            cookie_box = self.save_cookies()
        except NoOptionError as noe:
            logger.debug(f'NoOptionError {noe}')
            cookie_box = self.save_cookies()
        except Exception as e:
            logger.error(f"Error reading {CONFIG_FILE}: {e}")
        
        return cookie_box

    def save_cookies(self):
        cookie_box = {}
        print("Opening a browser for interactive Deezer login (please sign in in that window)...")
        driver = webdriver.Chrome()
        try:
            driver.get(self.LOGIN_URL)
            deadline = time.time() + 120
            poll_interval = 2
            while time.time() < deadline and not ("arl" in cookie_box and "sid" in cookie_box):
                time.sleep(poll_interval)
                for cookie in driver.get_cookies():
                    name = cookie.get("name")
                    if name in ("arl", "sid") and name not in cookie_box:
                        cookie_box[name] = cookie.get("value")
            # Save cookie_box in the config file under [cookies]
            config = load_configuration()
            try:
                if not config.has_section("cookies"):
                    config.add_section("cookies")
                for name in ("sid", "arl"):
                    if name in cookie_box:
                        config.set("cookies", name, cookie_box[name])
                with open(self.CONFIG_FILE, "w") as f:
                    config.write(f)
            except Exception as e:
                logger.error(f"Couldn't save cookie file {CONFIG_FILE}: {e}")
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        return cookie_box

    def set_session_params(self):
        cookie_box = self.get_cookie_box()
        self.session.cookies.update({
            name: cookie_box[name] for name in ("arl", "sid")
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

    @deezer_data_validation
    def get_profile_data(self, tab: str, nb: int = 100) -> dict:
        body = {
            'user_id': self.user_id,
            'tab': tab,
            'nb': nb
        }
        results = self.__get_api("deezer.pageProfile", body)
        return results

    @deezer_data_validation
    def get_artist_data(self, artist_id: str, tab: int = 0) -> dict:
        body = {
            "art_id": artist_id,
            "lang": "fr",
            "tab": tab
        }
        results = self.__get_api("deezer.pageArtist", body)
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

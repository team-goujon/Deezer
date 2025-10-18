import requests
import time
from configparser import ConfigParser
from selenium import webdriver

class DeezerAPI:
    API_URL = "https://www.deezer.com/ajax/gw-light.php"

    def __init__(self):
        self.session = requests.Session()
        self.api_token = ""
        self.set_session_params()
        self.get_user_data()
        pass

    def get_cookie_box(self):
        config_file = "cookies.ini"
        config = ConfigParser()
        cookie_box = {}
        try:
            config.read(config_file)
            if not config.has_section("cookies"):
                print("No [cookies] section in config file.")
                cookie_box = self.get_cookies()
            elif set(['sid', 'arl']).issubset(set(config.options("cookies"))):
                for name in ['sid', 'arl']:
                    cookie_box[name] = config.get("cookies", name)
                if not(cookie_box['sid'] and cookie_box['arl']):
                    print("At least one cookie value is missing.")
                    cookie_box = self.get_cookies()
            else:
                print("Some cookies are missing in config file.")
                cookie_box = self.get_cookies()
            return cookie_box
        except Exception as e:
            print(f"Error reading {config_file}: {e}")

    def get_cookies(self):
        config_file = "cookies.ini"
        config = ConfigParser()
        cookie_box = {}
        print("Opening a browser for interactive Deezer login (please sign in in that window)...")
        driver = webdriver.Chrome()
        try:
            driver.get("https://www.deezer.com/fr")
            deadline = time.time() + 120
            poll_interval = 2
            while time.time() < deadline and not ("arl" in cookie_box and "sid" in cookie_box):
                time.sleep(poll_interval)
                for cookie in driver.get_cookies():
                    name = cookie.get("name")
                    if name in ("arl", "sid") and name not in cookie_box:
                        cookie_box[name] = cookie.get("value")
            # Save cookie_box in the config file under [cookies]
            try:
                config.read(config_file)
                if not config.has_section("cookies"):
                    config.add_section("cookies")
                for name in ("sid", "arl"):
                    if name in cookie_box:
                        config.set("cookies", name, cookie_box[name])
                with open(config_file, "w") as f:
                    config.write(f)
            except Exception as e:
                print(f"Warning: couldn't save cookie file {config_file}: {e}")

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
        results = self.get_api("deezer.getUserData")
        self.api_token = results['checkForm']
        user_info = results["USER"]
        self.user_id = user_info["USER_ID"]
        pass

    def get_api(self, method: str, body: dict = None) -> dict:
        payload = {
            "api_version": "1.0",
            "api_token": self.api_token,
            "input": "3",
            "method": method,
        }
        resp = self.session.post(self.API_URL, params=payload, json=body)
        resp.raise_for_status()
        if resp.text != '':
            return resp.json()['results']
        else:
            return

    def get_profile_data(self, tab: str, nb: int = 100) -> dict:
        body = {
            'user_id': self.user_id,
            'tab': tab,
            'nb': nb
        }
        results = self.get_api("deezer.pageProfile", body)
        return results

    def get_artist_data(self, artist_id: int, tab: int = 0) -> list:
        body = {
            "art_id": artist_id,
            "lang": "fr",
            "tab": tab
        }
        results = self.get_api("deezer.pageArtist", body)
        return results

    def get_songs(self, album_id: int):
        body = {
            "alb_id": album_id,
            "nb": 100,
            "start": 0
        }
        results = self.get_api("song.getListByAlbum", body)
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
        results = self.get_api("playlist.create", body)
        pass

    def add_songs_to_playlist(self, songs_list: list, playlist_id: int):
        body = {
            "playlist_id": str(playlist_id),
            "songs": songs_list,
            "offset": -1,
            "order": 0,
            "replace": False
        }
        results = self.get_api("playlist.addSongs", body)
        pass

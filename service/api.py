import requests
from http.cookiejar import MozillaCookieJar

class DeezerAPI:
    API_URL = "https://www.deezer.com/ajax/gw-light.php"

    @classmethod
    def __init__(self, cookie_file: str):
        self.session = requests.Session()
        self.api_token = ""
        self.set_session_params(cookie_file)
        self.get_user_data()
        pass

    def set_session_params(self, cookie_file: str):
        cookie_jar = MozillaCookieJar(cookie_file)
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        self.session.cookies.update({
            cookie.name: cookie.value for cookie in cookie_jar
            if cookie.name == "arl" or cookie.name == "sid"
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
        print(results)
        self.api_token = results['checkForm']
        user_info = results["USER"]
        self.user_id = user_info["USER_ID"]
        if not self.api_token:
            raise RuntimeError("Impossible de récupérer checkForm (vérifier le cookie 'arl' et la session).")
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
        return resp.json()['results']

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
        print(results)
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
        print(results)
        pass

import requests
from http.cookiejar import MozillaCookieJar
import json
import pandas as pd


class playlist_creation():

    def __init__(self, playlist_name, artists_list, cookie_file):
        self.playlist_name = playlist_name
        self.session = requests.Session()
        self.api_token = ""
        self.artists_list = artists_list
        self.set_session_params(cookie_file)
        self.get_apitoken_and_userid()
        self.set_song_list_to_add()
        # print(self.songs_to_add)
        self.create_playlist(False)
        self.get_last_playlist_id()
        self.add_songs_to_playlist()
        pass

    def set_session_params(self, cookie_file: str):
        cj = MozillaCookieJar(cookie_file)
        cj.load(ignore_discard=True, ignore_expires=True)
        self.session.cookies.update({c.name: c.value for c in cj if c.name == "arl" or c.name == "sid"})
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible)',
            'Referer': 'https://www.deezer.com/',
            'Origin': 'https://www.deezer.com',
            'Content-Type': 'application/json'
        })
        pass

    def ajax_api_request(self, method: str, body: dict)->requests.Response:
        API_URL = "https://www.deezer.com/ajax/gw-light.php"
        payload = {
            "api_version": "1.0",
            "api_token": self.api_token,
            "input": "3",
            "method": method,
        }
        resp = self.session.post(API_URL, params=payload, json=body)
        resp.raise_for_status()
        return resp

    def get_apitoken_and_userid(self):
        resp = self.ajax_api_request("deezer.getUserData",{})
        print(resp)
        js = resp.json()
        if isinstance(js, dict):
            results = js.get('results') or {}
            self.api_token = results.get('checkForm') or results.get('CHECKFORM') or results.get('check_form') #à voir si il y a vraiment besoin de toutes les formes mais au début ça marchait pas 
            user_info = results.get("USER")
            self.user_id = user_info.get("USER_ID")
        if not self.api_token:
            raise RuntimeError("Impossible de récupérer checkForm (vérifie le cookie 'arl' et la session).")
        pass

    def get_album_tracks(self, album_id: int) -> pd.DataFrame:
        body = {
            "alb_id": album_id,
            "nb": 100,
            "start": 0
        }
        resp = self.ajax_api_request("song.getListByAlbum", body)
        data = resp.json()
        tracks = data["results"].get("data", [])
        # print(tracks[0])
        tracks_list = pd.DataFrame({"Track_id": [t["SNG_ID"] for t in tracks ],
                            "Artist_id": [int(t["ART_ID"]) for t in tracks]})
        return tracks_list

    def get_albums_by_artist(self, artist_id: int) -> list:
        body = {
            "art_id": artist_id,
            "lang": "fr",
            "tab": 0
        }
        resp = self.ajax_api_request("deezer.pageArtist", body)
        data = resp.json()
        results = data["results"]
        albums_list = results['ALBUMS']['data']
        albums_ids = [a["ALB_ID"] for a in albums_list]
        return albums_ids

    def get_all_tracks_from_artist(self, art_id: int) -> pd.DataFrame:
        tracks_df = pd.DataFrame([])
        album_ids = self.get_albums_by_artist(art_id)
        for alb_id in album_ids:
            album_tracks_df = self.get_album_tracks(alb_id)
            tracks_df = pd.concat([tracks_df,album_tracks_df], ignore_index=True)
        tracks_df.drop_duplicates(inplace=True)
        # print(tracks_df.dtypes)
        # print(tracks_df)
        return tracks_df[tracks_df["Artist_id"] == art_id]

    def set_song_list_to_add(self):
        self.songs_to_add = pd.DataFrame([])
        for art_id in self.artists_list:
            tracks_df = self.get_all_tracks_from_artist(art_id)
            self.songs_to_add = pd.concat([self.songs_to_add,tracks_df.sample(n=3)], ignore_index=True)
        pass

    def create_playlist(self, public):
        body = {
            "title": self.playlist_name,
            "description": "test",
            "status": 0 if public else 1,
            "tags": "",
            "songs": [],
            "collaborative": False
        }
        resp = self.ajax_api_request("playlist.create", body)
        print(resp.text)
        pass

    def get_last_playlist_id(self):
        body = {
            'user_id': self.user_id,
        }
        resp = self.ajax_api_request("deezer.pageProfile", body)
        js = json.loads(resp.text)
        playlists_data = js.get("results").get("TAB").get("home").get("playlists")
        last_playlist = playlists_data["data"][0]
        self.playlist_id = last_playlist['PLAYLIST_ID']
        pass

    def add_songs_to_playlist(self):
        songs_list_formated = [[s,0] for s in self.songs_to_add['Track_id']]
        body = {
            "playlist_id": str(self.playlist_id),
            "songs": songs_list_formated,
            "offset": -1,
            "order": 0,
            "replace": False
        }
        resp = self.ajax_api_request("playlist.addSongs", body)
        print(resp.text)
        return



if __name__ == "__main__":
    #Constantes pour tester
    # PLAYLIST_NAME = "testMulti3"
    # ALBUM_ID = 302127
    ARTIST_IDS = [111636522,10192306,375308,817174,810503,137537962,1355757,167710,58801,1296451] #liste d'aritste avec des trucs pour faire plaisir à Nico parce qu'il m'a fait péter les couilles
    test = playlist_creation("testMulti4", ARTIST_IDS, "cookies.txt")




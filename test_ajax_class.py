import requests
from http.cookiejar import MozillaCookieJar
import json
import pandas as pd
import numpy as np


class playlist_creation():

    def __init__(self, cookie_file: str):
        self.session = requests.Session()
        self.api_token = ""
        self.set_session_params(cookie_file)
        self.get_apitoken_and_userid()
        pass

    def test(self,artist_id):
        body = {
            "art_id": artist_id,
            "lang": "fr",
            "nb": 50,
            "tab": 1
        }
        # resp = self.ajax_api_request("artist.getSelectedAndRelatedArtist", body)
        resp = self.ajax_api_request("deezer.pageArtist", body)
        data = resp.json()
        print(data.keys())
        # data = data["error"]
        # print(data)
        data = data["results"]
        print(data.keys())
        data = data["RELATED_ARTISTS"]
        print(data['count'])
        print(data['total'])
        names =[d['ART_NAME'] for d in data['data']]
        print(names)
        # print(data)
        # print(data.keys())
        pass

# Auth class

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

    def ajax_api_request(self, method: str, body: dict) -> requests.Response:
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

    def get_favorite_artists(self) -> pd.DataFrame:
        body = {
            'user_id': self.user_id,
            'tab': 'artists',
            'nb': 10000
        }
        resp = self.ajax_api_request("deezer.pageProfile", body)
        data = resp.json()
        data = data["results"]['TAB']['artists']['data']
        favorite_artists = pd.DataFrame({"Artist_id": [int(a["ART_ID"]) for a in data],
                                         "Artist_name": [a["ART_NAME"] for a in data]})
        favorite_artists.sort_values(by="Artist_name",inplace=True)
        favorite_artists.reset_index(inplace=True)
        return favorite_artists

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

    def get_album_tracks(self, album_id: int) -> pd.DataFrame:
        body = {
            "alb_id": album_id,
            "nb": 100,
            "start": 0
        }
        resp = self.ajax_api_request("song.getListByAlbum", body)
        data = resp.json()
        tracks = data["results"].get("data", [])
        tracks_list = pd.DataFrame({"Track_id": [t["SNG_ID"] for t in tracks ],
                            "Artist_id": [int(t["ART_ID"]) for t in tracks]})
        return tracks_list

    def create_playlist(self, name: str, public: bool):
        body = {
            "title": name,
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

    def get_related_artists(self, artist_id: int) -> list:
        body = {
            "art_id": artist_id,
            "lang": "fr",
            "tab": 1,
            "nb": 100
        }
        resp = self.ajax_api_request("deezer.pageArtist", body)
        data = resp.json()
        data = data["results"]['RELATED_ARTISTS']['data']
        related_artists = [int(a['ART_ID']) for a in data]
        return related_artists


#Secondary class

    def get_related_artists_list(self, base_list: list) -> list:
        related_list = []
        for art_id in base_list:
            tmp = self.get_related_artists(art_id)
            related_list += tmp
        full_df = pd.DataFrame({"related_artist": related_list})
        sorted_df = full_df.groupby(["related_artist"],as_index=False).value_counts().sort_values(by="count", ascending=False)
        return sorted_df[sorted_df["count"]>1]["related_artist"].to_list()



    def set_song_list_to_add(self, tracks_by_artist: int):
        self.songs_to_add = pd.DataFrame([])
        for art_id in self.artists_list:
            tracks_df = self.get_all_tracks_from_artist(art_id)
            self.songs_to_add = pd.concat([self.songs_to_add,tracks_df.sample(n=tracks_by_artist)], ignore_index=True)
        pass

    def get_all_tracks_from_artist(self, art_id: int) -> pd.DataFrame:
        tracks_df = pd.DataFrame([])
        album_ids = self.get_albums_by_artist(art_id)
        for alb_id in album_ids:
            album_tracks_df = self.get_album_tracks(alb_id)
            tracks_df = pd.concat([tracks_df,album_tracks_df], ignore_index=True)
        tracks_df.drop_duplicates(inplace=True)
        return tracks_df[tracks_df["Artist_id"] == art_id]




    def create_artist_list(self, max_selection: int, include_relative: bool) -> list:
        self.max_selection = max_selection
        selected_favorites = self.base_artists_selection()
        self.artists_list = selected_favorites
        if include_relative:
            self.artists_list += self.get_related_artists_list(selected_favorites)
        print(f"{self.max_selection} artistes choisis, et {len(self.artists_list)} au total")
        pass

    def base_artists_selection(self) -> list:
        question = "Choisissez des artistes parmis vos favoris."
        print(question)
        favoris = self.get_favorite_artists()
        with pd.option_context('display.max_rows', None):
            print(favoris["Artist_name"])
        selected_artists = []
        for n in range(1,self.max_selection+1):
            i = int(input(f"Entrez l'indice de l'artiste {n}: "))
            selected_artists.append(int(favoris.iloc[i,1]))
        return selected_artists

    def create_playlist_with_songs(self, name: str, public: bool):
        self.create_playlist(name, public)
        self.get_last_playlist_id()
        self.add_songs_to_playlist()
        pass





if __name__ == "__main__":
    #Constantes pour tester
    # PLAYLIST_NAME = "testMulti3"
    # ALBUM_ID = 302127
    # ARTIST_IDS = [111636522,10192306,375308,817174,810503,137537962,1355757,167710,58801,1296451] #liste d'aritste avec des trucs pour faire plaisir à Nico parce qu'il m'a fait péter les couilles
    test = playlist_creation("cookies.txt")
    test.create_artist_list(max_selection=3, include_relative=True)
    test.set_song_list_to_add(tracks_by_artist=3)
    test.create_playlist_with_songs(name="TestWithFav2", public=False)




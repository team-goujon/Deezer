import requests
from http.cookiejar import MozillaCookieJar
import json
import pandas as pd
import numpy as np


class test_method_ajax_api():

    def __init__(self, cookie_file: str, method: str, body: json, recover_user_id: bool, see_keys: bool):
        self.session = requests.Session()
        self.api_token = ""
        self.set_session_params(cookie_file)
        self.get_apitoken_and_userid()
        self.test(method,body,recover_user_id,see_keys)
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

    def test(self, method: str, body: json, recover_user_id: bool, see_keys: bool):
        if recover_user_id:
            body["user_id"] = self.user_id
            print(body)
        resp = self.ajax_api_request(method, body)
        data = resp.json()
        print(data.keys())
        if data['error'] != []:
            print("Erreur dans la requête")
            print(data["error"])
        if see_keys:
            self.go_through_keys(data)
        pass

    def go_through_keys(self, data: json):
        data = data["results"]
        print(data.keys())
        temp_data = data
        flag = True
        path = []
        while flag:
            chosen_key = input("Choose json keys to go deeper, 1 to go one level up, 0 to go back to 'results', leave empty to quit: ")
            match chosen_key:
                case '':
                    flag = False
                case '0':
                    path = []
                    temp_data = data
                case '1':
                    temp_data = self.go_up(data, temp_data, path)
                case _:
                    if chosen_key in temp_data:
                        path.append(chosen_key)
                        temp_data = temp_data[chosen_key]
                        if type(temp_data) != dict:
                            print(type(temp_data))
                            if input("print data y/n ? ") == "y":
                                if type(temp_data) == list and temp_data != []:
                                    print(temp_data[0])
                                else:
                                    print(temp_data)
                            temp_data = self.go_up(data, temp_data, path)
                    else:
                        print("Wrong key")
            if flag:
                print(temp_data.keys())
        pass

    def go_up(self, data, temp_data, path):
        path.pop()
        temp_data = data
        for k in path:
            temp_data = temp_data[k]
        return temp_data


if __name__ == "__main__":
    #Constantes pour tester
    # PLAYLIST_NAME = "testMulti3"
    # ALBUM_ID = 302127
    # ARTIST_IDS = [111636522,10192306,375308,817174,810503,137537962,1355757,167710,58801,1296451] #liste d'aritste avec des trucs pour faire plaisir à Nico parce qu'il m'a fait péter les couilles

    #body pageArtist
    method = "deezer.pageArtist"
    recover_user_id = False
    body = {
            "art_id": 810503,
            "lang": "fr",
            "count": 20,
            "tab": 1 #0 pour les albums, 1 pour tous les artistes semblables
        }

    # #body pageProfile
    # method = "deezer.pageProfile"
    # recover_user_id = True
    # body = {
    #         # 'user_id': user_id,
    #         'tab': 'home',
    #         'nb': 10000
    #     }

    test = test_method_ajax_api("cookies.txt", method, body, recover_user_id, True)

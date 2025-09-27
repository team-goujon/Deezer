import requests
from http.cookiejar import MozillaCookieJar
import json
import pandas as pd

API_URL = "https://www.deezer.com/ajax/gw-light.php"

def get_checkform_and_session(cookie_file="cookies.txt"):
    """Créé une session, qu'on réutilise pour toutes les autres requêtes, basé sur les cookies de .deezer.com et fais une requête pour récupérer l'api_token et l'user_id
        ya ptet des trucs inutiles qu'à mis chat gpt là dedans

    Args:
        cookie_file (str, optional): fichier avec les cookies (récupérés dans chrome et stockés dans cookies.txt)

    Returns:
        s: session pour les autres requêtes
        api_token: comme le port-salut
        user_id: idem
    """
    
    s = requests.Session()
    cj = MozillaCookieJar(cookie_file)
    cj.load(ignore_discard=True, ignore_expires=True)
    s.cookies.update({c.name: c.value for c in cj if c.name == "arl" or c.name == "sid"})
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible)',
        'Referer': 'https://www.deezer.com/',
        'Origin': 'https://www.deezer.com',
        'Content-Type': 'application/json'
    })

    params = {
        'method': 'deezer.getUserData',
        'input': '3',
        'api_version': '1.0',
        'api_token': ''
    }

    r = s.post(API_URL, params=params, json={})
    r.raise_for_status()
    js = r.json()

    checkform = None
    user_id = None
    if isinstance(js, dict):
        results = js.get('results') or {}
        checkform = results.get('checkForm') or results.get('CHECKFORM') or results.get('check_form') #à voir si il y a vraiment besoin de toutes les formes mais au début ça marchait pas 
        user_info = results.get("USER")
        user_id = user_info.get("USER_ID")
    if not checkform:
        raise RuntimeError("Impossible de récupérer checkForm (vérifie le cookie 'arl' et la session).")
    # print(user_id)
    return s, checkform, user_id

def get_album_tracks(session: requests.Session, api_token, album_id):
    """Récuère les ids des tracks d'un album à partir de l'album_id de deezer

    Args:
        session (requests.Session): session des requêtes
        api_token (str):
        album_id (int):

    Returns:
        Dataframe: Dataframe avec les ids des tracks (j'ai fait une Dataframe parceque j'imagine qu'on récupèrera d'autres infos)
    """
    payload = {
        "api_version": "1.0",
        "api_token": api_token,
        "input": "3",
        "method": "song.getListByAlbum",
    }
    body = {
        "alb_id": album_id,
        "nb": 50,
        "start": 0
    }
    resp = session.post(API_URL, params=payload, json=body)
    resp.raise_for_status()
    data = resp.json()

    tracks = data["results"].get("data", [])
    # tracks_names = [t["SNG_TITLE"] for t in tracks]
    tracks_ids = [t["SNG_ID"] for t in tracks]
    # print(tracks[0])

    return pd.DataFrame(tracks_ids,columns=["Track_id"])

def get_albums_by_artist(session: requests.Session, api_token, artist_id):
    """Récupère la liste des albums d'un artiste

    Args:
        session (requests.Session): session des requêtes
        api_token (str):
        artist_id (int):

    Returns:
        list: list des ids d'albums
    """
    payload = {
        "api_version": "1.0",
        "api_token": api_token,
        "input": "3",
        "method": "deezer.pageArtist",
    }
    body = {
        "art_id": artist_id,
        "lang": "fr",
        "tab": 0
    }
    resp = session.post(API_URL, params=payload, json=body)
    resp.raise_for_status()
    data = resp.json()
    results = data["results"]
    print(results.keys())
    print(results["DATA"]["DATA"].keys())
    albums_list = results['ALBUMS']['data']
    albums_ids = [a["ALB_ID"] for a in albums_list]
    return albums_ids

def create_playlist(session: requests.Session, api_token, name, songs_ids, public):
    """Crée une playlist, à priori on devrait pouvoir mettre les tracks direct mais ça veut pas, il faut que je check le payload dans chrome il manque peut être des choses
        Et en plus la réponse de la requête est vide, et chat gpt avait l'air de penser qu'on devrait recevoir des infos de la playlist avec notamment l'id de la playlist

    Args:
        session (requests.Session): session des requêtes
        api_token (str):
        name (str): nom de la playlist
        songs_ids (list):
        public (bool):
    """
    payload = {
        "api_version": "1.0",
        "api_token": api_token,
        "input": "3",
        "method": "playlist.create",
    }
    body = {
        "title": name,
        "description": "test",
        "status": 0 if public else 1,
        "tags": "",
        "songs": [],
        "collaborative": False
    }

    resp = session.post(API_URL, params=payload, json=body)
    resp.raise_for_status()
    # js = json.loads(resp.text)
    print(resp.text)
    return

def get_last_playlist_id(session: requests.Session, api_token, user_id):
    """Récupère l'id de la dernière playlist créée vu que je l'ai pas avec l'autre fonction :(
        mais par contre on peut sûrement utilisé ce type de requête pour récupérer les favoris

    Args:
        session (requests.Session): _description_
        api_token (_type_): _description_
        user_id (_type_): _description_

    Returns:
        int: id de la dernière playlist créée
    """
    params = {
        'method': 'deezer.pageProfile',
        'input': '3',
        'api_version': '1.0',
        'api_token': api_token
    }
    body = {
        'user_id': user_id,
    }

    r = session.post(API_URL, params=params, json=body)
    r.raise_for_status()
    # print(r.text)
    js = json.loads(r.text)
    # print(js.keys())
    playlists_data = js.get("results").get("TAB").get("home").get("playlists")
    last_playlist = playlists_data["data"][0]
    last_playlist_id = last_playlist['PLAYLIST_ID']
    # print(last_playlist)
    return last_playlist_id

def add_songs_to_playlist(session: requests.Session, api_token, playlist_id, songs_list):
    """Ajoute des tracks à la playlist avec l'id playlist_id

    Args:
        session (requests.Session): _description_
        api_token (_type_): _description_
        play_list_id (_type_): _description_
        songs_list (_type_): _description_
    """
    songs_list_formated = [[s,0] for s in songs_list] #Ca j'ai vu en vérifiant la requête dans chrome en ajoutant des tracks à la main, je sais pas du tout à quoi sert le 0 ou ce que ça fait si on met une autre valeur
    # print(songs_list_formated)
    payload = {
        "api_version": "1.0",
        "api_token": api_token,
        "input": "3",
        "method": "playlist.addSongs",
    }
    body = {
        "playlist_id": str(playlist_id),
        "songs": songs_list_formated,
        "offset": -1,
        "order": 0,
        "replace": False
    }

    resp = session.post(API_URL, params=payload, json=body)
    resp.raise_for_status()
    print(resp.text)

if __name__ == "__main__":
    #Faut faire des fonctions avec ce qu'il y a dessous mais c'était pour tester
    #Constantes pour tester
    PLAYLIST_NAME = "testMulti2"
    ALBUM_ID = 302127
    ARTIST_IDS = [111636522,10192306,375308,817174,810503,137537962,1355757,167710,58801,1296451] #liste d'aritste avec des trucs pour faire plaisir à Nico parce qu'il m'a fait péter les couilles

    songs_to_add = pd.DataFrame([])

    #pour initialiser
    session, token, user_id =  get_checkform_and_session("cookies.txt")

    #Boucle sur ma liste d'artiste pour récupérer toutes les tracks de tous leurs albums et en prendre 3 random (pas sûr de la qualité du random) à chaque fois
    for art_id in ARTIST_IDS:
        tracks_df = pd.DataFrame([])
        album_ids = get_albums_by_artist(session, token, art_id)
        for alb_id in album_ids:
            album_tracks_df = get_album_tracks(session, token, alb_id)
            tracks_df = pd.concat([tracks_df,album_tracks_df], ignore_index=True)
        tracks_df.drop_duplicates(inplace=True)
        songs_to_add = pd.concat([songs_to_add,tracks_df.sample(n=3)], ignore_index=True)

    #Création de la playlist, récupération de l'id et ajout des tracks
    create_playlist(session, token, PLAYLIST_NAME, [], False)
    playlist_id = get_last_playlist_id(session, token, user_id)
    add_songs_to_playlist(session, token, playlist_id, songs_to_add["Track_id"])




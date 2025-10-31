from service import DeezerService
import pandas as pd
import logging
from utils.logging_manager import *
logger = logging.getLogger(__name__)

def main():
    try:
        newServ = DeezerService()
        playlist_name = input('Entrez le nom de la playlist: ')
        public = yesno_input('La playlist est-elle publique ?')
        n_artists = int_input("Combien d'artistes ?")
        user_selection = pd.DataFrame([])
        if yesno_input("Choisir les artistes manuellement ?"):
            user_favorites = newServ.get_user_favorites_artists()
            user_selection = get_user_selection(user_favorites, n_artists)
        else:
            newServ.number_random_artists = n_artists
        relative = yesno_input("Inclure les artistes semblables ?")
        n_tracks = int_input("Combien de titres par artiste ?") 
        newServ.number_tracks_by_artist = n_tracks
        newServ.create_playlist(playlist_name, public, user_selection, relative)
        pass
    except Exception as e:
        logger.error(f"{e.__class__.__name__}: {e}")

@debugging
def get_user_selection(user_favorites: pd.DataFrame, number_selected_artists: int) -> pd.DataFrame:
    with pd.option_context('display.max_rows', None):
        print(user_favorites['ART_NAME'])
    selected_index = []
    for i in range(1,number_selected_artists+1):
        n = int_input(f"Entrez l'indice de l'artiste {i}: ")
        selected_index.append(n)
    selected_artists = user_favorites.loc[selected_index,:]
    return selected_artists

def yesno_input(prompt: str) -> bool:
    resp = input(prompt + ' (y/n): ')
    return resp.lower() == 'y'

def int_input(prompt: str) -> int:  
    while True:
        resp = input(prompt + ': ')
        if resp.isdigit() == False:
            print("Veuillez entrer un entier valide.")
        else:
            return int(resp)

if __name__ == '__main__':
    main()
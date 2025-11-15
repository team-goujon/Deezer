from service import DeezerService
import pandas as pd
import logging
from utils.logging_manager import *
from utils.schema import *
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
    number_selected_artists = min(number_selected_artists, len(user_favorites))
    print(f"Sélectionnez {number_selected_artists} artistes en entrant leurs indices:")
    for i in range(number_selected_artists):
        n = int_input(f"Artiste {i+1}: ")
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

def test():
    try:
        logger.debug("DeezerService test method called")
        service = DeezerService()
        artist_data = service.session.get_profile_data(tab='home')
        print(service.session.get_profile_data.__name__)
        # print(artist_data['RELATED_ARTISTS'].keys())
        # print(type(artist_data['ALBUMS']['data']))
        # print(type(artist_data['ALBUMS']['data'][0]))
        validate(instance=artist_data, schema=playlist_id_schema,)
        logger.debug("Data structure is valid according to schema")
    except ValidationError as ve:
        logger.error(f"ValidationError: {ve.message}")
    

if __name__ == '__main__':
    # test()
    main()
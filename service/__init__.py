import pandas as pd
import numpy as np
from service.api import DeezerAPI
from utils.configuration import *
import logging
from utils.logging_manager import *
logger = logging.getLogger(__name__)

class DeezerService():
    
    def __init__(self):
        self.config = get_config_section("service")
        self.session = DeezerAPI()
        self.number_random_artists = int(self.config.get("random_artists_number", 10))
        self.number_tracks_by_artist = int(self.config.get("tracks_by_artist_number", 3))
        pass

    def create_playlist(self, name: str, public: bool, user_selection: pd.DataFrame, include_relative: bool = False):
        try:
            user_favorites = self.get_user_favorites_artists()
            if user_selection.empty:
                self.selected_artists = user_favorites.sample(n=self.number_random_artists)
            else:
                self.selected_artists = user_selection
            if include_relative:
                self.selected_artists = self.__add_related_artists()
            track_list = self.__set_random_tracks_list()
            self.__save_playlist_on_deezer_profile(name, public, track_list)
            pass
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}")

    def get_user_favorites_artists(self) -> pd.DataFrame:
        try:
            data = self.session.get_profile_data(tab='artists')
            data = data['TAB']['artists']['data']
            favorite_artists = pd.DataFrame(data)
            favorite_artists.sort_values(by='ART_NAME',inplace=True)
            favorite_artists.reset_index(drop=True,inplace=True)
            return favorite_artists[['ART_ID', 'ART_NAME', 'ART_PICTURE']]
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}")

    @debugging
    def __add_related_artists(self) -> pd.DataFrame:
        try:
            selected_artists = self.selected_artists
            related_artists = pd.DataFrame([])
            for art_id in selected_artists['ART_ID']:
                related = self.__get_related_artists(art_id)
                related_artists = pd.concat([related_artists,related], ignore_index=True)
            self.__checking_dataframe(related_artists, ['ART_ID', 'ART_NAME', 'ART_PICTURE'], "Related artists")
            sorted_related_artists = related_artists.groupby(['ART_ID'],as_index=False).value_counts().sort_values(by="count", ascending=False)
            sorted_related_artists = sorted_related_artists[sorted_related_artists['count'] > 1]
            all_artists = pd.concat([selected_artists, sorted_related_artists[['ART_ID', 'ART_NAME', 'ART_PICTURE']]], ignore_index=True)
            return all_artists
        except DeezerServiceError as dse:
            logger.warning(f"{dse.__class__.__name__}: {dse.message}")
            return selected_artists

    def __get_related_artists(self, artist_id: str) -> pd.DataFrame:
        try:
            data = self.session.get_artist_data(artist_id, tab=1)
            if 'RELATED_ARTISTS' not in data:
                raise DeezerServiceError(f"Artist ID {artist_id} has no related artists data")
            data = data['RELATED_ARTISTS']['data']
            relative_artists = pd.DataFrame(data)
            self.__checking_dataframe(relative_artists, ['ART_ID', 'ART_NAME', 'ART_PICTURE'], f"Related artists for artist ID {artist_id}")
            return relative_artists[['ART_ID', 'ART_NAME', 'ART_PICTURE']]
        except DeezerServiceError as dse:  
            logger.warning(f"{dse.__class__.__name__}: {dse.message}")
            return pd.DataFrame([])
    
    @debugging
    def __set_random_tracks_list(self):
        artist_list = self.selected_artists['ART_ID'].to_numpy()
        artist_list = np.append(artist_list, '352227652')
        logger.debug(f"Selected artists IDs: {artist_list}")
        tracks_list = pd.DataFrame([])
        for a in artist_list:
            artist_tracks = self.__get_tracks_by_artist(a)
            if not artist_tracks.empty:
                tracks_list = pd.concat([tracks_list,artist_tracks.sample(n=self.number_tracks_by_artist)], ignore_index=True)
        if tracks_list.empty:
            raise DeezerServiceError("No tracks found for the selected artists")
        return tracks_list

    def __get_tracks_by_artist(self, artist_id: str) -> pd.DataFrame:
        try:
            data = self.session.get_artist_data(artist_id)
            if 'ALBUMS' not in data:
                raise DeezerServiceError(f"Artist ID {artist_id} has no albums data")
            albums = pd.DataFrame(data['ALBUMS']['data'])
            self.__checking_dataframe(albums, ['SONGS'], f"Albums for artist ID {artist_id}")
            albums['SONGS_LIST'] = albums['SONGS'].apply(lambda x: x['data'] if 'data' in x else [])
            tracks_by_album = albums['SONGS_LIST'].to_numpy()
            tracks_by_album = sum(tracks_by_album, [])
            tracks = pd.DataFrame(tracks_by_album)
            self.__checking_dataframe(tracks, ['SNG_ID','SNG_TITLE','ART_ID'], f"Tracks for artist ID {artist_id}")
            tracks = tracks[tracks['ART_ID']==artist_id]
            return tracks[['SNG_ID','SNG_TITLE','ART_ID']]
        except DeezerServiceError as dse:
            logger.warning(f"{dse.__class__.__name__}: {dse.message}")
            return pd.DataFrame([])

    def __save_playlist_on_deezer_profile(self, name: str, public: bool, songs_df: pd.DataFrame):
        self.session.create_playlist(name=name, description="", public=public)
        playlist_id = self.__get_last_playlist_id()
        songs_list_formated = [[s,0] for s in songs_df['SNG_ID']]
        self.session.add_songs_to_playlist(songs_list_formated, playlist_id)
        pass

    def __get_last_playlist_id(self) -> str:
        data = self.session.get_profile_data(tab='home')
        user_playlists = data['TAB']['home']['playlists']
        last_playlist = user_playlists['data'][0]
        return last_playlist['PLAYLIST_ID']
    
    def __checking_dataframe(self, df: pd.DataFrame, required_columns: list, name: str) -> bool:
        if df.empty:
            raise DeezerServiceError(f"{name} data is empty")
        for col in required_columns:
            if col not in df.columns:
                raise DeezerServiceError(f"{name} data is missing required column: {col}")
        pass
    
class DeezerServiceError(Exception):
    """Base class for exceptions in DeezerService."""
    def __init__(self, message: str):
        self.message = message
    pass

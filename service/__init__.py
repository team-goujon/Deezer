import pandas as pd
from service.api import DeezerAPI
import logging
from logging_manager import log_function
logger = logging.getLogger(__name__)

class DeezerService():
    def __init__(self, cookies: str):
        self.session = DeezerAPI(cookies)
        self.number_random_artists: int = 10
        self.number_tracks_by_artist: int = 3
        pass

    def create_playlist(self, name: str, public: bool, user_selection: pd.DataFrame, include_relative: bool = False):
        try:
            user_favorites = self.get_user_favorites_artists()
            if user_selection.empty:
                selected_artists = user_favorites.sample(n=self.number_random_artists)
            else:
                selected_artists = user_selection
            if include_relative:
                selected_artists = self.__add_related_artists(user_selection)
            track_list = self.__set_random_tracks_list(selected_artists, False)
            self.__save_playlist_on_deezer_profile(name, public, track_list)
            pass
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}")

    @log_function
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

    def __add_related_artists(self, selected_artists: pd.DataFrame) -> pd.DataFrame:
        related_artists = pd.DataFrame([])
        for art_id in selected_artists['ART_ID']:
            related = self.__get_related_artists(art_id)
            related_artists = pd.concat([related_artists,related], ignore_index=True)
        sorted_related_artists = related_artists.groupby(['ART_ID'],as_index=False).value_counts().sort_values(by="count", ascending=False)
        sorted_related_artists = sorted_related_artists[sorted_related_artists['count'] > 1]
        all_artists = pd.concat([selected_artists, sorted_related_artists[['ART_ID', 'ART_NAME', 'ART_PICTURE']]], ignore_index=True)
        return all_artists

    def __get_related_artists(self, artist_id: int) -> pd.DataFrame:
        data = self.session.get_artist_data(artist_id=artist_id, tab=1)
        data = data['RELATED_ARTISTS']['data']
        relative_artists = pd.DataFrame(data)
        return relative_artists[['ART_ID', 'ART_NAME', 'ART_PICTURE']]

    def __set_random_tracks_list(self, artist_list: pd.DataFrame, related: bool):
        tracks_list = pd.DataFrame([])
        for a in artist_list['ART_ID']:
            artist_tracks = self.__get_tracks_by_artist(a)
            tracks_list = pd.concat([tracks_list,artist_tracks.sample(n=self.number_tracks_by_artist)], ignore_index=True)
        return tracks_list

    def __get_tracks_by_artist(self, artist_id: int) -> pd.DataFrame:
        data = self.session.get_artist_data(artist_id=artist_id)
        data = data['ALBUMS']['data']
        albums = pd.DataFrame(data)
        albums['SONGS_LIST'] = albums['SONGS'].apply(lambda x: x['data'])
        tracks_by_album = albums['SONGS_LIST'].to_numpy()
        tracks_by_album = sum(tracks_by_album, [])
        tracks = pd.DataFrame(tracks_by_album)
        tracks = tracks[tracks['ART_ID']==artist_id]
        return tracks[['SNG_ID','SNG_TITLE','ART_ID']]

    def __save_playlist_on_deezer_profile(self, name: str, public: bool, songs_df: pd.DataFrame):
        self.session.create_playlist(name=name, description="", public=public)
        playlist_id = self.__get_last_playlist_id()
        songs_list_formated = [[s,0] for s in songs_df['SNG_ID']]
        self.session.add_songs_to_playlist(songs_list=songs_list_formated, playlist_id=playlist_id)
        pass

    @log_function
    def __get_last_playlist_id(self) -> str:
        data = self.session.get_profile_data(tab='home')
        user_playlists = data['TAB']['home']['playlists']
        last_playlist = user_playlists['data'][0]
        return last_playlist['PLAYLIST_ID']



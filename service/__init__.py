import pandas as pd
from service.api import DeezerAPI
from utils.configuration import get_config_section
import logging
from utils.logging_manager import debugging
from pydantic import ValidationError
from utils.exceptions import DeezerServiceError
from utils.models import GoujonPlaylistModel
logger = logging.getLogger(__name__)

class DeezerService:

    def __init__(self):
        self.config = get_config_section("service")
        self.api = DeezerAPI()

    def create_playlist(self, playlist_to_create: GoujonPlaylistModel, options: dict) -> GoujonPlaylistModel:
        try:
            if options['mode'] == 'Favorites':
                user_favorites = self.__get_user_favorites_artists()
                playlist_to_create.selected_artists = user_favorites.sample(n=options['number_random_artists'])
            if options['include_relative']:
                playlist_to_create.selected_artists = self.__add_related_artists(playlist_to_create.selected_artists)
            playlist_to_create.track_list = self.__set_random_tracks_list(playlist_to_create.selected_artists, options['number_tracks_by_artist'])
            return playlist_to_create
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}")
            raise DeezerServiceError(str(e))

    # @debugging
    def set_artist_selection(self, mode) -> pd.DataFrame:
        try:
            if mode == 'Flow':
                return self.__get_flow_artists()
            return self.__get_user_favorites_artists()
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {e}")
            raise DeezerServiceError(str(e))

    # @debugging
    def __get_user_favorites_artists(self) -> pd.DataFrame:
        try:
            data = self.api.get_profile_data(tab='artists')
            data = data['TAB']['artists']['data']
            favorite_artists = pd.DataFrame(data)
            favorite_artists.sort_values(by='ART_NAME',inplace=True)
            favorite_artists.reset_index(drop=True,inplace=True)
            return favorite_artists[['ART_ID', 'ART_NAME', 'ART_PICTURE']]
        except ValidationError as e:
            logger.error(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
            raise DeezerServiceError("Failed to retrieve or validate user's favorite artists")

    # @debugging
    def __add_related_artists(self, selected_artists) -> pd.DataFrame:
        related_artists = pd.DataFrame([])
        for art_id in selected_artists['ART_ID']:
            related = self.__get_related_artists(art_id)
            related_artists = pd.concat([related_artists,related], ignore_index=True)
        if related_artists.empty:
            logger.warning("No related artists found")
            return selected_artists
        sorted_related_artists = related_artists.groupby(['ART_ID'],as_index=False).value_counts().sort_values(by="count", ascending=False)
        sorted_related_artists = sorted_related_artists[sorted_related_artists['count'] > 1]
        all_artists = pd.concat([selected_artists, sorted_related_artists], ignore_index=True).drop_duplicates().reset_index(drop=True)
        return all_artists

    # @debugging
    def __get_related_artists(self, artist_id: str) -> pd.DataFrame:
        try:
            data = self.api.get_artist_data(artist_id, tab=1)
            data = data['RELATED_ARTISTS']['data']
            relative_artists = pd.DataFrame(data)
            return relative_artists[['ART_ID', 'ART_NAME', 'ART_PICTURE']]
        except ValidationError as e:  
            logger.warning(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
            logger.warning(f"Failed to retrieve or validate related artists for artist ID {artist_id}")
            return pd.DataFrame([])
    
    # @debugging
    def __set_random_tracks_list(self, selected_artists, number_tracks_by_artist) -> pd.DataFrame:
        artist_list = selected_artists['ART_ID'].to_list()
        artist_list.append('352227652')
        logger.debug(f"Selected artists IDs: {artist_list}")
        tracks_list = pd.DataFrame([])
        for a in artist_list:
            artist_tracks = self.__get_tracks_by_artist(a)
            if not artist_tracks.empty:
                n_tracks = min(len(artist_tracks), number_tracks_by_artist)
                tracks_list = pd.concat([tracks_list,artist_tracks.sample(n=n_tracks)], ignore_index=True)
        if tracks_list.empty:
            raise DeezerServiceError("No tracks found for the selected artists")
        return tracks_list

    # @debugging
    def __get_tracks_by_artist(self, artist_id: str) -> pd.DataFrame:
        try:
            data = self.api.get_artist_data(artist_id, tab=0)
            albums = pd.DataFrame(data['ALBUMS']['data'])
            albums['SONGS_LIST'] = albums['SONGS'].apply(lambda x: x['data'] if 'data' in x else [])
            tracks = pd.DataFrame(albums['SONGS_LIST'].explode().tolist())
            tracks['DURATION'] = tracks['DURATION'].astype(int)
            filtered_tracks = tracks[(tracks['ART_ID']==artist_id)&(tracks['DURATION']>80)]
            return filtered_tracks[['SNG_ID','SNG_TITLE','ART_ID','ART_NAME', 'ART_PICTURE']]
        except ValidationError as e:
            logger.warning(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
            logger.warning(f"Failed to retrieve or validate tracks list for artist ID {artist_id}")
            return pd.DataFrame([])

    def save_playlist_on_deezer_profile(self, playlist_to_create: GoujonPlaylistModel):
        self.api.create_playlist(name=playlist_to_create.name, description="GoujonPlayslit", public=playlist_to_create.public)
        playlist_id = self.__get_last_playlist_id()
        songs_list = playlist_to_create.track_list['SNG_ID'].drop_duplicates().to_list()
        songs_list_formated = [[s,0] for s in songs_list]
        self.api.add_songs_to_playlist(songs_list_formated, playlist_id)
        pass

    def __get_last_playlist_id(self) -> str:
        try:
            data = self.api.get_profile_data(tab='home')
            user_playlists = data['TAB']['home']['playlists']
            last_playlist = user_playlists['data'][0]
            return last_playlist['PLAYLIST_ID']
        except ValidationError as e:
            logger.error(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
            raise DeezerServiceError("Failed to retrieve or validate user's playlists")
    
    def __get_flow_songs(self) -> dict:
        data = self.api.get_user_flow()
        flow_df = pd.DataFrame(data['data'])
        songs_df = flow_df[['SNG_ID', 'SNG_TITLE', 'ART_ID', 'ART_NAME']]
        return songs_df

    def __get_flow_artists(self) -> pd.DataFrame:
        data = self.api.get_user_flow()
        flow_df = pd.DataFrame(data['data'])
        artists_df = flow_df[['ART_ID', 'ART_NAME', 'ALB_PICTURE']].drop_duplicates().reset_index(drop=True)
        artists_df = artists_df.rename(columns={"ALB_PICTURE": "ART_PICTURE"})
        return artists_df
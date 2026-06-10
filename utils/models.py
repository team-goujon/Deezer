from pydantic import BaseModel, Field
import logging
logger = logging.getLogger(__name__)


# Models for artists data (used for favorite and related artists)
class ArtistModel(BaseModel):
    ART_ID: str
    ART_NAME: str
    ART_PICTURE: str

class ListArtistsModel(BaseModel):
    data: list[ArtistModel] = Field(..., min_length=1)


# Model to get related artists information
class GetRelatedArtistsModel(BaseModel):
    RELATED_ARTISTS: ListArtistsModel


# Models to get favorite artists
class TabArtistsModel(BaseModel):
    artists: ListArtistsModel

class GetUserFavoritesArtistsModel(BaseModel):
    TAB: TabArtistsModel


# Models to get playlist id
class PlaylistModel(BaseModel):
    PLAYLIST_ID: str

class ListPlaylistModel(BaseModel):
    data: list[PlaylistModel] = Field(..., min_length=1)

class AllPlaylistModel(BaseModel):
    playlists: ListPlaylistModel

class TabHomeModel(BaseModel):
    home: AllPlaylistModel

class GetLastPlaylistIdModel(BaseModel):
    TAB: TabHomeModel


# Models to get album songs information
class SongModel(BaseModel):
    SNG_ID: str
    SNG_TITLE: str
    DURATION: int
    ART_ID: str
    ART_NAME: str
    ART_PICTURE: str | None = None

# Also used for get_user_flow
class ListSongModel(BaseModel):
    data: list[SongModel] = Field(..., min_length=1)

class AlbumModel(BaseModel):
    SONGS: ListSongModel

class ListAlbumModel(BaseModel):
    data: list[AlbumModel] = Field(..., min_length=1)

class GetTracksByArtistModel(BaseModel):
    ALBUMS: ListAlbumModel


#Model for playlist create by service
class GoujonPlaylistModel(BaseModel):
    name: str
    public: bool
    selected_artists: list[ArtistModel] = Field(default_factory=list)
    track_list: list[SongModel] = Field(default_factory=list)


deezer_validation_models = { 
    ('get_artist_data','0'): GetTracksByArtistModel,
    ('get_artist_data','1'): GetRelatedArtistsModel,
    ('get_profile_data','artists'): GetUserFavoritesArtistsModel,
    ('get_profile_data','home'): GetLastPlaylistIdModel,
    ('get_user_flow',''): ListSongModel,
    ('get_playlist_songs',''): ListSongModel,
}

def data_validation(func):
    def wrapper(*args, **kwargs):
        logger.debug(f"Validating data for function {func.__name__} with arguments {args} and keyword arguments {kwargs}")
        result = func(*args, **kwargs)
        tab = ''
        if 'tab' in kwargs:
            tab = str(kwargs['tab'])
        model: BaseModel = deezer_validation_models[func.__name__,tab]
        model.model_validate(result)
        return result
    return wrapper

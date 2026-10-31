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


# Models to get all playlists
class PlaylistModel(BaseModel):
    PARENT_USER_ID: str
    PLAYLIST_ID: str
    TITLE: str
    NB_SONG: int
    STATUS: int
    PLAYLIST_PICTURE: str | None = None

class ListPlaylistModel(BaseModel):
    data: list[PlaylistModel] = Field(..., min_length=1)

class TabPlaylistModel(BaseModel):
    playlists: ListPlaylistModel

class GetPlaylistsModel(BaseModel):
    TAB: TabPlaylistModel


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


#Models to get playlist songs information
class PlaylistDataDetailsModel(BaseModel):
    TITLE: str
    STATUS: int

class PlaylistDataModel(BaseModel):
    DATA: PlaylistDataDetailsModel
    SONGS: ListSongModel


#Model for playlist create by service
class GoujonPlaylistModel(BaseModel):
    id: str | None = None
    name: str
    public: bool
    selected_artists: list[ArtistModel] = Field(default_factory=list)
    track_list: list[SongModel] = Field(default_factory=list)


deezer_validation_models = { 
    ('get_artist_data','0'): GetTracksByArtistModel,
    ('get_artist_data','1'): GetRelatedArtistsModel,
    ('get_profile_data','artists'): GetUserFavoritesArtistsModel,
    ('get_profile_data','playlists'): GetPlaylistsModel,
    ('get_user_flow',''): ListSongModel,
    ('get_playlist_songs',''): ListSongModel,
    ('get_playlist_infos',''): PlaylistDataModel
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

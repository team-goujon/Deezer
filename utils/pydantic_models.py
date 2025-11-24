from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Models for artists data (used for favorite and related artists)
class ArtistModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    ART_ID: str
    ART_NAME: str
    ART_PICTURE: str

class ListArtistsModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    data: list[ArtistModel] = Field(min_length=1)


# Model to get related artists information
class GetRelatedArtistsModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    RELATED_ARTISTS: ListArtistsModel


# Models to get favorite artists
class TabArtistsModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    artists: ListArtistsModel

class GetUserFavoritesArtistsModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    TAB: TabArtistsModel


# Models to get playlist id
class PlaylistModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    PLAYLIST_ID: str

class ListPlaylistModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    data: list[PlaylistModel] = Field(min_length=1)

class AllPlaylistModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    playlists: ListPlaylistModel

class TabHomeModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    home: AllPlaylistModel

class GetLastPlaylistIdModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    TAB: TabHomeModel


# Models to get album songs information
class SongModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    SNG_ID: str
    SNG_TITLE: str
    ART_ID: str
    DURATION: str

class ListSongModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    data: list[SongModel] = Field(min_length=1)

class AlbumModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    SONGS: ListSongModel

class ListAlbumModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    data: list[AlbumModel] = Field(min_length=1)

class GetTracksByArtistModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    ALBUMS: ListAlbumModel


model_dict = { 
    ('get_artist_data','0'): GetTracksByArtistModel,
    ('get_artist_data','1'): GetRelatedArtistsModel,
    ('get_profile_data','artists'): GetUserFavoritesArtistsModel,
    ('get_profile_data','home'): GetLastPlaylistIdModel
}

def deezer_data_validation(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        model: BaseModel = model_dict[func.__name__,str(kwargs['tab'])]
        model.model_validate(result)
        return result
    return wrapper

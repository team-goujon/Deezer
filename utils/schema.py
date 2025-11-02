from jsonschema import validate, ValidationError

related_artists_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "definitions": {
        "artist": {
            "type": "object",
            "properties": {
                'ART_ID': {'type': 'string'},
                'ART_NAME': {'type': 'string'},
                'ART_PICTURE': {'type': 'string'}
            },
            "required": ['ART_ID', 'ART_NAME', 'ART_PICTURE'],
            "additionalProperties": True
        }
    },
    "properties": {
        "RELATED_ARTISTS": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/artist"},
                    "minItems": 1
                }
            },
            "required": ["data"],
            "additionalProperties": True
        }
    },
    "required": ["RELATED_ARTISTS"],
    "additionalProperties": True
}

album_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "definitions": {
        "song": {
            "type": "object", 
            "properties": {
                'SNG_ID': {'type': 'string'},
                'SNG_TITLE': {'type': 'string'},
                'ART_ID': {'type': 'string'}
            },
            "required": ['SNG_ID', 'SNG_TITLE', 'ART_ID'],
            "additionalProperties": True
        },
        "data_song": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/song"},
                    "minItems": 1
                }
            },
            "required": ["data"],
            "additionalProperties": True
        },
        "album": {
            "type": "object",
            "properties": {
                'SONGS': {"$ref": "#/definitions/data_song"}
            },
            "required": ['SONGS'],
            "additionalProperties": True
        }
    },
    "properties": {
        "ALBUMS": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/album"},
                    "minItems": 1
                }
            },
            "required": ["data"],
            "additionalProperties": True
        }
    },
    "required": ["ALBUMS"],
    "additionalProperties": True
}

favorites_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "definitions": {
        "artist": {
            "type": "object",
            "properties": {
                'ART_ID': {'type': 'string'},
                'ART_NAME': {'type': 'string'},
                'ART_PICTURE': {'type': 'string'}
            },
            "required": ['ART_ID', 'ART_NAME', 'ART_PICTURE'],
            "additionalProperties": True
        },
        "data_artists": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/artist"},
                    "minItems": 1
                }
            },
            "required": ["data"],
            "additionalProperties": True
        },
    },
    "properties": {
        "TAB": {
            "type": "object",
            "properties": {
                "artists": {"$ref": "#/definitions/data_artists"},
            },
            "required": ["artists"],
            "additionalProperties": True
        }
    },
    "required": ["TAB"],
    "additionalProperties": True
}

playlist_id_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "definitions": {
        "id_playlist": {
            "type": "object",
            "properties": {
                'PLAYLIST_ID': {'type': 'string'},
            },
            "required": ['PLAYLIST_ID'],
            "additionalProperties": True
        },
        "data_playlists": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/id_playlist"},
                    "minItems": 1
                }
            },
            "required": ["data"],
            "additionalProperties": True
        },
        "playlists": {
            "type": "object",
            "properties": {
                "playlists": {"$ref": "#/definitions/data_playlists"},
            },
            "required": ["playlists"],
            "additionalProperties": True
        }
    },
    "properties": {
        "TAB": {
            "type": "object",
            "properties": {
                "home": {"$ref": "#/definitions/playlists"},
            },
            "required": ["home"],
            "additionalProperties": True
        }
    },
    "required": ["TAB"],
    "additionalProperties": True
}

def deezer_data_validation(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if func.__name__ == 'get_artist_data' and kwargs['tab'] == 0:
            validate(instance=result, schema=album_schema)
        if func.__name__ == 'get_artist_data' and kwargs['tab'] == 1:
            validate(instance=result, schema=related_artists_schema)
        if func.__name__ == 'get_profile_data' and kwargs['tab'] == 'artists':
            validate(instance=result, schema=favorites_schema)
        if func.__name__ == 'get_profile_data' and kwargs['tab'] == 'home':
            validate(instance=result, schema=playlist_id_schema)
        return result
    return wrapper


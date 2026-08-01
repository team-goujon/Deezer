# Le principe : trois familles de modèles
Aujourd'hui utils/models.py mélange les trois dans un seul paquet plat. Il faut les distinguer :

|Famille|Rôle|Qui la manipule|
|-------|----|---------------|
|Enveloppes (`TAB`, `DATA`, `SONGS`...)|Déballer le JSON Deezer. Existent uniquement pour parser.|api.py, et rien d'autre|
|Entités (`SongModel`, `ArtistModel`, `PlaylistSummaryModel`)|Les objets métier. Portent les règles de traduction.|service + front|
|Agrégat (`GoujonPlaylistModel`)|L'état de la session utilisateur.|webapp + service|

Et la règle par frontière :
* api → service : l'API renvoie un modèle, jamais un dict. C'est api.py qui sait à quoi ressemble Deezer.
* service → front : le service renvoie des entités, jamais des dicts fabriqués à la main. Jinja lit les attributs directement.
* entre deux requêtes : `model_dump_json()` dans la session, `model_validate_json()` au retour. Ça vous le faites déjà bien.

# Concrètement sur votre code

## 1. Les entités absorbent les bizarreries de Deezer
C'est là que les alias servent. Deezer appelle la photo `ART_PICTURE` ici et `ALB_PICTURE` là, et encode `public` en `STATUS == 0`. Ces deux traductions appartiennent au modèle.

Corollaire : **une entité ne porte pas le vocabulaire de Deezer**. Ses champs sont nommés dans les termes du domaine, et l'`AliasChoices` fait le pont vers les clés du JSON. C'est exactement ce que les alias permettent, donc s'en priver serait laisser fuiter la forme de l'API jusque dans les templates.

```python
from pydantic import BaseModel, ConfigDict, Field, AliasChoices

class SongModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str             = Field(validation_alias=AliasChoices('id', 'SNG_ID'))
    title: str          = Field(validation_alias=AliasChoices('title', 'SNG_TITLE'))
    duration: int       = Field(validation_alias=AliasChoices('duration', 'DURATION'))
    artist_id: str      = Field(validation_alias=AliasChoices('artist_id', 'ART_ID'))
    artist_name: str    = Field(validation_alias=AliasChoices('artist_name', 'ART_NAME'))
    picture: str | None = Field(default=None,
                                validation_alias=AliasChoices('picture', 'ART_PICTURE', 'ALB_PICTURE'))


class ArtistModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str             = Field(validation_alias=AliasChoices('id', 'ART_ID'))
    name: str           = Field(validation_alias=AliasChoices('name', 'ART_NAME'))
    picture: str | None = Field(default=None,
                                validation_alias=AliasChoices('picture', 'ART_PICTURE', 'ALB_PICTURE'))


class PlaylistSummaryModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str        = Field(validation_alias=AliasChoices('id', 'PLAYLIST_ID'))
    owner_id: str  = Field(validation_alias=AliasChoices('owner_id', 'PARENT_USER_ID'))
    name: str      = Field(validation_alias=AliasChoices('name', 'TITLE'))
    nb_song: int   = Field(validation_alias=AliasChoices('nb_song', 'NB_SONG'))
    status: int    = Field(validation_alias=AliasChoices('status', 'STATUS'))
    picture: str | None = Field(default=None, validation_alias=AliasChoices('picture', 'PLAYLIST_PICTURE'))

    @property
    def public(self) -> bool:
        return self.status == 0
```

Le `rename(columns={"ALB_PICTURE": "ART_PICTURE"})` de `load_playlist` et celui de `__get_flow_artists` disparaissent tous les deux, et `STATUS == 0` n'est plus écrit qu'une fois.

## 2. Les enveloppes savent produire l'agrégat

```python
class ListSongModel(BaseModel):
    data: list[SongModel]

class PlaylistPageModel(BaseModel):
    """Réponse de deezer.pagePlaylist"""
    DATA: PlaylistSummaryModel
    SONGS: ListSongModel

    def to_goujon_playlist(self) -> "GoujonPlaylistModel":
        return GoujonPlaylistModel(
            id=self.DATA.id,
            name=self.DATA.name,
            public=self.DATA.public,
            track_list=self.SONGS.data,
        )
```

Le SCREAMING_SNAKE des enveloppes n'est pas une convention qu'on choisit, c'est une contrainte : ces champs doivent matcher les clés du JSON Deezer, sinon le parsing échoue. Les entités, elles, n'ont aucune raison d'en porter puisque les `validation_alias` font la traduction.

D'où la règle de lecture : **un attribut en SCREAMING_SNAKE signifie qu'on est encore dans la forme Deezer, donc dans une enveloppe, donc dans `api.py`**. Dès qu'on est en minuscules, on est dans le domaine. Si tu croises `SNG_ID` dans le service ou dans un template, c'est le symptôme d'une entité qui n'a pas été traduite.

À vérifier sur le payload réel : je ne sais pas si `pagePlaylist.DATA` contient bien `PARENT_USER_ID` et `NB_SONG`. Si non, mets un défaut sur ces deux champs.

## 3. L'agrégat porte les règles qui dépendent de son état

```python
class GoujonPlaylistModel(BaseModel):
    id: str | None = None
    name: str
    public: bool
    selected_artists: list[ArtistModel] = Field(default_factory=list)
    track_list: list[SongModel] = Field(default_factory=list)

    @property
    def is_persisted(self) -> bool:
        return self.id is not None

    @property
    def unique_track_ids(self) -> list[str]:
        return list(dict.fromkeys(t.id for t in self.track_list))
```
`is_persisted` remplace le paramètre `editing_playlist` dans les trois méthodes du service. `unique_track_ids` remplace le `pd.DataFrame(...).drop_duplicates().to_list()` de `save_playlist_on_deezer_profile`.

## 4. api.py parse explicitement, et le décorateur disparaît

```python
@with_auth
def get_playlist_infos(self, auth: dict, playlist_id: int, nb: int = -1) -> PlaylistPageModel:
    body = {"playlist_id": str(playlist_id), "nb": nb}
    return PlaylistPageModel.model_validate(self.__get_api("deezer.pagePlaylist", body))
```

Le registre `deezer_validation_models[(func_name, tab)]` n'existe que parce qu'un décorateur générique ne peut pas savoir quel modèle appliquer. C'est un contournement qui vous coûte le type de retour. Deux lignes explicites par méthode valent mieux : tu récupères l'annotation, l'autocomplétion, et tu supprimes le couplage bizarre entre le nom de la méthode et la clé `tab`.

## 5. Le service devient une ligne

```python
def load_playlist(self, playlist_id: str) -> GoujonPlaylistModel:
    try:
        return self.api.get_playlist_infos(playlist_id).to_goujon_playlist()
    except ValidationError as e:
        logger.error(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
        raise DeezerServiceError("Failed to retrieve or validate playlist songs")


def get_all_playlists(self, user_id: str) -> list[PlaylistSummaryModel]:
    try:
        page = self.api.get_profile_data(tab='playlists')
        return [p for p in page.TAB.playlists.data if p.owner_id == user_id]
    except ValidationError as e:
        logger.error(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
        raise DeezerServiceError("Failed to retrieve or validate user's playlists")
```

Plus de DataFrame, plus de dicts anonymes, et le type de retour documente le contrat.

## 6. Le front reçoit les modèles, pas des dicts

Jinja accède aux attributs et appelle les properties. model_dump() avant render_template est inutile :

```python
return render_template('edit_playlist.html', playlist=playlist)
```
```html
<h2>{{ playlist.name }}</h2>
{% for track in playlist.track_list %}
  <td>{{ track.title }}</td>
  <td>{{ track.artist_name }}</td>
{% endfor %}
```

Au passage ça supprime le `playlist_title=playlist.name` passé séparément, et le template a accès à `playlist.is_persisted` pour choisir entre le bouton "Save" et le bouton "Replace All" au lieu d'avoir deux fichiers dupliqués.

# Les pièges qui vous attendent

`populate_by_name=True` est obligatoire sur tout modèle qui transite par la session. Dès qu'un champ a un `validation_alias`, `model_dump_json()` écrit le nom du champ mais `model_validate_json()` attend l'alias. Sans ce flag, le round-trip session casse. C'est le bug le plus probable si tu introduis les alias.

`min_length=1` n'a rien à faire dans une enveloppe. Une enveloppe valide la structure, pas une attente métier. Une playlist vide est un état légitime : si tu veux la refuser, fais-le dans le service avec un message clair, pas via une `ValidationError` transformée en erreur générique.

Ne modélise pas les corps de requête sortants. `{"playlist_id": ..., "songs": ...}` est écrit une fois et lu par personne. Ce qui manque côté écriture, ce n'est pas un modèle, c'est un retour : arrête de faire `pass` et remonte l'erreur.

`pandas` reste légitime, mais au milieu seulement. `__add_related_artists` fait du `groupby().value_counts()` et `__set_random_tracks_list` du `sample()` : c'est du vrai travail de DataFrame, garde-le. La règle est : modèles aux frontières, DataFrame au centre, une conversion à l'entrée et une à la sortie. Ce qu'il faut supprimer, ce sont les DataFrames construits juste pour renommer une colonne ou sélectionner des champs.

Tes tests vont se scinder en deux, et c'est mieux. Aujourd'hui `test_service.py` mocke l'API avec des dicts, donc chaque test valide implicitement le parsing. Avec des modèles en retour d'API, tu obtiens : des tests de parsing qui prennent un vrai payload Deezer capturé et vérifient qu'il se valide, et des tests de service qui construisent directement des `SongModel`. Les seconds ne cassent plus quand Deezer ajoute un champ.

Si `utils/models.py` grossit, le split naturel est `utils/models/deezer.py` (enveloppes) et `utils/models/domain.py` (entités + agrégat). L'import `from utils.models import ...` continue de marcher via `__init__.py`.
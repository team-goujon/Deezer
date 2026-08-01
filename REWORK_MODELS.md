# Rework : gestion des modèles Pydantic

Document de travail issu de la revue de la PR #47. Il décrit la cible et un chemin de
migration en cinq phases, chacune mergeable indépendamment.

## Le principe

L'application a trois couches : une couche API qui récupère du JSON Deezer, une couche
service qui applique la logique métier, une couche front qui affiche. Chaque couche
manipule une famille de modèles différente, et la frontière entre deux couches est un
`model_validate`.

| Famille | Rôle | Qui la manipule |
|---|---|---|
| **Enveloppes** (`TAB`, `DATA`, `SONGS`...) | Déballer le JSON Deezer. Existent uniquement pour parser. | `service/api.py`, et rien d'autre |
| **Entités** (`SongModel`, `ArtistModel`, `PlaylistSummaryModel`) | Les objets métier. Portent les règles de traduction. | service + front |
| **Agrégat** (`GoujonPlaylistModel`) | L'état de la session utilisateur. | webapp + service |

Règles par frontière :

- **api vers service** : l'API renvoie un modèle, jamais un dict. C'est `api.py` qui sait à
  quoi ressemble Deezer.
- **service vers front** : le service renvoie des entités, jamais des dicts fabriqués à la
  main. Jinja lit les attributs directement.
- **entre deux requêtes** : `model_dump_json()` dans la session, `model_validate_json()` au
  retour.

Le point de départ du problème actuel est dans `utils/models.py` : le décorateur
`data_validation` valide puis jette le modèle et renvoie le dict brut. Les modèles servent
donc de simple assertion de schéma, et pandas sert de couche de transformation là où
Pydantic ferait le travail.

---

## Phase 1 : découper `utils/models.py`

Aucun changement de comportement.

### `utils/models/domain.py`

Les objets que le service et le front manipulent.

```python
from pydantic import BaseModel, ConfigDict, Field, AliasChoices

_CONFIG = ConfigDict(populate_by_name=True)   # indispensable pour le round-trip session


class ArtistModel(BaseModel):
    model_config = _CONFIG

    id: str             = Field(validation_alias=AliasChoices('id', 'ART_ID'))
    name: str           = Field(validation_alias=AliasChoices('name', 'ART_NAME'))
    picture: str | None = Field(default=None,
                                validation_alias=AliasChoices('picture', 'ART_PICTURE', 'ALB_PICTURE'))


class SongModel(BaseModel):
    model_config = _CONFIG

    id: str             = Field(validation_alias=AliasChoices('id', 'SNG_ID'))
    title: str          = Field(validation_alias=AliasChoices('title', 'SNG_TITLE'))
    duration: int       = Field(validation_alias=AliasChoices('duration', 'DURATION'))
    artist_id: str      = Field(validation_alias=AliasChoices('artist_id', 'ART_ID'))
    artist_name: str    = Field(validation_alias=AliasChoices('artist_name', 'ART_NAME'))
    picture: str | None = Field(default=None,
                                validation_alias=AliasChoices('picture', 'ART_PICTURE', 'ALB_PICTURE'))

    @property
    def artist(self) -> ArtistModel:
        return ArtistModel(id=self.artist_id, name=self.artist_name, picture=self.picture)


class PlaylistSummaryModel(BaseModel):
    model_config = _CONFIG

    id: str             = Field(validation_alias=AliasChoices('id', 'PLAYLIST_ID'))
    owner_id: str       = Field(validation_alias=AliasChoices('owner_id', 'PARENT_USER_ID'))
    name: str           = Field(validation_alias=AliasChoices('name', 'TITLE'))
    nb_song: int        = Field(default=0, validation_alias=AliasChoices('nb_song', 'NB_SONG'))
    status: int         = Field(validation_alias=AliasChoices('status', 'STATUS'))
    picture: str | None = Field(default=None, validation_alias=AliasChoices('picture', 'PLAYLIST_PICTURE'))

    @property
    def public(self) -> bool:
        return self.status == 0

    def is_owned_by(self, user_id: str) -> bool:
        return self.owner_id == user_id


class GoujonPlaylistModel(BaseModel):
    model_config = _CONFIG

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

    def find_song(self, song_id: str) -> SongModel | None:
        return next((t for t in self.track_list if t.id == song_id), None)

    def song_ids_of_artist(self, artist_id: str) -> set[str]:
        return {t.id for t in self.track_list if t.artist_id == artist_id}

    def without_song(self, song_id: str) -> "GoujonPlaylistModel":
        return self.model_copy(deep=True, update={
            'track_list': [t for t in self.track_list if t.id != song_id]})

    def with_song_replaced(self, song_id: str, new_song: SongModel) -> "GoujonPlaylistModel":
        return self.model_copy(deep=True, update={
            'track_list': [new_song if t.id == song_id else t for t in self.track_list]})
```

Points clés :

- **Aucune entité ne porte le vocabulaire de Deezer.** Les champs sont nommés dans les
  termes du domaine et les `AliasChoices` font le pont vers les clés du JSON. C'est le but
  même de la couche entité : sans ça, la forme de l'API Deezer fuit jusque dans les
  templates. Le renommage est traité en phase 1b.
- Les alias absorbent les bizarreries de Deezer. Le `rename(columns={"ALB_PICTURE":
  "ART_PICTURE"})` de `load_playlist` et celui de `__get_flow_artists` disparaissent tous
  les deux.
- La règle `STATUS == 0` n'est plus écrite qu'une fois.
- `is_persisted` remplace le paramètre `editing_playlist` dans les trois méthodes du
  service.
- `find_song` permet de retrouver l'artiste d'une piste à partir du seul identifiant de
  chanson, donc le front n'a plus besoin de faire circuler l'identifiant d'artiste (voir
  phase 4).
- `without_song` et `with_song_replaced` renvoient une **nouvelle** instance au lieu de
  muter. C'est ce qui élimine la classe de bug sur laquelle les tests actuels sont tombés :
  plus d'aliasing possible entre la fixture et l'objet sous test.

### `utils/models/deezer.py`

Les enveloppes. Elles ne sortent jamais de `service/api.py`, et chacune sait produire du
domaine.

Leur SCREAMING_SNAKE n'est pas une convention qu'on choisit, c'est une contrainte : ces
champs doivent matcher les clés du JSON Deezer, sinon le parsing échoue. D'où la règle de
lecture : **un attribut en SCREAMING_SNAKE signifie qu'on est encore dans la forme Deezer,
donc dans une enveloppe, donc dans `api.py`.** Dès qu'on est en minuscules, on est dans le
domaine. Croiser `SNG_ID` dans le service ou dans un template est le symptôme d'une entité
qui n'a pas été traduite.

```python
from pydantic import BaseModel, Field
from utils.models.domain import ArtistModel, SongModel, PlaylistSummaryModel, GoujonPlaylistModel


class ListArtistsModel(BaseModel):
    data: list[ArtistModel] = Field(default_factory=list)

class ListSongModel(BaseModel):
    data: list[SongModel] = Field(default_factory=list)

class ListPlaylistModel(BaseModel):
    data: list[PlaylistSummaryModel] = Field(default_factory=list)


# deezer.pageProfile tab=artists
class FavoriteArtistsPage(BaseModel):
    class _Tab(BaseModel):
        artists: ListArtistsModel
    TAB: _Tab

    def artists(self) -> list[ArtistModel]:
        return self.TAB.artists.data


# deezer.pageProfile tab=playlists
class ProfilePlaylistsPage(BaseModel):
    class _Tab(BaseModel):
        playlists: ListPlaylistModel
    TAB: _Tab

    def playlists(self) -> list[PlaylistSummaryModel]:
        return self.TAB.playlists.data


# deezer.pageArtist tab=0
class ArtistTracksPage(BaseModel):
    class _Album(BaseModel):
        SONGS: ListSongModel
    class _Albums(BaseModel):
        data: list["ArtistTracksPage._Album"] = Field(default_factory=list)
    ALBUMS: _Albums

    def tracks(self) -> list[SongModel]:
        return [s for album in self.ALBUMS.data for s in album.SONGS.data]


# deezer.pageArtist tab=1
class RelatedArtistsPage(BaseModel):
    RELATED_ARTISTS: ListArtistsModel

    def artists(self) -> list[ArtistModel]:
        return self.RELATED_ARTISTS.data


# deezer.pagePlaylist
class PlaylistPage(BaseModel):
    DATA: PlaylistSummaryModel
    SONGS: ListSongModel

    def to_goujon_playlist(self) -> GoujonPlaylistModel:
        return GoujonPlaylistModel(
            id=self.DATA.id,
            name=self.DATA.name,
            public=self.DATA.public,
            track_list=self.SONGS.data,
        )
```

`utils/models/__init__.py` réexporte tout, donc les imports existants continuent de
marcher.

> À vérifier sur un payload réel : la présence de `PARENT_USER_ID` et `NB_SONG` dans
> `pagePlaylist.DATA`. Un défaut est posé sur `nb_song` par prudence, mais `owner_id` doit
> rester requis pour le contrôle de propriété.

### Pièges

- **`populate_by_name=True` est obligatoire** sur tout modèle qui transite par la session.
  Dès qu'un champ a un `validation_alias`, `model_dump_json()` écrit le nom du champ mais
  `model_validate_json()` attend l'alias. Sans ce flag, le round-trip session casse.
- **Pas de `min_length=1` dans une enveloppe.** Une enveloppe valide la *structure*, pas une
  attente métier. Une playlist vide est un état légitime : si on veut la refuser, on le fait
  dans le service avec un message clair, pas via une `ValidationError` transformée en erreur
  générique.

---

## Phase 1b : propager le renommage des entités

Étape dédiée, volontairement séparée de la phase 1 : le diff est un pur renommage,
mécanique et trivial à relire.

Le renommage est **atomique**. Dès que le champ s'appelle `id`, tout accès `t.SNG_ID`
casse, donc modèles, service, webapp, templates et tests bougent dans le même commit.

| Avant | Après |
|---|---|
| `SongModel.SNG_ID` | `SongModel.id` |
| `SongModel.SNG_TITLE` | `SongModel.title` |
| `SongModel.DURATION` | `SongModel.duration` |
| `SongModel.ART_ID` | `SongModel.artist_id` |
| `SongModel.ART_NAME` | `SongModel.artist_name` |
| `SongModel.ART_PICTURE` | `SongModel.picture` |
| `ArtistModel.ART_ID` | `ArtistModel.id` |
| `ArtistModel.ART_NAME` | `ArtistModel.name` |
| `ArtistModel.ART_PICTURE` | `ArtistModel.picture` |

Fichiers touchés :

- `service/__init__.py` : `add_data_to_playlist`, `set_artist_selection`, et toutes les
  méthodes playlist.
- `webapp.py` : `artist_selection` fait `a.ART_ID in selected_ids`, qui devient
  `a.id in selected_ids`.
- `templates/artist_selection.html` : `values['ART_NAME']`, `values['ART_PICTURE']` et la
  `value` du champ `artist_index`.
- `templates/save_playlist.html` et `templates/edit_playlist.html` : `values['SNG_TITLE']`,
  `values['ART_NAME']`, `values['ART_PICTURE']`.
- `tests/unit_tests/test_service.py` : les fixtures `SongModel(...)` et les helpers
  `make_mock_artist_data_*`.

> Les payloads Deezer bruts des mocks de test ne changent pas : `SNG_ID` figure dans les
> `AliasChoices`, donc ils se valident toujours. Ce sont les constructions directes de
> modèles et les lectures d'attributs qui changent.

**Les sessions déjà sérialisées restent lisibles.** Les anciens dumps contiennent `SNG_ID`
comme nom de champ, et `SNG_ID` fait partie des `AliasChoices`, donc
`model_validate_json()` les accepte sans migration. Aucun utilisateur ne perd sa playlist
en cours au déploiement.

Point de vigilance dans l'autre sens : après le renommage, `model_dump_json()` écrit `id`,
`title`... Un rollback vers la version précédente ne saurait plus relire ces sessions. Si
c'est un souci, vider `sessions/` fait partie du rollback.

---

## Phase 2 : une méthode d'API par forme de réponse

Le registre `deezer_validation_models[(func_name, tab)]` et le décorateur `data_validation`
disparaissent. Le vrai problème qu'ils cachaient : `get_artist_data(tab=0|1)` et
`get_profile_data(tab=...)` **changent de type de retour selon un argument**. On les scinde.

```python
@with_auth
def get_favorite_artists(self, auth: dict, nb: int = 100) -> FavoriteArtistsPage:
    body = {'user_id': auth.get("user_id"), 'tab': 'artists', 'total': nb}
    return FavoriteArtistsPage.model_validate(self.__get_api("deezer.pageProfile", body))

@with_auth
def get_profile_playlists(self, auth: dict, nb: int = -1) -> ProfilePlaylistsPage:
    body = {'user_id': auth.get("user_id"), 'tab': 'playlists', 'total': nb}
    return ProfilePlaylistsPage.model_validate(self.__get_api("deezer.pageProfile", body))

def get_artist_tracks(self, artist_id: str) -> ArtistTracksPage:
    body = {"art_id": artist_id, "lang": "fr", "tab": 0}
    return ArtistTracksPage.model_validate(self.__get_api("deezer.pageArtist", body))

def get_related_artists(self, artist_id: str) -> RelatedArtistsPage:
    body = {"art_id": artist_id, "lang": "fr", "tab": 1}
    return RelatedArtistsPage.model_validate(self.__get_api("deezer.pageArtist", body))

def get_playlist_infos(self, playlist_id: str, nb: int = -1) -> PlaylistPage:
    body = {"playlist_id": str(playlist_id), 'nb': nb}
    return PlaylistPage.model_validate(self.__get_api("deezer.pagePlaylist", body))
```

Effet de bord bienvenu : `__get_api` avale les exceptions non-Deezer et renvoie `None`.
Aujourd'hui ce `None` se propage jusqu'à un `TypeError` obscur. Avec le parse explicite,
`model_validate(None)` lève une `ValidationError` immédiatement, au bon endroit.

Côté écriture, les méthodes cessent de finir par `pass` :

```python
def create_playlist(self, name: str, description: str, public: bool) -> str:
    body = {"title": name, "description": description, "status": int(not public),
            "tags": "", "songs": [], "collaborative": False}
    results = self.__get_api("playlist.create", body)
    if results is None:
        raise DeezerAPIError("playlist.create returned no result")
    return str(results)
```

> À confirmer sur un appel réel, mais `playlist.create` renvoie normalement l'id de la
> playlist créée dans `results`. Si c'est le cas, `__get_last_playlist_id()` disparaît
> entièrement, avec sa race condition et son `total=-1` qui rapatrie toutes les playlists
> pour lire `data[0]`.

Il ne faut pas modéliser les corps de requête sortants : `{"playlist_id": ..., "songs": ...}`
est écrit une fois et lu par personne. Ce qui manque côté écriture, ce n'est pas un modèle,
c'est un retour.

---

## Phase 3 : le service, sans dict ni DataFrame sur les chemins playlist

```python
def get_all_playlists(self, user_id: str) -> list[PlaylistSummaryModel]:
    try:
        return [p for p in self.api.get_profile_playlists().playlists() if p.is_owned_by(user_id)]
    except ValidationError as e:
        logger.error(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
        raise DeezerServiceError("Failed to retrieve or validate user's playlists")


def load_playlist(self, playlist_id: str, user_id: str) -> GoujonPlaylistModel:
    try:
        page = self.api.get_playlist_infos(playlist_id)
    except ValidationError as e:
        logger.error(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
        raise DeezerServiceError("Failed to retrieve or validate playlist songs")
    if not page.DATA.is_owned_by(user_id):
        raise DeezerServiceError("Playlist not owned by the current user")
    return page.to_goujon_playlist()


def delete_song_from_playlist(self, playlist: GoujonPlaylistModel, song_id: str) -> GoujonPlaylistModel:
    try:
        if playlist.is_persisted:
            self.api.delete_songs_from_playlist(playlist.id, [[song_id, 0]])
        return playlist.without_song(song_id)
    except Exception as e:
        logger.error(f"Failed to delete song from playlist: {e}")
        raise DeezerServiceError("Failed to delete song from playlist")


def replace_song_in_playlist(self, playlist: GoujonPlaylistModel, song_id: str) -> GoujonPlaylistModel:
    song = playlist.find_song(song_id)
    if song is None:
        raise DeezerServiceError(f"Song {song_id} is not in this playlist")
    try:
        new_song = self.__pick_new_song(song.artist_id, playlist.song_ids_of_artist(song.artist_id))
        if new_song is None:
            logger.info(f"No alternative track for artist {song.artist_id}. Keeping the original song.")
            return playlist
        updated = playlist.with_song_replaced(song_id, new_song)
        if playlist.is_persisted:
            self.api.delete_songs_from_playlist(playlist.id, [[song_id, 0]])
            self.api.add_songs_to_playlist(playlist.id, [[new_song.id, 0]])
            self.api.update_song_order_in_playlist(playlist.id, updated.unique_track_ids)
        return updated
    except Exception as e:
        logger.error(f"Failed to replace song in playlist: {e}")
        raise DeezerServiceError("Failed to replace song in playlist")


def replace_all_songs(self, playlist: GoujonPlaylistModel) -> GoujonPlaylistModel:
    try:
        updated, cache, removed, added = playlist, {}, [], []
        for song in playlist.track_list:
            if song.artist_id not in cache:
                cache[song.artist_id] = self.__get_tracks_by_artist(song.artist_id)
            new_song = self.__pick_new_song(
                song.artist_id, updated.song_ids_of_artist(song.artist_id), cache[song.artist_id])
            if new_song is None:
                continue
            removed.append(song.id)
            added.append(new_song.id)
            updated = updated.with_song_replaced(song.id, new_song)
        if playlist.is_persisted and removed:
            self.api.delete_songs_from_playlist(playlist.id, [[s, 0] for s in removed])
            self.api.add_songs_to_playlist(playlist.id, [[s, 0] for s in added])
            self.api.update_song_order_in_playlist(playlist.id, updated.unique_track_ids)
        return updated
    except Exception as e:
        logger.error(f"Failed to replace all songs in playlist: {e}")
        raise DeezerServiceError("Failed to replace all songs in playlist")


def save_playlist_on_deezer_profile(self, playlist: GoujonPlaylistModel) -> GoujonPlaylistModel:
    playlist_id = self.api.create_playlist(
        name=playlist.name, description="GoujonPlaylist", public=playlist.public)
    self.api.add_songs_to_playlist(playlist_id, [[s, 0] for s in playlist.unique_track_ids])
    return playlist.model_copy(update={'id': playlist_id})


def __get_tracks_by_artist(self, artist_id: str) -> list[SongModel]:
    try:
        tracks = self.api.get_artist_tracks(artist_id).tracks()
    except ValidationError as e:
        logger.warning(f"{e.__class__.__name__}: {e.title} - {e.error_count()} error(s)")
        logger.warning(f"Failed to retrieve tracks for artist ID {artist_id}")
        return []
    return [t for t in tracks if t.artist_id == artist_id and t.duration > 80]


def __pick_new_song(self, artist_id: str, excluded_ids: set[str],
                    candidates: list[SongModel] | None = None) -> SongModel | None:
    candidates = self.__get_tracks_by_artist(artist_id) if candidates is None else candidates
    available = [t for t in candidates if t.id not in excluded_ids]
    return random.choice(available) if available else None
```

Bonus au passage :

- `save_playlist_on_deezer_profile` renvoie la playlist persistée, donc la session récupère
  un `id` et l'utilisateur peut continuer à éditer.
- Le `and removed` supprime l'appel API avec une liste vide.
- `__get_tracks_by_artist` n'a plus besoin du `astype(int)` puisque Pydantic coerce déjà
  `"200"` en `200`.
- Le contrôle de propriété dans `load_playlist` ferme le trou actuel : le POST sur
  `/playlists_to_edit` fait aujourd'hui confiance à `request.form.get('action')` pour l'id,
  et le filtre `PARENT_USER_ID == user_id` n'existe que dans la liste affichée.
- `replace_song_in_playlist` ne prend plus `artist_id` : il le déduit de la playlist en
  session via `find_song`. Aujourd'hui `artist_id` vient du client et part tel quel dans
  l'appel Deezer. Là, un `song_id` forgé ne correspond à rien et l'appel est rejeté avant
  toute requête réseau.
- Plus aucun attribut en SCREAMING_SNAKE dans le service : si `SNG_ID` réapparaît ici,
  c'est qu'une enveloppe a fuité hors de `api.py`.

---

## Phase 4 : le front reçoit des modèles, une route par action

Jinja accède aux attributs et appelle les properties. `model_dump()` avant
`render_template` est inutile.

### Supprimer l'encodage d'action dans `value`

Aujourd'hui l'action et ses paramètres sont concaténés dans une seule chaîne
(`replace_{ART_ID}_{SNG_ID}`) puis découpés au `split('_')`. Ça ne tient que sur des IDs
numériques : les fixtures de test actuelles (`art_1`, `song_1`) le casseraient.

Deux changements suppriment le problème à la racine plutôt que de choisir un meilleur
séparateur.

**1. L'identifiant d'artiste n'a pas besoin de circuler.** La playlist est en session et la
piste s'y trouve, donc `find_song(song_id).artist_id` donne l'artiste côté serveur. Un seul
identifiant à transmettre.

**2. `formaction` met cet identifiant dans l'URL.** Chaque bouton pointe vers sa propre
route, Flask fait le routage et le typage, et il ne reste plus rien à parser. Un
identifiant transmis n'est plus une chaîne à déchiffrer mais un paramètre de route.

> À noter : un `<button>` submit n'envoie que sa propre paire `name`/`value`. Des attributs
> custom ou `data-*` posés sur le bouton ne sont **pas** transmis au serveur. L'alternative
> sans `formaction` serait un `<form>` par ligne avec des inputs cachés, ce qui impose de
> supprimer le formulaire englobant, les formulaires imbriqués étant invalides.

### Les routes

```python
def _current_playlist() -> GoujonPlaylistModel:
    return GoujonPlaylistModel.model_validate_json(session['playlist'])


def _store(playlist: GoujonPlaylistModel) -> None:
    session['playlist'] = playlist.model_dump_json()


@app.route('/playlist', methods=['GET'])
@require_auth
def playlist_editor():
    return render_template('playlist_editor.html', playlist=_current_playlist())


@app.route('/playlist/song/<song_id>/replace', methods=['POST'])
@require_auth
def replace_song(song_id: str):
    _store(service.replace_song_in_playlist(_current_playlist(), song_id))
    return redirect(url_for('playlist_editor'))


@app.route('/playlist/song/<song_id>/delete', methods=['POST'])
@require_auth
def delete_song(song_id: str):
    _store(service.delete_song_from_playlist(_current_playlist(), song_id))
    return redirect(url_for('playlist_editor'))


@app.route('/playlist/replace_all', methods=['POST'])
@require_auth
def replace_all_songs():
    _store(service.replace_all_songs(_current_playlist()))
    return redirect(url_for('playlist_editor'))


@app.route('/playlist/save', methods=['POST'])
@require_auth
def save_playlist():
    _store(service.save_playlist_on_deezer_profile(_current_playlist()))
    return redirect(url_for('menu'))
```

Chaque route fait une seule chose et redirige vers la vue. C'est le motif
POST/Redirect/GET, qui corrige au passage un défaut actuel : aujourd'hui un rafraîchissement
après un « Replace » resoumet l'action.

Autre défaut corrigé : dans la version actuelle, les trois `if request.form.get('action',
'').startswith(...)` s'évaluent en séquence sur la même requête. Une route par action rend
l'exclusion mutuelle structurelle.

### Le template

`/save_playlist` et `/edit_playlist` partagent désormais la même vue, ce qui supprime la
duplication à 95% entre `save_playlist.html` et `edit_playlist.html`. Un seul
`templates/playlist_editor.html` :

```jinja
<form method="post" class="dz-card m-3 px-3 px-sm-5 py-4 w-100">
  <h2 class="fs-2 mb-3">{{ playlist.name }}</h2>
  <h3 class="fs-4 fw-normal mb-3">Playlist content
    <span class="badge bg-secondary fs-6 fw-normal">
      {{ playlist.track_list|length }} track{{ 's' if playlist.track_list|length > 1 }}
    </span>
  </h3>

  {% for track in playlist.track_list %}
    <tr>
      <td><img src="https://cdn-images.dzcdn.net/images/artist/{{ track.picture }}/56x56-000000-80-0-0.jpg" ...></td>
      <td>{{ track.title }}</td>
      <td>{{ track.artist_name }}</td>
      <td>
        <button type="submit" formaction="{{ url_for('replace_song', song_id=track.id) }}"
                class="btn btn-sm btn-outline-info"><i class="bi bi-shuffle me-2"></i>Replace</button>
      </td>
      <td>
        <button type="submit" formaction="{{ url_for('delete_song', song_id=track.id) }}"
                class="btn btn-sm btn-outline-danger"><i class="bi bi-trash me-2"></i>Delete</button>
      </td>
    </tr>
  {% endfor %}

  {% if playlist.is_persisted %}
    <button id="replace-all-btn" type="submit" formaction="{{ url_for('replace_all_songs') }}"
            class="btn btn-primary"><i class="bi bi-shuffle me-1"></i>Replace All Songs</button>
  {% else %}
    <button type="submit" formaction="{{ url_for('save_playlist') }}"
            class="btn btn-primary"><i class="bi bi-cloud-upload me-1"></i>Save on Deezer</button>
  {% endif %}
</form>
```

Le `<form>` englobant ne sert plus qu'à regrouper les boutons : chacun porte son
`formaction`, donc l'action propre du formulaire n'est jamais utilisée. Il n'y a aucun champ
de saisie dans cette vue, donc pas de soumission implicite possible par la touche Entrée.

Plus aucun `model_dump()` avant `render_template`, plus de `playlist_title` passé à côté, et
le template lit `is_persisted` au lieu qu'un humain doive se souvenir quel fichier sert quel
flux. Les templates ne contiennent plus une seule clé Deezer : `track.title` au lieu de
`values['SNG_TITLE']`.

De même pour la liste des playlists, où `formaction` remplace l'id encodé dans `value` :

```jinja
{% for playlist in playlists %}
  <td><img src="https://cdn-images.dzcdn.net/images/cover/{{ playlist.picture }}/56x56-000000-80-0-0.jpg" ...></td>
  <td>{{ playlist.name }}</td>
  <td>{{ playlist.nb_song }} songs</td>
  <td>
    <button type="submit" formaction="{{ url_for('load_playlist_for_edit', playlist_id=playlist.id) }}"
            class="btn btn-sm btn-outline-info"><i class="bi bi-pencil me-2"></i>Edit</button>
  </td>
{% endfor %}
```

```python
@app.route('/playlist/<playlist_id>/edit', methods=['POST'])
@require_auth
def load_playlist_for_edit(playlist_id: str):
    user_id = str(session['auth'].get('user_id'))
    _store(service.load_playlist(playlist_id, user_id))
    return redirect(url_for('playlist_editor'))
```

---

## Phase 5 (optionnel) : sortir pandas du service

Après la phase 3, il ne reste que deux usages réels de pandas : le `sample(n=...)` sur les
favoris et le comptage d'occurrences dans `__add_related_artists`. `random.sample` et
`collections.Counter` les couvrent en trois lignes chacun, et `add_data_to_playlist` cesse
de faire des `pd.concat` sur des DataFrames aux colonnes hétérogènes (aujourd'hui la colonne
`count` fuit dans le concat et n'est ignorée que parce que Pydantic ignore les champs en
trop).

Règle générale à conserver : modèles aux frontières, DataFrame au centre si le calcul est
réellement de nature tabulaire, une conversion à l'entrée et une à la sortie. Ce qu'il faut
supprimer, ce sont les DataFrames construits juste pour renommer une colonne ou sélectionner
des champs.

---

## Impact sur les tests

Le rework scinde naturellement `test_service.py` en deux, et c'est le principal gain de
maintenabilité :

- **`tests/unit_tests/test_models.py`** : des payloads Deezer réels capturés dans
  `tests/fixtures/*.json`, parsés contre les enveloppes. C'est là qu'on détecte un
  changement d'API Deezer.
- **`tests/unit_tests/test_service.py`** : l'API mockée renvoie des instances de modèles.
  Ces tests ne cassent plus quand Deezer ajoute un champ, et
  `make_mock_artist_data_songs_for_replace` (qui fabrique aujourd'hui la structure
  `ALBUMS.data[].SONGS.data[]` à la main) devient une simple liste de `SongModel`.

Le `model_copy(deep=True)` devient inutile dans les tests : comme les méthodes du modèle
renvoient de nouvelles instances, les fixtures ne peuvent plus être mutées par un test.

Il faut aussi une fixture `playlist_being_edited` avec un `id` renseigné. Aujourd'hui
`assert_called_once_with(playlist.id, ...)` vérifie qu'on appelle l'API avec `None`, ce qui
ne teste rien.

---

## Ordre de merge suggéré

1. Correctifs ciblés dans la PR #47 (voir la revue).
2. Phase 1 : découpage des modèles, sans changement fonctionnel.
3. Phase 1b : renommage des entités, dans son propre commit pour un diff purement mécanique.
4. Phase 2.
5. Phase 3.
6. Phase 4.
7. Phase 5 si on veut aller au bout.

Les phases 1, 1b et 2 peuvent tenir dans une même PR « plomberie modèles » tant que le
renommage reste isolé dans son commit.

Chaque phase reste petite et la suite de tests d'intégration existante sert de garde-fou.

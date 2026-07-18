from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from datetime import timedelta
from service import DeezerService
from utils.models import GoujonPlaylistModel, ArtistModel
from service.auth import is_auth, authenticate, require_auth
from version import VERSION, RELEASE_DATE
import logging
import redis
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

load_dotenv()  

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=60)
app.config['SESSION_USE_SIGNER'] = True     
app.config['SESSION_REDIS'] = redis.from_url(os.getenv('REDIS_URL'))
app.config.from_object(__name__)
Session(app)
service = DeezerService()

@app.context_processor
def inject_app_metadata():
    return {'app_version': VERSION, 'app_date': RELEASE_DATE}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        arl = request.form.get('arl', '').strip()
        sid = request.form.get('sid', '').strip()
        
        if not arl or not sid:
            return render_template('login.html', error='Both arl and sid cookies are required')
        
        auth_data = authenticate(arl, sid)
        
        if not auth_data:
            return render_template('login.html', error='Invalid cookies. Please check your values and try again.')
        
        session['auth'] = auth_data
        logger.info(f"User authenticated successfully")
        return redirect(url_for('menu'))
    
    if is_auth(session):
        return redirect(url_for('menu'))
    return render_template('login.html')

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def menu():
    return render_template('menu.html')

@app.route('/playlist_parameters', methods=['GET', 'POST'])
@require_auth
def playlist_parameters():
    if request.method == 'POST':
        name = request.form.get('playlist_name', type=str)
        public = request.form.get('public_playlist') == 'on'
        session['playlist'] = GoujonPlaylistModel(name=name, public=public).model_dump_json()
        selection_mode = request.form['mode_selection']
        include_relative = request.form.get('related_artists') == 'on'
        playlist_options = {
            'mode': selection_mode,
            'include_relative': include_relative,
            'number_random_artists': request.form.get('artists_number', type=int, default=int(service.config.get("random_artists_number"))),
            'number_tracks_by_artist': request.form.get('songs_number', type=int, default=int(service.config.get("tracks_by_artist_number")))
        }
        session['playlist_options'] = playlist_options
        if selection_mode == 'Favorites':
            playlist = GoujonPlaylistModel.model_validate_json(session['playlist'])
            session['playlist'] = service.add_data_to_playlist(playlist, playlist_options).model_dump_json()
            return redirect(url_for('save_playlist'))
        if selection_mode == 'Flow' or selection_mode == 'Manual':
            session['artist_to_display'] = [a.model_dump() for a in service.set_artist_selection(selection_mode)]
            return redirect(url_for('artist_selection'))
    return render_template('playlist_parameters.html')

@app.route('/save_playlist', methods=['GET', 'POST'])
@require_auth
def save_playlist():
    playlist = GoujonPlaylistModel.model_validate_json(session['playlist'])
    if request.method == 'POST':
        if request.form.get('action', '') == 'save':
            service.save_playlist_on_deezer_profile(playlist)
            return redirect(url_for('menu'))
        if request.form.get('action', '').startswith('replace_'):
            _, artist_id, song_id = request.form.get('action').split('_')
            session['playlist'] = service.replace_song_in_playlist(playlist, artist_id, song_id).model_dump_json()
        if request.form.get('action', '').startswith('delete_'):
            _, song_id = request.form.get('action').split('_')
            session['playlist'] = service.delete_song_from_playlist(playlist, song_id).model_dump_json()
    track_list_to_render = [t.model_dump() for t in playlist.track_list]
    return render_template('save_playlist.html', playlist_title=playlist.name, tracks=track_list_to_render)

@app.route('/artist_selection', methods=['GET', 'POST'])
@require_auth
def artist_selection():
    if request.method == 'POST':
        selected_ids = request.form.getlist('artist_index')
        playlist = GoujonPlaylistModel.model_validate_json(session['playlist'])
        artists_to_display = [ArtistModel.model_validate(a) for a in session['artist_to_display']]
        playlist.selected_artists = [a for a in artists_to_display if a.ART_ID in selected_ids]
        session['playlist'] = service.add_data_to_playlist(playlist, session['playlist_options']).model_dump_json()
        return redirect(url_for('save_playlist'))
    return render_template('artist_selection.html', artists=session['artist_to_display'], mode=session['playlist_options']['mode'])

@app.route('/playlists_to_edit', methods=['GET', 'POST'])
@require_auth
def playlists_to_edit():
    if request.method == 'POST':
        id_to_edit = request.form.get('action')
        session['playlist'] = service.load_playlist(id_to_edit).model_dump_json()
        return redirect(url_for('edit_playlist'))
    user_id = str(session['auth'].get('user_id'))
    playlists = service.get_all_playlists(user_id)
    return render_template('playlists_to_edit.html', playlists=playlists)

@app.route('/edit_playlist', methods=['GET', 'POST'])
@require_auth
def edit_playlist():
    playlist = GoujonPlaylistModel.model_validate_json(session['playlist'])
    if request.method == 'POST':
        if request.form.get('action', '') == 'all_songs_replace':
            session['playlist'] =  service.replace_all_songs(playlist).model_dump_json()
        if request.form.get('action', '').startswith('replace_'):
            _, artist_id, song_id = request.form.get('action').split('_')
            session['playlist'] = service.replace_song_in_playlist(playlist, artist_id, song_id, editing_playlist=True).model_dump_json()
        if request.form.get('action', '').startswith('delete_'):
            _, song_id = request.form.get('action').split('_')
            session['playlist'] = service.delete_song_from_playlist(playlist, song_id, editing_playlist=True).model_dump_json()
    track_list_to_render = [t.model_dump() for t in playlist.track_list]
    return render_template('edit_playlist.html', playlist_title=playlist.name, tracks=track_list_to_render)

@app.route('/cancel', methods=['GET'])
def cancel():
    session.pop('form_data', None)
    session.pop('artists_list', None)
    session.pop('artists_to_display', None)
    session.pop('track_list', None)
    return redirect(url_for('menu'))

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_message=error)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
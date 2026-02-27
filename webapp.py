from flask import Flask, render_template, request, redirect, url_for, make_response, session
from flask_session import Session
from cachelib.file import FileSystemCache
from service import DeezerService
from utils.models import GoujonPlaylistModel
from service.auth import is_auth, authenticate, require_auth
import pandas as pd
import logging
logger = logging.getLogger(__name__)

app = Flask(__name__)
SESSION_TYPE = 'cachelib'
SESSION_SERIALIZATION_FORMAT = 'json'
SESSION_CACHELIB = FileSystemCache(threshold=500, cache_dir="./sessions")
app.config.from_object(__name__)
Session(app)
service = DeezerService()

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
@require_auth
def menu():
    if request.method == 'POST':
        playlist_to_create = GoujonPlaylistModel(name="", public=False, selected_artists=pd.DataFrame([]), track_list=pd.DataFrame([]))
        playlist_to_create.name = request.form.get('playlist_name', type=str)
        playlist_to_create.public = request.form.get('public_playlist') == 'on'
        session['playlist_to_create'] = playlist_to_create
        selection_mode = request.form['mode_selection']
        include_relative = request.form.get('related_artists') == 'on'
        playlist_options = {
            'mode': selection_mode,
            'include_relative': include_relative,
            'number_random_artists': request.form.get('artists_number', type=int, default=service.config.get("random_artists_number")),
            'number_tracks_by_artist': request.form.get('songs_number', type=int, default=service.config.get("tracks_by_artist_number"))
        }
        session['playlist_options'] = playlist_options
        if selection_mode == 'Favorites':
            session['playlist_to_create'] = service.create_playlist(playlist_to_create, playlist_options)
            return redirect(url_for('playlist_to_create'))
        if selection_mode == 'Flow' or selection_mode == 'Manual':
            session['artist_to_display'] = service.set_artist_selection(selection_mode)
            return redirect(url_for('artist_selection'))
        
    return render_template('menu.html')

@app.route('/playlist_to_create', methods=['GET', 'POST'])
@require_auth
def playlist_to_create():
    playlist_to_create: GoujonPlaylistModel = session['playlist_to_create']
    if request.method == 'POST':
        service.save_playlist_on_deezer_profile(playlist_to_create)
        return redirect(url_for('menu'))
    track_list_to_render = playlist_to_create.track_list[['SNG_TITLE', 'ART_NAME', 'ART_PICTURE']].to_dict(orient='records')
    return render_template('playlist_to_create.html', tracks=track_list_to_render)

@app.route('/artist_selection', methods=['GET', 'POST'])
@require_auth
def artist_selection():
    artist_to_display = session['artist_to_display']
    playlist_to_create: GoujonPlaylistModel = session['playlist_to_create']
    if request.method == 'POST':
        selected_ids = request.form.getlist('artist_index')
        playlist_to_create.selected_artists = artist_to_display[artist_to_display['ART_ID'].isin(selected_ids)]
        session['playlist_to_create'] = service.create_playlist(playlist_to_create, session['playlist_options'])
        return redirect(url_for('playlist_to_create'))
    artist_to_be_rendered = artist_to_display.to_dict(orient='records')
    return render_template('artist_selection.html', artists=artist_to_be_rendered, mode=session['playlist_options']['mode'])

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
    app.run(debug=True)
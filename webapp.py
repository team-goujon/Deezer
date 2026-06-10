from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from datetime import timedelta
from service import DeezerService
from utils.models import GoujonPlaylistModel
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
app.config['SESSION_SERIALIZATION_FORMAT'] = 'pickle'          
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
@require_auth
def menu():
    if request.method == 'POST':
        name = request.form.get('playlist_name', type=str)
        public = request.form.get('public_playlist') == 'on'
        session['playlist_to_create'] = GoujonPlaylistModel(name=name, public=public)
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
            session['playlist_to_create'] = service.add_data_to_playlist(session['playlist_to_create'], playlist_options)
            return redirect(url_for('playlist_to_create'))
        if selection_mode == 'Flow' or selection_mode == 'Manual':
            session['artist_to_display'] = service.set_artist_selection(selection_mode)
            return redirect(url_for('artist_selection'))
        
    return render_template('menu.html')

@app.route('/playlist_to_create', methods=['GET', 'POST'])
@require_auth
def playlist_to_create():
    playlist_to_create = session['playlist_to_create']
    if request.method == 'POST':
        service.save_playlist_on_deezer_profile(playlist_to_create)
        return redirect(url_for('menu'))
    track_list_to_render = [t.model_dump(include={'SNG_TITLE', 'ART_NAME', 'ART_PICTURE'}) for t in playlist_to_create.track_list]
    return render_template('playlist_to_create.html', tracks=track_list_to_render)

@app.route('/artist_selection', methods=['GET', 'POST'])
@require_auth
def artist_selection():
    if request.method == 'POST':
        selected_ids = request.form.getlist('artist_index')
        session['playlist_to_create'].selected_artists = [a for a in session['artist_to_display'] if a.ART_ID in selected_ids]
        session['playlist_to_create'] = service.add_data_to_playlist(session['playlist_to_create'], session['playlist_options'])
        return redirect(url_for('playlist_to_create'))
    artist_to_be_rendered = [a.model_dump() for a in session['artist_to_display']]
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
    app.run(host="0.0.0.0", port=5000, debug=True)
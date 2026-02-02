from flask import Flask, render_template, request, redirect, url_for, make_response, session
from flask_session import Session
from cachelib.file import FileSystemCache
from service import DeezerService
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
        session['auth'] = authenticate()
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
        session['form_data'] = request.form.to_dict()
        selection_mode = session['form_data']['mode_selection']
        include_relative = session['form_data'].get('related_artists', 'off') == 'on'
        session['artists_list'] = service.set_artist_selection(mode=selection_mode, include_relative=include_relative).to_dict(orient='records')
        if selection_mode == 'Favorites':
            session['track_list'] = service.create_playlist(session['artists_list']).to_dict(orient='records')
            return redirect(url_for('playlist_to_create'))
        if selection_mode in ['Flow', 'Manual']:
            return redirect(url_for('artist_selection'))
    return render_template('menu.html')

@app.route('/playlist_to_create', methods=['GET', 'POST'])
@require_auth
def playlist_to_create():
    track_list = session['track_list']
    if request.method == 'POST':
        playlist_name = session['form_data'].get('playlist_name')
        is_playlist_public = session['form_data'].get('public_playlist') == 'on'
        service.save_playlist_on_deezer_profile(track_list, playlist_name, is_playlist_public)
        return redirect(url_for('menu'))
    return render_template('playlist_to_create.html', tracks=track_list)

@app.route('/artist_selection', methods=['GET', 'POST'])
@require_auth
def artist_selection():
    logger.debug(session)
    artist_to_display = session['artists_list']
    if request.method == 'POST':
        selected_ids = request.form.getlist('artist_index')
        selected_artists = [item for item in artist_to_display if item['ART_ID'] in selected_ids]
        session['track_list'] = service.create_playlist(selected_artists).to_dict(orient='records')
        return redirect(url_for('playlist_to_create'))
    return render_template('artist_selection.html', artists=artist_to_display, mode=session['form_data']['mode_selection'])

if __name__ == '__main__':
    app.run(debug=True)
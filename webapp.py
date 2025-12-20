from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from service import DeezerService
from utils.models import GoujonPlaylistModel
import pandas as pd
import logging
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = '6793792e96ccff55287960d6725b998562b93f7521caa5721c5d8f45454e63a6'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_THRESHOLD'] = 3
Session(app)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        session['service'] = DeezerService()
        return redirect(url_for('menu'))
    return render_template('home.html')


@app.route('/menu', methods=['GET', 'POST'])
def menu():
    service: DeezerService = session['service']
    if request.method == 'POST':
        playlist_to_create = GoujonPlaylistModel(name="", public=False, selected_artists=pd.DataFrame([]), track_list=pd.DataFrame([]))
        playlist_to_create.name = request.form.get('playlist_name', type=str)
        playlist_to_create.public = request.form.get('public_playlist') == 'on'
        session['playlist_to_create'] = playlist_to_create
        session['number_random_artists'] = request.form.get('artists_number', type=int, default=service.config.get("random_artists_number"))
        session['number_tracks_by_artist'] = request.form.get('songs_number', type=int, default=service.config.get("tracks_by_artist_number"))
        mode = request.form['mode_selection']
        session['mode'] = mode
        session['include_relative'] = request.form.get('related_artists') == 'on' and mode != 'Flow'
        if mode == 'Favorites':
            session['playlist_to_create'] = service.create_playlist(session)
            return redirect(url_for('playlist_to_create'))
        if mode == 'Flow' or mode == 'Manual':
            session['artist_to_display'] = service.set_artist_selection(mode).to_dict()
            return redirect(url_for('artist_selection'))
    return render_template('menu.html')

@app.route('/playlist_to_create', methods=['GET', 'POST'])
def playlist_to_create():
    service: DeezerService = session['service']
    playlist_to_create: GoujonPlaylistModel = session['playlist_to_create']
    if request.method == 'POST':
        service.save_playlist_on_deezer_profile(playlist_to_create)
        return redirect(url_for('home'))
    track_list_to_render = playlist_to_create.track_list[['SNG_TITLE', 'ART_NAME']].to_dict(orient='records')
    return render_template('playlist_to_create.html', tracks=track_list_to_render)

@app.route('/artist_selection', methods=['GET', 'POST'])
def artist_selection():
    service: DeezerService = session['service']
    artist_to_display = pd.DataFrame(session['artist_to_display'])
    playlist_to_create: GoujonPlaylistModel = session['playlist_to_create']
    if request.method == 'POST':
        selected_ids = request.form.getlist('artist_index')
        playlist_to_create.selected_artists = artist_to_display[artist_to_display['ART_ID'].isin(selected_ids)]
        session['playlist_to_create'] = playlist_to_create
        session['playlist_to_create'] = service.create_playlist(session)
        return redirect(url_for('playlist_to_create'))
    artist_to_be_rendered = artist_to_display.to_dict(orient='records')
    return render_template('artist_selection.html', artists=artist_to_be_rendered, mode=session['mode'])

if __name__ == '__main__':
    app.run(debug=True)
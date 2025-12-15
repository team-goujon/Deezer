from flask import Flask, render_template, request, redirect, url_for
from service import DeezerService
import pandas as pd
import logging
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        global service
        service = DeezerService()
        return redirect(url_for('menu'))
    return render_template('home.html')


@app.route('/menu', methods=['GET', 'POST'])
def menu():
    if request.method == 'POST':
        service.playlist_to_create.name = request.form.get('playlist_name', type=str)
        service.playlist_to_create.public = request.form.get('public_playlist') == 'on'
        service.number_random_artists = request.form.get('artists_number', type=int)
        service.number_tracks_by_artist = request.form.get('songs_number', type=int)
        service.mode = request.form['mode_selection']
        service.include_relative = request.form.get('related_artists') == 'on' and service.mode != 'Flow'
        if service.mode == 'Favorites':
            service.create_playlist()
            return redirect(url_for('playlist_to_create'))
        if service.mode == 'Flow' or service.mode == 'Manual':
            service.artist_to_display = service.set_artist_selection()
            return redirect(url_for('artist_selection'))
    return render_template('menu.html')

@app.route('/playlist_to_create', methods=['GET', 'POST'])
def playlist_to_create():
    track_list = service.playlist_to_create.track_list
    if request.method == 'POST':
        service.save_playlist_on_deezer_profile(track_list)
        return redirect(url_for('home'))
    track_list_to_render = service.playlist_to_create.track_list[['SNG_TITLE', 'ART_NAME']].to_dict(orient='records')
    return render_template('playlist_to_create.html', tracks=track_list_to_render)

@app.route('/artist_selection', methods=['GET', 'POST'])
def artist_selection():
    artist_to_display = service.artist_to_display
    if request.method == 'POST':
        selected_ids = request.form.getlist('artist_index')
        service.playlist_to_create.selected_artists = artist_to_display[artist_to_display['ART_ID'].isin(selected_ids)]
        service.create_playlist()
        return redirect(url_for('playlist_to_create'))
    artist_to_be_rendered = artist_to_display.to_dict(orient='records')
    return render_template('artist_selection.html', artists=artist_to_be_rendered, mode=service.mode)

if __name__ == '__main__':
    app.run(debug=True)
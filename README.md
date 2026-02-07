# Deezer

## Configuration
Do it once:
```
cp config.ini.sample config.ini
```

## Usage
```
pip install -r requirements.txt
python webapp.py
```

## Plan
### V1
- class managing auth (call via browser to authenticate on deezer ?) and primary functions (create playlist, get songs, add songs, etc.)
- class that provides secondary function (that uses primary functions)
- script that create the playlist

### V1.1
- manage error
- add logger
- automate cookies collection

### V2
- user interface
- unit tests + e2e tests?
- use docker locally

### V3
- list the artists used for the playlist, and enables user to edit it before creation
- enables user to edit list of songs in the playlist before creation
- manages artist and song preferences (ban artist and/or songs)
- load previous playlist created for editing

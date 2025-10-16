from service import DeezerService

def main():
    newServ = DeezerService('cookies.txt')
    playlist_name = input('Entrez le nom de la playlist: ')
    public = False
    if input('public playlist ? y/n ') == "y":
        public = True
    random = True
    relative = False
    if input('Artists manual selection ? y/n ') == "y":
        random = False
        if input('Include relatives ? y/n ') == "y":
            relative = True
    newServ.create_playlist(playlist_name, random, public, relative)
    pass

if __name__ == '__main__':
    main()
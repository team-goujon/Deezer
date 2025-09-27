import requests
import json
import pandas as pd


def recover_track_id_list(artist: str, artist_id: int):
    url = "https://api.deezer.com/search"
    payload = ""
    search_index = 0
    next_search = True
    track_list = pd.DataFrame([])

    while next_search:
        querystring = {"q":f"artist:\"{artist}\"strict=on","index": search_index}
        response = requests.request("GET", url, data=payload, params=querystring).text
        res = json.loads(response)
        if 'next' not in res.keys():
            next_search = False
        df = pd.DataFrame(res['data'])
        if track_list.empty:
            track_list = df
        else:
            track_list = pd.concat([track_list,df],ignore_index=True)
        search_index+=25

    track_list = track_list[track_list['readable']==True]
    track_list['artist_id'] = track_list['artist'].apply(lambda x: x['id'])
    track_list = track_list[track_list['artist_id']==artist_id]

    # print(track_list.dtypes)
    # print(track_list[['id','title','artist','album']])

    return track_list

if __name__ == '__main__':
    print(recover_track_id_list('chinese man',58801))

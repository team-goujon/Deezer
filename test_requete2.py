import requests
import json
import pandas as pd


payload = ""
search_index = 0
artist_id = 58801

url = f"https://api.deezer.com/artist/{artist_id}"
response = requests.request("GET", url, data=payload).text
res = json.loads(response)
print(res)

url = f"https://api.deezer.com/artist/{artist_id}/top?limit=500"
response = requests.request("GET", url, data=payload).text
res = pd.DataFrame(json.loads(response)['data'])
print(res)



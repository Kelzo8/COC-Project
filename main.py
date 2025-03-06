import requests
import json

url = "https://allsportsapi2.p.rapidapi.com/api/rankings/fifa"
headers = {
    "x-rapidapi-key": "da62be9e24msheae0f8d203fa470p1f013ejsn172018fb6771",
    "x-rapidapi-host": "allsportsapi2.p.rapidapi.com"
}

response = requests.get(url, headers=headers)
data = response.json()
print("Response structure:")
print(json.dumps(data, indent=2))
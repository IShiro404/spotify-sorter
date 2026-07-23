"""Radio-Banger 2005-2017: Songs aus radio_bangers.json auf Spotify suchen
und als private Playlist anlegen. Nicht gefundene Songs werden gemeldet."""

import json
import os
import time
from pathlib import Path

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

ROOT = Path(__file__).parent
NAME = "Radio Banger 2005-2017 \U0001F4FB"

load_dotenv(ROOT / ".env")
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="playlist-read-private playlist-modify-private",
    cache_path=str(ROOT / ".token_cache"),
    redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")),
    retries=5, status_retries=5)

wanted = json.loads((ROOT / "radio_bangers.json").read_text(encoding="utf-8"))
found, missed = [], []
seen = set()

for artist, title in wanted:
    hit = None
    for q in (f"track:{title} artist:{artist}", f"{title} {artist}"):
        try:
            r = sp.search(q, type="track", limit=5, market="DE")
        except spotipy.exceptions.SpotifyException as e:
            print(f"Suche fehlgeschlagen ({e.http_status}): {q}")
            r = None
        items = (r or {}).get("tracks", {}).get("items", [])
        if items:
            # bevorzugt exakter Titel-Prefix-Match, sonst erster Treffer
            hit = next((t for t in items
                        if t["name"].lower().startswith(title.split(" - ")[0].lower())),
                       items[0])
            break
        time.sleep(0.1)
    if hit and hit["id"] not in seen:
        seen.add(hit["id"])
        found.append(hit)
        print(f"OK   {hit['artists'][0]['name']} - {hit['name']}")
    elif not hit:
        missed.append(f"{artist} - {title}")
        print(f"MISS {artist} - {title}")
    time.sleep(0.1)

print(f"\nGefunden: {len(found)}, nicht gefunden: {len(missed)}")
for m in missed:
    print(f"  MISS: {m}")

me_id = sp.current_user()["id"]
pid = None
page = sp.current_user_playlists(limit=50)
while page:
    for pl in page["items"]:
        if pl["name"] == NAME and pl["owner"]["id"] == me_id:
            pid = pl["id"]
    page = sp.next(page) if page.get("next") else None

ids = [t["id"] for t in found]
if pid is None:
    pl = sp._post("me/playlists", payload={
        "name": NAME, "public": False,
        "description": "Die Radio-Banger von damals, 2005-2017 (spotify-sorter)"})
    pid = pl["id"]
for i in range(0, len(ids), 100):
    sp.playlist_add_items(pid, ids[i:i + 100])
    time.sleep(0.1)
print(f"'{NAME}': {len(ids)} Songs")

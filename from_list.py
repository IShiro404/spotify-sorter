"""Generischer Playlist-Builder: JSON-Liste [[artist, title], ...] auf Spotify
suchen und als private Playlist anlegen/erweitern.

Usage: python from_list.py <liste.json> "<Playlist-Name>" "<Beschreibung>"
"""

import json
import os
import sys
import time
from pathlib import Path

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

ROOT = Path(__file__).parent


def main():
    src, name, desc = sys.argv[1], sys.argv[2], sys.argv[3]
    load_dotenv(ROOT / ".env")
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        scope="playlist-read-private playlist-modify-private",
        cache_path=str(ROOT / ".token_cache"),
        redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")),
        retries=5, status_retries=5)

    wanted = json.loads(Path(src).read_text(encoding="utf-8"))
    found, missed, seen = [], [], set()

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
            if pl["name"] == name and pl["owner"]["id"] == me_id:
                pid = pl["id"]
        page = sp.next(page) if page.get("next") else None

    ids = [t["id"] for t in found]
    if pid is None:
        pl = sp._post("me/playlists", payload={
            "name": name, "public": False, "description": desc})
        pid = pl["id"]
    for i in range(0, len(ids), 100):
        sp.playlist_add_items(pid, ids[i:i + 100])
        time.sleep(0.1)
    print(f"'{name}': {len(ids)} Songs (Playlist-ID {pid})")


if __name__ == "__main__":
    main()

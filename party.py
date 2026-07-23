"""Jungsabend-Playlist aus den Party-Ratings bauen.

Liest data/party_rated_*.json (id + energy 1-3), ordnet die Tracks mit
einfacher Flow-Logik und erstellt/aktualisiert die private Playlist
"Jungsabend \U0001F37B" (kompletter Rebuild der Reihenfolge bei jedem Lauf).

Flow-Regeln:
- Warm-up: die ersten ~8 Slots bevorzugen energy 2, danach Peaks (3)
  gleichmaessig verteilt, energy 1 als Verschnaufer dazwischen
- gleicher Artist nicht innerhalb von 6 Slots
- gleiches Genre max. 3x hintereinander
"""

import glob
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
NAME = "Jungsabend \U0001F37B"


def build_order():
    lib = json.loads((DATA / "library.json").read_text(encoding="utf-8"))
    manual = json.loads((DATA / "manual_genres.json").read_text(encoding="utf-8"))

    rated = {}
    for f in sorted(glob.glob(str(DATA / "party_rated_*.json"))):
        for e in json.loads(Path(f).read_text(encoding="utf-8")):
            rated[e["id"]] = max(e["energy"], rated.get(e["id"], 0))

    pool = []
    for tid, energy in rated.items():
        t = lib["tracks"].get(tid)
        if not t:
            continue
        genres = set()
        for a in t["artists"]:
            genres |= set(manual.get(a["id"], []))
        pool.append({
            "id": tid, "name": t["name"], "energy": energy,
            "artist": t["artists"][0]["name"] if t["artists"] else "?",
            "genres": genres or {"?"},
        })

    rng = random.Random(42)
    rng.shuffle(pool)
    order = []
    recent_artists = []   # letzte 6 Slots
    recent_genres = []    # letzte 3 Slots

    def target_energy(slot):
        if slot < 8:
            return 2
        return 3 if slot % 3 != 2 else 2   # 2 Peaks, 1 Traeger, im Wechsel

    while pool:
        slot = len(order)
        want = target_energy(slot)

        def score(c):
            s = -abs(c["energy"] - want) * 2.0
            if c["artist"] in recent_artists:
                s -= 10.0
            g3 = [g for gs in recent_genres for g in gs]
            if recent_genres and all(c["genres"] & gs for gs in recent_genres) and len(recent_genres) >= 3:
                s -= 3.0
            s += rng.random()
            return s

        best = max(pool, key=score)
        pool.remove(best)
        order.append(best)
        recent_artists = (recent_artists + [best["artist"]])[-6:]
        recent_genres = (recent_genres + [best["genres"]])[-3:]

    return order


def main():
    import os
    import time
    import spotipy
    from dotenv import load_dotenv
    from spotipy.oauth2 import SpotifyOAuth

    load_dotenv(ROOT / ".env")
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        scope="playlist-read-private playlist-modify-private",
        cache_path=str(ROOT / ".token_cache"),
        redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")),
        retries=5, status_retries=5)

    order = build_order()
    n3 = sum(1 for t in order if t["energy"] == 3)
    print(f"{len(order)} Tracks (davon {n3} Peaks)")
    for t in order[:15]:
        print(f"  {t['energy']}  {t['artist']} - {t['name']}")

    me_id = sp.current_user()["id"]
    pid = None
    page = sp.current_user_playlists(limit=50)
    while page:
        for pl in page["items"]:
            if pl["name"] == NAME and pl["owner"]["id"] == me_id:
                pid = pl["id"]
        page = sp.next(page) if page.get("next") else None

    ids = [t["id"] for t in order]
    if pid is None:
        pl = sp._post("me/playlists", payload={
            "name": NAME, "public": False,
            "description": "Party-Auswahl aus der eigenen Library, einfach durchlaufen lassen (spotify-sorter)"})
        pid = pl["id"]
        for i in range(0, len(ids), 100):
            sp.playlist_add_items(pid, ids[i:i + 100])
            time.sleep(0.1)
        print(f"'{NAME}' erstellt: {len(ids)} Songs")
    else:
        # Rebuild: replace_items setzt die ersten 100, Rest anhaengen
        sp.playlist_replace_items(pid, ids[:100])
        for i in range(100, len(ids), 100):
            sp.playlist_add_items(pid, ids[i:i + 100])
            time.sleep(0.1)
        print(f"'{NAME}' neu aufgebaut: {len(ids)} Songs")


if __name__ == "__main__":
    main()

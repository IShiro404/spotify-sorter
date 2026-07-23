"""Spotify-Library nach Genres in neue [Sorted]-Playlists einsortieren.

Subcommands:
  export    Alle Playlists + Liked Songs -> data/library.json,
            Artist-Genres -> data/artists.json,
            Artists ohne Genre-Tags -> data/unknown_artists.json
  classify  Tracks -> Buckets (genre_map + data/manual_genres.json)
            -> data/assignment.json + Konsolen-Report
  create    [Sorted]-Playlists anlegen/aktualisieren (nur hinzufügen,
            niemals löschen; bestehende Playlists werden nie verändert)

Liest niemals schreibend auf bestehende Nicht-[Sorted]-Playlists zu.
"""

import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from genre_map import BUCKETS, buckets_for_genres

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

SCOPES = (
    "user-library-read playlist-read-private playlist-read-collaborative "
    "playlist-modify-private playlist-modify-public"
)
PREFIX = "[Sorted] "


def client():
    load_dotenv(ROOT / ".env")
    auth = SpotifyOAuth(
        client_id=os.environ["SPOTIPY_CLIENT_ID"],
        client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
        redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        scope=SCOPES,
        cache_path=str(ROOT / ".token_cache"),
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth, retries=5, status_retries=5)


def paged(fetch_first, get_next):
    page = fetch_first()
    while page:
        yield from page["items"]
        page = get_next(page) if page.get("next") else None


def cmd_export():
    sp = client()
    me = sp.current_user()
    print(f"Eingeloggt als: {me['display_name']} ({me['id']})")

    tracks = {}          # track_id -> {name, artists: [{id, name}], sources: [...]}
    sources_count = {}

    def add_track(item, source):
        # Playlist-Items kommen je nach API-Version als "track" oder "item"
        t = item.get("track") or item.get("item")
        if not t or t.get("is_local") or not t.get("id"):
            return
        e = tracks.setdefault(t["id"], {
            "name": t["name"],
            "artists": [{"id": a["id"], "name": a["name"]} for a in t["artists"] if a.get("id")],
            "sources": [],
        })
        if source not in e["sources"]:
            e["sources"].append(source)

    # Liked Songs
    n = 0
    for item in paged(lambda: sp.current_user_saved_tracks(limit=50), sp.next):
        add_track(item, "__liked__")
        n += 1
    sources_count["Liked Songs"] = n
    print(f"Liked Songs: {n}")

    # Alle Playlists (eigene + gefolgte), [Sorted]-Playlists überspringen.
    # Spotify-eigene/redaktionelle Playlists liefern für Dev-Mode-Apps 403
    # (API-Einschränkung seit Nov 2024) -> überspringen und melden.
    skipped = []
    for pl in paged(lambda: sp.current_user_playlists(limit=50), sp.next):
        if pl["name"].startswith(PREFIX):
            continue
        n = 0
        try:
            for item in paged(
                lambda pl=pl: sp.playlist_items(pl["id"], limit=100,
                                                additional_types=("track",)),
                sp.next,
            ):
                add_track(item, pl["name"])
                n += 1
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status in (403, 404):
                skipped.append(f"{pl['name']} (owner: {pl['owner'].get('display_name', '?')})")
                continue
            raise
        sources_count[pl["name"]] = n
        print(f"Playlist '{pl['name']}': {n} Songs")
    if skipped:
        print(f"\nÜbersprungen (kein API-Zugriff, i.d.R. Spotify-eigene Playlists): {len(skipped)}")
        for s in skipped:
            print(f"  - {s}")

    (DATA / "library.json").write_text(
        json.dumps({"tracks": tracks, "sources": sources_count}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nGesamt unique Tracks: {len(tracks)}")

    # Artist-Genres in 50er-Batches. Für neue Dev-Mode-Apps liefert Spotify
    # seit 2025 keine Genres mehr (Batch-Endpoint 403, "genres"-Feld entfernt)
    # -> dann artists.json ohne Genres schreiben; Klassifikation macht Claude
    # über data/manual_genres.json.
    artist_ids = sorted({a["id"] for t in tracks.values() for a in t["artists"]})
    names = {a["id"]: a["name"] for t in tracks.values() for a in t["artists"]}
    artists = {}
    try:
        for i in range(0, len(artist_ids), 50):
            batch = artist_ids[i:i + 50]
            for a in sp.artists(batch)["artists"]:
                if a:
                    artists[a["id"]] = {"name": a["name"], "genres": a.get("genres", [])}
            time.sleep(0.1)
    except spotipy.exceptions.SpotifyException as e:
        print(f"Artist-Genre-Abruf nicht möglich (HTTP {e.http_status}) — "
              "fahre ohne Spotify-Genres fort.")
        artists = {aid: {"name": names[aid], "genres": []} for aid in artist_ids}
    (DATA / "artists.json").write_text(
        json.dumps(artists, ensure_ascii=False, indent=1), encoding="utf-8")

    unknown = {aid: v["name"] for aid, v in artists.items() if not v["genres"]}
    (DATA / "unknown_artists.json").write_text(
        json.dumps(unknown, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Artists gesamt: {len(artists)}, ohne Genre-Tags: {len(unknown)}")
    print("-> data/unknown_artists.json (werden von Claude manuell klassifiziert)")


def load_manual():
    p = DATA / "manual_genres.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def cmd_classify():
    lib = json.loads((DATA / "library.json").read_text(encoding="utf-8"))
    artists = json.loads((DATA / "artists.json").read_text(encoding="utf-8"))
    manual = load_manual()   # artist_id -> [bucket, ...]

    assignment = defaultdict(list)   # bucket -> [track_id]
    unmatched = []

    for tid, t in lib["tracks"].items():
        hits = set()
        for a in t["artists"]:
            info = artists.get(a["id"], {})
            hits |= buckets_for_genres(info.get("genres", []))
            for b in manual.get(a["id"], []):
                if b in BUCKETS:
                    hits.add(b)
        if not hits:
            hits = {"Sonstiges"}
            unmatched.append(t["name"] + " — " + ", ".join(x["name"] for x in t["artists"]))
        for b in hits:
            assignment[b].append(tid)

    # Vollständigkeits-Check: jeder Track in >= 1 Bucket
    assigned = {tid for ids in assignment.values() for tid in ids}
    assert assigned == set(lib["tracks"]), "Vollständigkeits-Check fehlgeschlagen!"

    (DATA / "assignment.json").write_text(
        json.dumps(assignment, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Unique Tracks: {len(lib['tracks'])}\n")
    for b in BUCKETS:
        ids = assignment.get(b, [])
        examples = [lib["tracks"][i]["name"] for i in ids[:3]]
        print(f"{b:24s} {len(ids):5d}   z.B. {'; '.join(examples)}")
    print(f"\nNur in 'Sonstiges': {len(assignment.get('Sonstiges', []))}")
    if unmatched:
        (DATA / "unmatched_tracks.txt").write_text("\n".join(unmatched), encoding="utf-8")
        print("Liste -> data/unmatched_tracks.txt")


def cmd_create():
    sp = client()
    me = sp.current_user()
    lib = json.loads((DATA / "library.json").read_text(encoding="utf-8"))
    assignment = json.loads((DATA / "assignment.json").read_text(encoding="utf-8"))

    # Bestehende [Sorted]-Playlists finden (idempotenter Re-Run)
    existing = {}
    for pl in paged(lambda: sp.current_user_playlists(limit=50), sp.next):
        if pl["name"].startswith(PREFIX) and pl["owner"]["id"] == me["id"]:
            existing[pl["name"]] = pl["id"]

    for bucket in BUCKETS:
        ids = assignment.get(bucket, [])
        if not ids:
            continue
        name = PREFIX + bucket
        if name in existing:
            pid = existing[name]
            have = set()
            for item in paged(
                lambda: sp.playlist_items(pid, limit=100, additional_types=("track",)),
                sp.next,
            ):
                t = item.get("track") or item.get("item")
                if t and t.get("id"):
                    have.add(t["id"])
            todo = [i for i in ids if i not in have]
            action = "aktualisiert"
        else:
            # POST /users/{id}/playlists liefert fuer neue Dev-Apps 403,
            # /me/playlists funktioniert
            pl = sp._post("me/playlists", payload={
                "name": name, "public": False,
                "description": "Automatisch nach Genre sortiert (spotify-sorter)"})
            pid = pl["id"]
            todo = list(dict.fromkeys(ids))
            action = "erstellt"

        for i in range(0, len(todo), 100):
            sp.playlist_add_items(pid, todo[i:i + 100])
            time.sleep(0.1)
        print(f"{name}: {action}, +{len(todo)} Songs (gesamt Bucket: {len(set(ids))})")

    print("\nFertig. Bestehende Playlists wurden nicht verändert.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "export":
        cmd_export()
    elif cmd == "classify":
        cmd_classify()
    elif cmd == "create":
        cmd_create()
    else:
        print("Usage: python sorter.py [export|classify|create]")
        sys.exit(1)

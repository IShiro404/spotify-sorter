"""Einmaliges Update der Calm-Banger-Playlist: Nischen-Tracks raus,
bekannte Calm-Banger + Library-Favoriten rein."""

import os
import time
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

PID = "4QBqCxXjIOBNQGGfiHafWF"

REMOVE = [  # (artist-substring, title-substring), beides muss matchen
    ("novo amor", "anchor"), ("bruno major", "nothing"),
    ("sufjan", "mystery of love"), ("ben howard", "only love"),
    ("ben howard", "promise"), ("damien rice", "9 crimes"),
    ("gonzalez", "heartbeats"), ("stone", "big jet plane"),
    ("max richter", "nature of daylight"), ("winehouse", "losing game"),
    ("oasis", "half the world away"), ("chapman", "baby can i hold you"),
    ("fleetwood", "landslide"), ("marvin gaye", "what's going on"),
    ("sam cooke", "change is gonna come"), ("goulding", "how long will i love you"),
    ("snow patrol", "run"), ("lumineers", "sleep on the floor"),
    ("bon iver", "holocene"), ("radiohead", "karma police"),
]

LIB_ADD = [  # Track-IDs direkt aus Emres Library
    "2QjOHCTQ1Jl3zawyYOpxh6",  # The Neighbourhood - Sweater Weather
    "7m9OqQk4RVRkw9JJdeAw96",  # XXXTENTACION - Jocelyn Flores
    "0JP9xo3adEtGSdUEISiszL",  # XXXTENTACION - Moonlight
    "2HafqoJbgXdtjwCOvNEF14",  # Iñigo Quintero - Si No Estás
    "7qjZnBKE73H4Oxkopwulqe",  # sombr - back to friends
    "0TFTAtCYhp2tQ9KcJIZb55",  # sombr - undressed
    "0VOnehekjQz9cvUwLzmYSQ",  # Semicenk - Sen Kaldın
    "4SJjMPowhsrYSWgxM61yxm",  # Semicenk - Çıkmaz Bir Sokakta
    "0EKQyZOAnheVB6pumbtggA",  # Yüzyüzeyken Konuşuruz - Kaş
    "3Ommpa2aE0RU3F04BedepA",  # Şebnem Ferah - Bu Aşk Fazla Sana
    "65i0i1aixjk7GoJaMEnKqy",  # Paula Hartmann - Nie verliebt
    "4PMqSO5qyjpvzhlLI5GnID",  # SZA - Good Days
]

SEARCH_ADD = [
    ("Radiohead", "Creep"),
    ("Ed Sheeran", "Perfect"),
    ("Ed Sheeran", "Thinking Out Loud"),
    ("Bruno Mars", "When I Was Your Man"),
    ("Bruno Mars", "Talking To The Moon"),
    ("Adele", "Hello"),
    ("Rihanna Mikky Ekko", "Stay"),
    ("Eminem", "Mockingbird"),
    ("2Pac", "Changes"),
    ("Leona Lewis", "Bleeding Love"),
    ("Beyonce", "Halo"),
    ("Wiz Khalifa Charlie Puth", "See You Again"),
    ("Imagine Dragons", "Demons"),
    ("OneRepublic Timbaland", "Apologize"),
    ("The Script", "The Man Who Can't Be Moved"),
    ("Justin Bieber", "Love Yourself"),
    ("James Arthur", "Impossible"),
    ("Lukas Graham", "7 Years"),
    ("Milow", "Ayo Technology"),
    ("Green Day", "Boulevard of Broken Dreams"),
    ("Evanescence", "My Immortal"),
    ("Oasis", "Wonderwall"),
    ("The Beatles", "Let It Be"),
    ("Goo Goo Dolls", "Iris"),
    ("A Great Big World Christina Aguilera", "Say Something"),
    ("Labrinth", "Jealous"),
    ("Duncan Laurence", "Arcade"),
    ("One Direction", "Night Changes"),
    ("Stephen Sanchez", "Until I Found You"),
    ("Ruth B.", "Dandelions"),
]

load_dotenv(".env")
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="playlist-read-private playlist-modify-private",
    cache_path=".token_cache",
    redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"]), retries=5)

items = []
page = sp.playlist_items(PID, limit=100, additional_types=("track",))
while page:
    for it in page["items"]:
        t = it.get("track") or it.get("item")
        if t:
            items.append(t)
    page = sp.next(page) if page.get("next") else None
print(f"Aktuell: {len(items)} Songs")

to_remove = []
for t in items:
    artists = " ".join(a["name"] for a in t["artists"]).lower()
    for a_sub, t_sub in REMOVE:
        if a_sub in artists and t_sub in t["name"].lower():
            to_remove.append(t)
            break
for t in to_remove:
    print(f"RAUS  {t['artists'][0]['name']} - {t['name']}")
if to_remove:
    sp.playlist_remove_all_occurrences_of_items(PID, [t["id"] for t in to_remove])

have = {t["id"] for t in items} - {t["id"] for t in to_remove}
add = [i for i in LIB_ADD if i not in have]

for artist, title in SEARCH_ADD:
    hit = None
    for q in (f"track:{title} artist:{artist}", f"{title} {artist}"):
        r = sp.search(q, type="track", limit=5, market="DE")
        cands = r.get("tracks", {}).get("items", [])
        if cands:
            hit = next((t for t in cands
                        if t["name"].lower().startswith(title.lower())), cands[0])
            break
        time.sleep(0.1)
    if hit and hit["id"] not in have and hit["id"] not in add:
        add.append(hit["id"])
        print(f"REIN  {hit['artists'][0]['name']} - {hit['name']}")
    elif not hit:
        print(f"MISS  {artist} - {title}")
    time.sleep(0.1)

for i in range(0, len(add), 100):
    sp.playlist_add_items(PID, add[i:i + 100])
print(f"\nEntfernt: {len(to_remove)}, hinzugefuegt: {len(add)}, neu gesamt: {len(have) + len(add)}")

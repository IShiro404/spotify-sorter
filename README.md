# spotify-sorter

Sortiert deine komplette Spotify-Library (alle Playlists + Liked Songs) automatisch
in neue Genre-Playlists mit Präfix `[Sorted]` — z.B. Jazz, Deutschrap, Hip-Hop,
Electronic. Bestehende Playlists werden **nie** verändert, nur gelesen.

Da Spotify seit 2025 keine Genre-Daten mehr über die API liefert (siehe unten),
übernimmt ein LLM (z.B. Claude) die Genre-Klassifikation der Artists — mit
Beispiel-Tracks und deinen Playlist-Namen als Kontext funktioniert das erstaunlich gut.

Bonus: `party.py` baut aus den eigenen Songs eine Party-Playlist mit Flow-Ordering
(Peaks verteilt, kein Artist doppelt hintereinander).

## Setup

1. App auf https://developer.spotify.com/dashboard anlegen (kostenlos),
   Redirect URI: `http://127.0.0.1:8888/callback`, Web API anhaken
2. `.env` anlegen:
   ```
   SPOTIPY_CLIENT_ID=...
   SPOTIPY_CLIENT_SECRET=...
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```
3. `pip install spotipy python-dotenv`

## Ablauf

```
python sorter.py export     # Library abrufen -> data/library.json + data/unknown_artists.json
# data/manual_genres.json erstellen: {artist_id: ["Bucket", ...], ...}
#   -> am einfachsten per LLM (Artist-Name + Beispiel-Tracks + Quell-Playlists mitgeben)
python sorter.py classify   # Buckets berechnen, Report ansehen
python sorter.py create     # [Sorted]-Playlists anlegen/aktualisieren
```

Re-Runs sind idempotent: `create` fügt nur Songs hinzu, die noch fehlen —
perfekt, um später neue Musik nachzusortieren.

Buckets (in `genre_map.py` anpassbar): Deutschrap, Türkisch, Hip-Hop/Rap, R&B/Soul,
Pop, Rock/Metal, Electronic/House, Jazz, Chill/Lo-Fi, Latin/International, Sonstiges.
Mehrfachzuordnung ist gewollt — ein Song darf in mehreren Playlists landen.

## Spotify-API-Fallen (Stand 2026, neue Dev-Mode-Apps)

Hart erarbeitete Erkenntnisse, die dir Debugging-Stunden sparen:

- **Playlist-Items** kommen teils unter dem Key `item` statt `track` zurück
- **Redaktionelle/fremd-kuratierte Playlists** liefern `403 Forbidden` — die
  kannst du nicht mehr auslesen, nur überspringen
- **Artist-Genres gibt es nicht mehr**: der Batch-Endpoint `/v1/artists?ids=...`
  liefert 403, und Einzelabfragen enthalten kein `genres`-Feld mehr — deshalb
  die LLM-Klassifikation
- **Playlist erstellen**: `POST /users/{id}/playlists` liefert 403 —
  `POST /me/playlists` funktioniert
- Redirect URI muss `127.0.0.1` sein, nicht `localhost`

## Lizenz

MIT

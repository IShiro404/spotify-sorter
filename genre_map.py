"""Mapping von Spotify-Artist-Genre-Tags auf grobe Playlist-Buckets.

Ein Artist kann mehrere Buckets treffen (Mehrfachzuordnung gewollt).
Reihenfolge der Regeln egal — alle Treffer zählen.
Sprach-/Szene-Buckets (Deutschrap, Türkisch) haben Vorrang vor dem
generischen Hip-Hop-Bucket: matcht ein Artist deutschrap/turkish hip hop,
landet er NICHT zusätzlich in "Hip-Hop / Rap".
"""

BUCKETS = [
    "Deutschrap",
    "Türkisch",
    "Hip-Hop / Rap",
    "R&B / Soul",
    "Pop",
    "Rock / Metal",
    "Electronic / House",
    "Jazz",
    "Chill / Lo-Fi",
    "Latin / International",
    "Sonstiges",
]

# Substring-Regeln: taucht der Key in einem Spotify-Genre-Tag auf → Bucket.
# Spotify-Tags sind lowercase ("german hip hop", "turkish pop", "lo-fi beats" ...).
RULES = {
    "Deutschrap": [
        "german hip hop", "german rap", "deutschrap", "german drill",
        "german trap", "german cloud rap", "austrian hip hop", "swiss hip hop",
    ],
    "Türkisch": [
        "turkish", "anatolian", "arabesk", "turk ",
    ],
    "Hip-Hop / Rap": [
        "hip hop", "hip-hop", "rap", "trap", "drill", "boom bap", "grime",
        "crunk", "hyphy", "phonk",
    ],
    "R&B / Soul": [
        "r&b", "rnb", "soul", "neo soul", "new jack swing", "quiet storm",
        "funk", "motown", "afrobeats", "afro r&b",
    ],
    "Pop": [
        "pop", "boy band", "girl group", "singer-songwriter", "idol",
    ],
    "Rock / Metal": [
        "rock", "metal", "punk", "grunge", "emo", "hardcore", "indie",
        "alternative", "shoegaze", "post-", "nu metal", "metalcore",
    ],
    "Electronic / House": [
        "house", "techno", "edm", "electro", "dance", "dubstep", "dnb",
        "drum and bass", "trance", "garage", "bass", "big room", "hardstyle",
        "future", "synthwave", "eurodance", "electronic",
    ],
    "Jazz": [
        "jazz", "bebop", "bossa nova", "swing", "big band", "blues",
    ],
    "Chill / Lo-Fi": [
        "lo-fi", "lofi", "chill", "ambient", "sleep", "study beats",
        "downtempo", "chillhop",
    ],
    "Latin / International": [
        "latin", "reggaeton", "salsa", "bachata", "cumbia", "corrido",
        "dembow", "brazilian", "k-pop", "j-pop", "afro", "amapiano",
        "dancehall", "reggae", "arab", "french", "italian", "russian",
        "balkan", "desi", "bollywood", "punjabi",
    ],
}

# Tags, die trotz Substring-Treffer NICHT in den jeweiligen Bucket sollen.
# Format: bucket -> Liste von Substrings, die den Treffer aufheben.
EXCLUDES = {
    "Pop": ["k-pop", "j-pop", "latin pop", "turkish pop"],          # gehen in Latin/International bzw. Türkisch
    "Hip-Hop / Rap": ["german", "deutschrap", "turkish", "austrian", "swiss"],
    "Rock / Metal": ["pop punk"],                                    # bleibt trotzdem via "punk"? nein: pop punk -> Rock ist ok
    "Electronic / House": ["bassline jazz"],
}
EXCLUDES["Rock / Metal"] = []  # pop punk soll in Rock bleiben
EXCLUDES["Electronic / House"] = []


def buckets_for_genres(genre_tags):
    """Liefert die Menge der Buckets für die Genre-Tags eines Artists."""
    hits = set()
    tags = [t.lower() for t in genre_tags]
    for bucket, keys in RULES.items():
        excludes = EXCLUDES.get(bucket, [])
        for tag in tags:
            if any(k in tag for k in keys) and not any(x in tag for x in excludes):
                hits.add(bucket)
                break
    return hits

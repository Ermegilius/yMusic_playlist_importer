import json
import csv
import time
import os
import urllib.request
import urllib.parse


# --- Load .env file (no external dependencies) ---

def _load_dotenv(path: str = ".env") -> None:
    """Parse a simple KEY=VALUE .env file and populate os.environ."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    except FileNotFoundError:
        pass  # .env is optional; tokens can also be set in the shell environment

_load_dotenv()


# --- Users ---
# Users are loaded automatically from the .env file.
# Add USER_<n>_NAME and USER_<n>_TOKEN pairs for each user (n = 1, 2, 3, ...).

def _load_users() -> list[dict]:
    """Discover all USER_<n>_NAME / USER_<n>_TOKEN pairs from environment."""
    users = []
    n = 1
    while True:
        name = os.environ.get(f"USER_{n}_NAME", "").strip()
        token = os.environ.get(f"USER_{n}_TOKEN", "").strip()
        if not name and not token:
            break  # no more entries
        if name and token:
            users.append({"name": name, "token": token})
        elif name:
            print(f"Warning: USER_{n}_NAME is set but USER_{n}_TOKEN is missing — skipping.")
        else:
            print(f"Warning: USER_{n}_TOKEN is set but USER_{n}_NAME is missing — skipping.")
        n += 1
    return users

USERS = _load_users()

BATCH_SIZE = 100


# --- Helper functions ---

def make_headers(token: str) -> dict:
    return {
        "Authorization": f"OAuth {token}",
        "X-Yandex-Music-Client": "WindowsPhone/3.17",
    }


def api_get(url: str, headers: dict) -> dict | None:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  GET error: {e}")
        return None


def api_post(url: str, headers: dict, body: dict) -> dict | None:
    data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  POST error: {e}")
        return None


def fetch_uid(headers: dict) -> str | None:
    resp = api_get("https://api.music.yandex.net/account/status", headers)
    if resp:
        return resp.get("result", {}).get("account", {}).get("uid")
    return None


def fetch_likes_ids(uid: str, headers: dict) -> list[str]:
    resp = api_get(f"https://api.music.yandex.net/users/{uid}/likes/tracks", headers)
    if not resp:
        return []
    tracks = resp.get("result", {}).get("library", {}).get("tracks", [])
    return [f"{t['id']}:{t['albumId']}" for t in tracks]


def fetch_tracks_batch(ids: list[str], headers: dict) -> list[dict]:
    resp = api_post("https://api.music.yandex.net/tracks", headers, {"track-ids": ",".join(ids)})
    return resp.get("result", []) if resp else []


def fetch_playlists_list(uid: str, headers: dict) -> list[dict]:
    """Return all playlists for the user (kind, title, trackCount)."""
    resp = api_get(f"https://api.music.yandex.net/users/{uid}/playlists/list", headers)
    return resp.get("result", []) if resp else []


def fetch_playlist_tracks(uid: str, kind: int, headers: dict) -> list[dict]:
    """Return full track objects for a playlist."""
    resp = api_get(f"https://api.music.yandex.net/users/{uid}/playlists/{kind}", headers)
    if not resp:
        return []
    raw = resp.get("result", {}).get("tracks", [])
    # Tracks may be full objects or wrapped under a nested "track" key
    return [item["track"] if "track" in item else item for item in raw]


def get_artists(track: dict) -> str:
    return ", ".join(a.get("name", "") for a in track.get("artists", []))


def get_album(track: dict) -> str:
    albums = track.get("albums", [])
    return albums[0].get("title", "") if albums else ""


def get_year(track: dict) -> str:
    albums = track.get("albums", [])
    return str(albums[0].get("year", "")) if albums else ""


def ms_to_min(ms) -> str:
    if not ms:
        return ""
    total_sec = ms // 1000
    return f"{total_sec // 60}:{total_sec % 60:02d}"


def fetch_single_track(track_id, headers: dict) -> dict | None:
    resp = api_get(f"https://api.music.yandex.net/tracks/{track_id}", headers)
    if resp and resp.get("result"):
        return resp["result"][0]
    return None


def _fetch_unavailable_details(tracks: list[dict], headers: dict) -> list[dict]:
    """For every track with an error, fetch full metadata individually."""
    ids = [str(t.get("id", "")) for t in tracks if t.get("error")]
    if not ids:
        return []
    print(f"    Fetching details for {len(ids)} unavailable track(s)...")
    details = []
    for tid in ids:
        detail = fetch_single_track(tid, headers)
        if detail:
            details.append(detail)
        time.sleep(0.2)
    return details


def save_unavailable_csv(tracks: list[dict], path: str) -> str | None:
    if not tracks:
        return None
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["#", "Title", "Artist", "Album", "Year", "Duration", "ID", "Error"])
        for i, track in enumerate(tracks, 1):
            writer.writerow([
                i,
                track.get("title", ""),
                get_artists(track),
                get_album(track),
                get_year(track),
                ms_to_min(track.get("durationMs")),
                track.get("id", ""),
                track.get("error", ""),
            ])
    print(f"    Unavailable tracks ({len(tracks)}) → {path}")
    return path


def _safe_filename(s: str) -> str:
    """Strip characters unsafe for filenames."""
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in s).strip()


def save_playlist_csv(tracks: list[dict], user_name: str, playlist_title: str) -> str:
    safe_title = _safe_filename(playlist_title)
    path = f"playlist_{user_name}_{safe_title}.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["#", "Title", "Artist", "Album", "Year", "Duration", "ID", "Availability"])
        row_num = 1
        unavailable = 0
        for track in tracks:
            error = track.get("error")
            if error:
                unavailable += 1
                writer.writerow([row_num, "", "", "", "", "", track.get("id", ""), f"Unavailable ({error})"])
            else:
                writer.writerow([
                    row_num,
                    track.get("title", ""),
                    get_artists(track),
                    get_album(track),
                    get_year(track),
                    ms_to_min(track.get("durationMs")),
                    track.get("id", ""),
                    "OK",
                ])
            row_num += 1
    print(f"    Saved {row_num - 1} tracks  →  {path}  (unavailable: {unavailable})")
    return path


def save_csv(tracks: list[dict], name: str) -> str:
    path = f"liked_tracks_{name}.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["#", "Title", "Artist", "Album", "Year", "Duration", "ID", "Availability"])
        row_num = 1
        unavailable = 0
        for track in tracks:
            error = track.get("error")
            if error:
                unavailable += 1
                writer.writerow([
                    row_num,
                    "",
                    "",
                    "",
                    "",
                    "",
                    track.get("id", ""),
                    f"Unavailable ({error})",
                ])
            else:
                writer.writerow([
                    row_num,
                    track.get("title", ""),
                    get_artists(track),
                    get_album(track),
                    get_year(track),
                    ms_to_min(track.get("durationMs")),
                    track.get("id", ""),
                    "OK",
                ])
            row_num += 1
    print(f"  Saved tracks: {row_num - 1}  →  {path}  (unavailable: {unavailable})")
    return path


# --- Main loop over users ---

if not USERS:
    print("No users found. Add USER_1_NAME / USER_1_TOKEN entries to your .env file.")
else:
    for user in USERS:
        name = user["name"]
        headers = make_headers(user["token"])
        print(f"\n{'='*40}")
        print(f"User: {name}")

        uid = fetch_uid(headers)
        if not uid:
            print("  Could not retrieve UID, skipping.")
            continue
        print(f"  UID: {uid}")

        track_ids = fetch_likes_ids(uid, headers)
        if not track_ids:
            print("  Likes list is empty or request failed.")
            continue
        print(f"  Liked tracks: {len(track_ids)}")

        all_tracks = []
        total_batches = (len(track_ids) + BATCH_SIZE - 1) // BATCH_SIZE
        for i in range(0, len(track_ids), BATCH_SIZE):
            batch = track_ids[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            print(f"  Batch {batch_num}/{total_batches}...", end="\r")
            all_tracks.extend(fetch_tracks_batch(batch, headers))
            time.sleep(0.3)

        print(f"  Fetched tracks: {len(all_tracks)}        ")
        save_csv(all_tracks, name)

        unavailable_details = _fetch_unavailable_details(all_tracks, headers)
        save_unavailable_csv(unavailable_details, f"unavailable_tracks_{name}.csv")

        # --- Playlists ---
        playlists = fetch_playlists_list(uid, headers)
        if playlists:
            print(f"  Playlists: {len(playlists)}")
            for pl in playlists:
                kind = pl.get("kind")
                title = pl.get("title", f"playlist_{kind}")
                track_count = pl.get("trackCount", "?")
                print(f"  → '{title}' ({track_count} tracks)...")
                pl_tracks = fetch_playlist_tracks(uid, kind, headers)
                save_playlist_csv(pl_tracks, name, title)
                details = _fetch_unavailable_details(pl_tracks, headers)
                save_unavailable_csv(details, f"unavailable_playlist_{name}_{_safe_filename(title)}.csv")
                time.sleep(0.3)

print(f"\n{'='*40}")
print("Done!")

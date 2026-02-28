# Yandex Music Exporter — Usage Guide

## Requirements

- A browser
- Python 3.10+
- Postman (optional, for manual verification)

---

## Step 1 — Get an OAuth token

Yandex Music has no official public API, but you can authenticate using the `client_id` of the official Yandex Music app.

Open this URL in your browser:

```
https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d
```

> `client_id=23cabbbdc6cd418abb4b39c32c41195d` was reportedly extracted from the official Yandex Music Windows Phone app by someone in the open-source community and appears in several projects. I cannot verify its origin or safety. Use it at your own risk.

After logging in, Yandex will redirect you to an error page — that's expected. Copy the `access_token` from the URL:

```
https://music.yandex.ru/#access_token=y0__xC...&token_type=bearer&expires_in=...
```

Save the token — it looks like `y0__xC...`.

> Tokens are valid for a long time (months), but will be revoked if you change your password.

---

## Step 2 — Verify the token (optional, via Postman)

**Request:**

```
GET https://api.music.yandex.net/account/status
```

**Headers:**

```
Authorization: OAuth <YOUR_TOKEN>
X-Yandex-Music-Client: WindowsPhone/3.17
```

**Expected response:**

```json
{
  "result": {
    "account": {
      "uid": 199751080,
      "login": "username",
      ...
    }
  }
}
```

Note your `uid` — it is required for subsequent requests.

---

## Step 3 — Get the list of liked track IDs (optional)

```
GET https://api.music.yandex.net/users/{uid}/likes/tracks
```

The response contains an array of objects with fields `id`, `albumId`, and `timestamp`.

---

## Step 4 — Run the Python script

The script automatically:

1. Retrieves the `uid` via the API
2. Downloads the list of liked track IDs
3. Fetches full track metadata in batches of 100
4. Saves the results to CSV files

### Setup

No additional libraries are required — the script uses only the Python standard library.

### Store your tokens securely

All user configuration lives in the `.env` file — no code edits required to add or remove users.

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in your entries:

   ```
   USER_1_NAME=Alice
   USER_1_TOKEN=y0__xCo...

   USER_2_NAME=Bob
   USER_2_TOKEN=y0__xCc...

   USER_3_NAME=Carol
   USER_3_TOKEN=y0__xCd...
   ```

   Add as many `USER_<n>_NAME` / `USER_<n>_TOKEN` pairs as you need. Numbering must start at `1` and be consecutive.

   `.env` is listed in `.gitignore` and will never be committed.

### Configure `fetch_tracks.py`

Nothing to edit — users are loaded automatically from `.env` at runtime.

### Run

```bash
python fetch_tracks.py
```

### Example output

```
========================================
User: Alice
  UID: ...
  Liked tracks: ...
  Fetched tracks: ...
  Saved tracks: ...  →  liked_tracks_Alice.csv  (unavailable: 0)
  Playlists: 3
  → 'Favourites' (157 tracks)...
    Saved 157 tracks  →  playlist_Alice_Favourites.csv  (unavailable: 0)
  → 'To Check' (93 tracks)...
    Saved 93 tracks  →  playlist_Alice_To_Check.csv  (unavailable: 0)
  → 'Recognised' (13 tracks)...
    Saved 13 tracks  →  playlist_Alice_Recognised.csv  (unavailable: 3)
    Fetching details for 3 unavailable track(s)...
    Unavailable tracks (3) → unavailable_playlist_Alice_Recognised.csv

========================================
User: Bob
  UID: ...
  Liked tracks: ...
  Fetched tracks: ...
  Saved tracks: ...  →  liked_tracks_Bob.csv  (unavailable: 1)
    Fetching details for 1 unavailable track(s)...
    Unavailable tracks (1) → unavailable_tracks_Bob.csv
  Playlists: 1
  → 'Road Trip' (42 tracks)...
    Saved 42 tracks  →  playlist_Bob_Road_Trip.csv  (unavailable: 0)

========================================
Done!
```

---

## Output

For each user, the following files may be created:

### `liked_tracks_{name}.csv`

All liked tracks.

| #   | Title         | Artist    | Album     | Year | Duration | ID       | Availability |
| --- | ------------- | --------- | --------- | ---- | -------- | -------- | ------------ |
| 1   | Enter Sandman | Metallica | Metallica | 1991 | 5:31     | 85560440 | OK           |
| 2   | ...           |           |           |      |          |          |              |

Tracks that cannot be played (e.g. due to `no-rights`) are still listed, with empty metadata fields and `Unavailable (no-rights)` in the Availability column.

### `unavailable_tracks_{name}.csv`

Created only when unavailable liked tracks exist. Contains full metadata fetched via individual API requests:

| #   | Title          | Artist        | Album      | Year | Duration | ID        | Error     |
| --- | -------------- | ------------- | ---------- | ---- | -------- | --------- | --------- |
| 1   | Some Audiobook | Some Narrator | Some Album |      | 5:25     | 109197665 | no-rights |

All files are saved in **UTF-8 BOM** encoding for correct display of non-Latin characters in Excel.

### `playlist_{name}_{title}.csv`

One file per playlist, same column structure as above. Special characters in the playlist title are replaced with underscores in the filename.

### `unavailable_playlist_{name}_{title}.csv`

Created per playlist when it contains unavailable tracks. Same structure as `unavailable_tracks_{name}.csv`.

---

## API endpoint reference

| Method | URL                             | Description                        |
| ------ | ------------------------------- | ---------------------------------- |
| `GET`  | `/account/status`               | Account info + uid                 |
| `GET`  | `/users/{uid}/likes/tracks`     | List of liked track IDs            |
| `POST` | `/tracks`                       | Full track metadata by IDs (batch) |
| `GET`  | `/tracks/{id}`                  | Full metadata for a single track   |
| `GET`  | `/users/{uid}/playlists/list`   | List of user playlists             |
| `GET`  | `/users/{uid}/playlists/{kind}` | Tracks in a specific playlist      |

**Base URL:** `https://api.music.yandex.net`

**Required headers:**

```
Authorization: OAuth <TOKEN>
X-Yandex-Music-Client: WindowsPhone/3.17
```

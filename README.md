# Yandex Music Likes Exporter

Yandex Music for some reason, does not provide an official way to export your music library. When you decide to leave the platform, you're on your own.

A non-coder friend of mine ran into exactly this problem. He had accumulated thousands of liked tracks over the years and wanted to move them elsewhere (no ads here). The only alternative? Adding each track manually, one by one. That's insane.

So I built this.

---

A zero-dependency Python script that exports liked tracks from Yandex Music to CSV for one or more users.

## Features

- Exports all **liked tracks** with title, artist, album, year, and duration
- Exports all **playlists** to individual CSV files
- Supports multiple users — configured entirely via `.env`, no code changes needed
- Unavailable tracks (e.g. `no-rights`) are saved to a separate CSV with full metadata fetched individually
- UTF-8 BOM encoding for correct Cyrillic display in Excel

## Requirements

- Python 3.10+

No external packages needed — uses the standard library only.

## Setup

1. **Get an OAuth token** for each user by opening this URL in a browser while logged in to the target Yandex account:

   ```
   https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d
   ```

   After login, copy `access_token` from the redirect URL.

2. **Create a `.env` file** from the template:

   ```bash
   cp .env.example .env
   ```

3. **Fill in your users** in `.env`:

   ```
   USER_1_NAME=Alice
   USER_1_TOKEN=y0__...

   USER_2_NAME=Bob
   USER_2_TOKEN=y0__...
   ```

   Add as many `USER_<n>` pairs as needed. Numbering must start at `1` and be consecutive.

## Usage

```bash
python fetch_tracks.py
```

## Output

| File                                      | Description                                                                    |
| ----------------------------------------- | ------------------------------------------------------------------------------ |
| `liked_tracks_{name}.csv`                 | All liked tracks; unavailable ones marked in the Availability column           |
| `unavailable_tracks_{name}.csv`           | Unavailable liked tracks with full metadata (created only if any exist)        |
| `playlist_{name}_{title}.csv`             | One file per playlist, same column structure (special chars → `_`)             |
| `unavailable_playlist_{name}_{title}.csv` | Unavailable tracks per playlist with full metadata (created only if any exist) |

## Notes

> This script uses the unofficial Yandex Music API via the official app's `client_id`. Tokens are valid for months but expire if you change your Yandex password.

> **About this `client_id`:** It was reportedly extracted from the official Yandex Music Windows Phone app by someone in the open-source community and appears in several projects. I cannot verify its origin or safety. Use it at your own risk.

> `.env` and all output CSV files are excluded from version control via `.gitignore`.

See [USAGE.md](USAGE.md) for a full walkthrough including API endpoint reference.

## License

[MIT](LICENSE)

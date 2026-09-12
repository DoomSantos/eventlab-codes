# FH6 EventLab Track Codes + Leaderboard

A free, self-hosted site for **doomsantosracing** EventLab share codes and community lap times.

- Codes: https://doomsantos.github.io/eventlab-codes/
- Leaderboard: https://doomsantos.github.io/eventlab-codes/leaderboard.html

## How to update track codes

Edit **`data/tracks.json`** only. You do **not** need to touch HTML/CSS/JS for new tracks or codes.

### Add a new track

```json
{
  "name": "Spa-Francorchamps",
  "variants": [
    {
      "label": "With Drivatars",
      "icon": "robot",
      "comingSoon": true
    },
    {
      "label": "Without Drivatars",
      "icon": "driver",
      "events": [
        { "laps": 5, "code": "123456789" },
        { "laps": 15, "code": "987654321" }
      ]
    }
  ]
}
```

Paste that object into the `"tracks"` array, save, commit, and push.

## Leaderboard (v1) — PC collector

Lap times come from Forza Horizon 6 **Data Out** UDP on PC.

### Timing API (local)

```powershell
python -m server --port 8787
python -m server --create-invite
```

### Run the collector

From this project folder (Python 3.10+):

```powershell
python -m collector --port 9876 --web-port 8765
```

Open **http://127.0.0.1:8765** → claim an invite → Clean laps auto-upload.

Private lab board (API): http://127.0.0.1:8080/board-lab.html (with `python -m http.server 8080` and the API running).

### Game settings

1. FH6 → **Settings → HUD and Gameplay → Data Out → On**
2. **Data Out IP Address** → your PC IP (`127.0.0.1` if FH6 is on the same PC)
3. **Data Out IP Port** → `9876` (avoid 5200–5300)
4. Allow UDP 9876 through Windows Firewall if needed

### Submit a lap

1. Enter your **display name** and select the **track**
2. Click **Save settings**
3. Drive an EventLab event — when a lap completes, the UI shows **Lap ready**
4. Click **Save lap** (keeps best time per name + track + Class/PI, e.g. `A 699`)
5. Click **Export to site JSON** → writes `data/leaderboard.json`
6. Commit and push so the public leaderboard updates

```powershell
python -m collector --export-only
git add data/leaderboard.json
git commit -m "Update leaderboard times"
git push
```

### Notes

- Ranked by **track**, then **Class/PI** (`A 699`)
- Assists are not recorded
- Xbox support / auto track detect come later

## Preview the website locally

```powershell
python -m http.server 8080
```

Visit http://localhost:8080 and http://localhost:8080/leaderboard.html

## Features

- Nested track → With/Without Drivatars → lap codes (tap to copy)
- Public leaderboard filtered by track and Class/PI
- PC Data Out collector with local SQLite + JSON export

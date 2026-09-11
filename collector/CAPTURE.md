# Albert Park capture protocol

Do this **before** more leaderboard polish. Labeled captures unlock track matching and pause-vs-rewind detection.

## Priority

1. Capture labeled Albert Park laps (this doc)
2. Build a simple matcher from those files
3. Then resume public board / multiplayer submit

## How many laps

| Label | Count | What to do on that lap |
|-------|------:|------------------------|
| `clean` | **12** | Full lap, no pause, no rewind |
| `paused` | **10** | Pause once mid-lap (2–5 sec), resume, finish. No rewind |
| `rewound` | **10** | Rewind once mid-lap, resume, finish. No pause |
| Mixed / messy | 0 for now | Skip — labels must be pure |

**Total: ~32 laps** on Albert Park is enough for a first verification model.

Same car/class is fine. Variety later helps; purity of the label matters more now.

## Collector steps

1. Restart collector, open http://127.0.0.1:8765
2. Set display name + track **Albert Park**
3. Drive one behaviour per lap
4. In the session list, set **Your label**
5. Tick the lap(s) → **Save captures**
6. Files land in `collector/captures/albert-park/*.json`

Each file stores path samples (x/y/z) plus every UDP gap with duration and position jump on resume.

## What we learn from that

- **Track ID:** clean paths become the Albert Park reference shape
- **Pause vs rewind:** both create gaps; rewind should show a larger backward position jump on resume, pause should resume near the same place

## After you hit the counts

Tell me and we’ll build the first auto-classifier from `collector/captures/albert-park/`.

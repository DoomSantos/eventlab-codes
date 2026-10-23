# Albert Park capture protocol

## Status

| Batch | Result |
|-------|--------|
| 1 | 12 clean / 10 paused / 10 rewound — track fingerprint built |
| 2 | 5 paused / 5 rewound with gap events — **pause vs rewind classifier 10/10** |

## What works now

- **Track match:** clean Albert Park paths → `data/fingerprints/albert-park.json`
- **Time Attack start:** offset-start paths → `data/fingerprints/albert-park-time-attack-start.json`  
  Rebuild: `python -m collector.build_ta_start_fingerprint`  
  Live collector: first-lap offset match arms a **TA session**; later laps inherit Mode Time Attack until a new non-matching lap 1  
  Supports multiple tracks via `data/fingerprints/*-time-attack-start.json` (Monza uses front/rear slot variants; Junior vs Full share pits and are separated by an 800 m layout window; Monaco has multi-slot pit variants; Top Gear uses soft runway corridors on the full-lap fingerprint)
- **Full-lap track fingerprints:** `python -m collector.build_track_fingerprint --track "…"`. Soft zones auto-detected from wide training corridors.
- **Integrity:**
  - no meaningful gaps → `clean`
  - gaps + jump ≤ ~8 m → treated as pause → `clean` (no competitive advantage)
  - gaps + jump ≥ ~25 m mid-lap → `rewound`
  - pre-start spawn teleports (lap timer under ~1 s) and prior-attempt noise are ignored
  - event restart (lap timer drops back to ~0) starts a fresh path segment so menu/load jumps don’t poison the next lap
- Verify with: `python -m collector.verify`

## Collector

1. Prefer `start-test-collector.bat` (source build) so captures land in `collector/captures/`
2. Driver UI: http://127.0.0.1:8765 · Research tools: http://127.0.0.1:8765/?lab=1
3. In lab mode: set the **track dropdown first**, label **Time Attack**, then **Save path captures** → `collector/captures/<track-slug>/`
4. Session status shows Clean / Rewound; Time Attack when offset-start matches
5. For TA research: restart event between samples so each lap begins at the offset start
6. Brands Hatch GP vs Indy share pit — treat like Monza: record each layout separately; builder uses a **2 km** layout window (they stay together ~1.4 km)


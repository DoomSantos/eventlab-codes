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
  Live collector auto-tags matching laps as mode `time_attack`
- **Integrity:**
  - no gaps → `clean`
  - gaps + jump ≤ ~8 m → `paused`
  - gaps + jump ≥ ~25 m → `rewound`
- Verify with: `python -m collector.verify`

## Collector

1. Prefer `start-test-collector.bat` (source build) so captures land in `collector/captures/`
2. http://127.0.0.1:8765
3. Label + **Save path captures** → `collector/captures/albert-park/`
4. Session **Auto** column shows Clean / Paused / Rewound; **Mode** shows Time Attack when offset-start matches
5. For TA research: restart event between samples so each lap begins at the offset start

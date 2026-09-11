# Albert Park capture protocol

## Status

| Batch | Result |
|-------|--------|
| 1 | 12 clean / 10 paused / 10 rewound — track fingerprint built |
| 2 | 5 paused / 5 rewound with gap events — **pause vs rewind classifier 10/10** |

## What works now

- **Track match:** clean Albert Park paths → `data/fingerprints/albert-park.json`
- **Integrity:**
  - no gaps → `clean`
  - gaps + jump ≤ ~8 m → `paused`
  - gaps + jump ≥ ~25 m → `rewound`
- Verify with: `python -m collector.verify`

## Collector

1. http://127.0.0.1:8765
2. Label + Save captures → `collector/captures/albert-park/`
3. Session **Auto** column now shows Clean / Paused / Rewound from gap jumps

# Albert Park capture protocol

## Batch 1 status: complete

- 12 clean / 10 paused / 10 rewound captured
- Track fingerprint built: `data/fingerprints/albert-park.json`
- All clean laps match Albert Park (~2–3m average path error)

## Gap / rewind note

Batch 1 stored **no gap events** because pause/rewind briefly cleared `IsRaceOn` and the detector hard-reset. That is fixed now.

## Batch 2 (needed for pause vs rewind)

Only these extras, with the **restarted** collector:

| Label | Extra laps |
|-------|------------:|
| `paused` | **5** |
| `rewound` | **5** |

One behaviour per lap. After save, check the session list shows **Gaps > 0** (or open the JSON and confirm `"gaps": [...]` is not empty).

## Collector steps

1. Open http://127.0.0.1:8765
2. Track = Albert Park
3. Drive → label → Save captures
4. Files go to `collector/captures/albert-park/`

When batch 2 is done, we can finish Clean / Paused / Rewound classification.

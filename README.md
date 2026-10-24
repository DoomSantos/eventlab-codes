# DoomSantos Racing — Time Attack

Timing for Forza Horizon 6 **Time Attack** EventLabs (PC or Xbox Series X|S).

- [Track Codes](https://doomsantos.github.io/eventlab-codes/)
- [Time Attack](https://doomsantos.github.io/eventlab-codes/leaderboard.html)
- [Live Timing](https://doomsantos.github.io/eventlab-codes/live-timing.html)
- [Leaderboards](https://doomsantos.github.io/eventlab-codes/leaderboards.html)

## What it is

Drive the official Time Attack events. A Windows collector reads Forza **Data Out**, spots the track from the offset pit start, and uploads **Clean** laps as you cross the line. Xbox players run the collector on a PC or laptop on the same home network.

Regular EventLab Track Codes stay for fun. They do not count on Live Timing or Leaderboards.

- **Live Timing** — best Clean lap **today (AEST)** per driver, plus who’s on a Time Attack event right now
- **Leaderboards** — one best Clean lap per driver × track × class
- Assists are not recorded
- Paused and rewound laps are not ranked

## Windows collector

Download: **[DSR-Lap-Collector.zip](https://github.com/DoomSantos/eventlab-codes/releases/latest/download/DSR-Lap-Collector.zip)**

1. Unzip anywhere on a **Windows PC** and run `DSR-Lap-Collector.exe`. If Windows SmartScreen appears: **More info → Run anyway**.
2. Leave that window open. A browser opens [http://127.0.0.1:8765](http://127.0.0.1:8765) — follow **Setup** on that page (first launch asks you to claim with the invite you were sent).
3. Forza Horizon 6 → Settings → HUD and Gameplay → **Data Out → On**
   - Port: `9876` (avoid 5200–5300)
   - **PC (game on this computer):** IP `127.0.0.1`
   - **Xbox Series X|S (or another PC on the same network):** IP = the collector PC address shown on the Setup page. Same home network, not guest Wi‑Fi. Allow UDP `9876` through Windows Firewall on the collector PC.
4. Load a **Time Attack** EventLab from the pit / offset grid and drive. Status should read **Game connected**. Clean times upload on their own.

If something fails, use **Troubleshooting** on the collector page.

One collector window at a time (close SimHub if it is also listening). If you switch layouts (for example full Monza vs Junior Course), quit the event and load the other one so the session can reset.

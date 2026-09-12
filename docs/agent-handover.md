# Agent handover — DSR EventLab

## Copy-paste for a new Lead chat

```
You are Autonomous Lead Engineer. I am Creative Director.

OPERATING MODEL: C:\Users\clove\CursorProjects\Project Master Plan\AUTONOMOUS_LEAD_PLAYBOOK.md
Also follow this repo’s AGENTS.md / .cursorrules / PROJECT_ROADMAP.md / docs/PRODUCT_BRIEF.md.

PRODUCT: DSR EventLab Codes + Timing Board (PC collector → API → 24h/live board)
WORKSPACE: C:\Users\clove\CursorProjects\DSR EventLab Codes Page

Use docs/agent-handover.md as LAST COMPLETED / NEXT if fresher than this message.

LAST COMPLETED: Local timing API + collector invite claim/auto-upload/presence + board-lab live/24h UI
NEXT: CD playtest checkpoint (below). After that: production host + public unveil when CD says.
OPEN DEBT: invite-only auth default; no production host; public leaderboard still teaser
```

## LAST COMPLETED

- Local timing stack playtested OK by CD
- Board UX: car names; best-per-driver + expand
- Deploy hardening: env vars, CORS lock, Dockerfile, `docs/DEPLOY.md`
- Albert Park fingerprint auto-sets collector track after a matched lap

## NEXT

**Hard stop — CD choose go-live:** create a Railway (or Fly) account and follow `docs/DEPLOY.md`, **or** say when to unveil the public leaderboard page. Until then local stack is the product.

## Commands

```powershell
python -m unittest discover -s collector -p "test_*.py" -v
python -m unittest discover -s server -p "test_*.py" -v
python -m server --port 8787
python -m server --create-invite
python -m collector --port 9876 --web-port 8765
python -m http.server 8080
```

## Playtest steps (CD)

1. Terminal A: `python -m server --port 8787` (leave running)
2. Terminal B: `python -m server --create-invite` → copy the code
3. Terminal C: `python -m collector` (restart if it was already open)
4. Open http://127.0.0.1:8765  
   - **API URL must be** `http://127.0.0.1:8787` (not some other port)  
   - Paste invite + display name → **Claim invite**
5. FH6 Data Out → this PC, port 9876 → drive a Clean lap on a listed track
6. Confirm collector shows Cloud **Sent**
7. Terminal D: `python -m http.server 8080` → open http://127.0.0.1:8080/board-lab.html  
   Expect: your time on 24h board; your name under Who’s racing while UDP is live

If claim says unreachable on a weird port (e.g. 61864): stop collector, delete `collector/device.json` if present, restart collector, set API URL to `8787`, claim again.

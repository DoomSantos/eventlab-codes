# Future: Microsoft / Xbox OAuth (deferred)

**Status:** Not building now. CD asked to keep this noted (2026-09-13).  
**Current auth:** invite → device token; free-text display name.

## What “Microsoft OAuth” usually means here

1. **MSA only** — Sign in with a personal Microsoft account (login identity).
2. **MSA + Xbox Live exchange** — same OAuth, then Xbox user token → XSTS → **gamertag / XUID** (what a racing board usually wants).

Official Xbox website flow (title sites):  
https://learn.microsoft.com/en-us/gaming/gdk/docs/services/fundamentals/s2s-auth-calls/service-authentication/live-website-authentication

Typical app registration: Entra ID, **Personal Microsoft accounts only**, scopes `xboxlive.signin` (+ optional `xboxlive.offline_access`).

## Pros (for DSR)

- Stable identity (XUID) and real gamertag on the board  
- Familiar “Sign in with Microsoft/Xbox” UX  
- Less invite churn for name/PC changes (if invites are dropped or only used as a gate)  
- Stronger anti-spoof than free-text names  
- No passwords stored on our side; Microsoft handles 2FA  

## Cons (for DSR)

- Large build: Entra app, HTTPS callbacks, token refresh, Xbox token chain  
- Does **not** replace PC collector / Data Out — only identifies the person  
- GitHub Pages is static; OAuth callback needs **Railway (or similar) backend**  
- Collector is an exe — needs browser link or device-code flow  
- ToS/privacy care for third-party Xbox identity use  
- Shared PCs / wrong MSA vs “racing persona”  
- Ops: secrets, rotation, Microsoft flow changes  
- Open OAuth without a gate = spam risk; OAuth ≠ lap integrity  

## Recommended future shape (when CD revisits)

**Invite (or allowlist) + optional Xbox link** — keep who-can-join under CD control; OAuth locks the public name to gamertag/XUID.

Do **not** treat OAuth as a substitute for Clean/Rewound integrity or time-attack start detection.

## Sensible milestone to reopen

Public timing unveil + time-attack EventLab events solid → then “Sign in with Xbox to claim board name,” still optionally behind invites.

## Related product notes

- Product brief currently locks: Xbox / MSA OAuth **not for this phase** (`docs/PRODUCT_BRIEF.md`).  
- Collector + Railway invite auth remains the live path.

# FH6 EventLab Track Codes

A free, self-hosted landing page for **doomsantosracing** EventLab share codes — same nested track → race type → laps layout as the Notion page, without a Notion subscription.

## How to update (the easy part)

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

Paste that object into the `"tracks"` array, save, then push (or re-upload) to your host. The page picks it up automatically.

### Mark something as coming soon

Use `"comingSoon": true` and omit `events`.

### Change Instagram / page title

Edit the top-level fields in `data/tracks.json`: `title`, `tagline`, `instagram`.

## Preview locally

Because the page loads JSON with `fetch`, open it through a tiny local server (double-clicking `index.html` may block the data file).

**PowerShell (from this folder):**

```powershell
python -m http.server 8080
```

Then visit http://localhost:8080

## Free hosting (recommended: GitHub Pages)

1. Create a GitHub account (free) if you don’t have one.
2. Create a new public repository (e.g. `eventlab-codes`).
3. Push this project to that repo.
4. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**.
5. Choose branch `main` (or `master`), folder `/ (root)`, Save.
6. Your site will be at:
   `https://YOUR_USERNAME.github.io/eventlab-codes/`

After that, every time you edit `data/tracks.json` and push, the live page updates in a minute or two.

### Other free options

| Host | Notes |
|------|--------|
| [Cloudflare Pages](https://pages.cloudflare.com/) | Free, fast CDN; connect the same GitHub repo |
| [Netlify](https://www.netlify.com/) | Free tier; drag-and-drop the folder or connect Git |
| [Vercel](https://vercel.com/) | Free tier; connect Git |

No paid plan needed for a static page like this.

## Features

- Nested expand/collapse (track → With/Without Drivatars → lap codes)
- Tap any code to copy
- Mobile-friendly dark racing layout
- All content driven by one JSON file

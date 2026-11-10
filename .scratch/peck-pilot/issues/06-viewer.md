# 06 Viewer UI

Status: resolved
Blocked by: 05

Spec: App → Frontend.

## What
Vite + TypeScript + three.js, one screen:
- Part dropdown and file upload
- Faces colored by label, with a legend
- click a Face to see its label and confidence
- side panel: Machining Features, Operations, Unplanned Features, G-code with a download button
- clicking a Face highlights its Operation, and clicking an Operation highlights its Faces

## Acceptance
Checked in a real browser:
- a bundled Part loads
- an upload works
- an invalid upload shows the error
- linked highlighting works in both directions

## Comments

**2026-11-10:** Done.
- Added `web/`: Vite, TypeScript and three.js, with no framework.
- `npm run build` produces `web/dist`, which FastAPI serves at `/`. Run `uvicorn peck_pilot.api:app --port 8765` and open http://127.0.0.1:8765. Port 8000 is taken by another local app.
- In dev, `npm run dev` proxies `/api` to :8765.

Checked in a real browser: headless Brave driven by puppeteer-core. The script is in the session scratchpad and isn't committed. It passes 12 of 12 checks:
- a bundled Part loads, with canvas, legend and G-code
- clicking a feature row highlights its Operations, and clicking an Operation row highlights its feature
- clicking the model selects a Face
- a junk upload shows a clear error
- the plate upload plans 3 holes and 6 Operations
- no horizontal scroll at 390 px
- no unexpected console errors

Fixes found by the check: grid overflow at phone width, camera framing on narrow screens, a favicon 404, and a plural ("1 holes").

The Claude in Chrome tools weren't available in this session, which is why headless Brave was used. The 3D view hasn't been looked at by a human yet.

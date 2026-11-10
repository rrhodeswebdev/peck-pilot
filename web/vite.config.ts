import { defineConfig } from "vite";

// Dev: `npm run dev` with `uvicorn peck_pilot.api:app` on :8765. Demo: `npm run build`, FastAPI serves dist/.
export default defineConfig({ server: { proxy: { "/api": "http://127.0.0.1:8765" } } });

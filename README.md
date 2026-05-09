# ULTIMATE OBS LOWER THIRDS SYSTEM

Version: 2.2 (GUI Local Server Update)

## Description

Professional browser-based Lower Thirds system for OBS with dynamic panels, custom fonts, logos, auto-save, and advanced animations.

## Key Features

- Logo support via file browse or URL/path
- Custom fonts and text colors
- Dynamic panels (add/remove/reorder)
- Auto-save in browser storage
- 11+ animation styles
- Global settings to apply across all panels

---

## Recommended Mode (Firefox + OBS Compatible)

Use the local HTTP server (do not use `file:///` links).

### Option A - GUI (recommended)

Run:

- `iniciar_servidor_gui.cmd`

This opens a desktop interface where you can:

- Start/stop the server
- Copy the panel URL
- Copy the source URL

### Option B - Terminal only

Run:

- `iniciar_servidor_local.bat`

---

## OBS Setup

When the local server is running, use these URLs:

- Panel (Dock): `http://127.0.0.1:5500/obs_control_panel.html`
- Source (Browser Source): `http://127.0.0.1:5500/obs_lower_thirds_source.html`

### Step 1: Add Browser Source

1. Open OBS Studio
2. Add a new **Browser** source
3. Name it `Lower Thirds`
4. URL: `http://127.0.0.1:5500/obs_lower_thirds_source.html`
5. Width: `1920`
6. Height: `1080`
7. Keep Custom CSS empty

### Step 2: Add Custom Dock

1. Go to **View > Docks > Custom Browser Docks...**
2. Dock Name: `Lower Thirds Control`
3. URL: `http://127.0.0.1:5500/obs_control_panel.html`
4. Click **Apply**

---

## Quick Helper Scripts

- `iniciar_servidor_gui.cmd`: opens desktop GUI and starts server
- `iniciar_servidor_local.bat`: starts server in terminal
- `abrir_painel_e_source.bat`: starts server if needed and opens both URLs in browser

---

## Notes

- Keep the local server running while using OBS.
- If port `5500` is in use, close the other process using that port.

---

Created by: [Your Name/Antigravity]

Happy Streaming!

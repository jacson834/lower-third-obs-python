ULTIMATE OBS LOWER THIRDS SYSTEM
Version: 2.3 (Modern GUI + Remote Security Update)

DESCRIPTION
Professional browser-based Lower Thirds system for OBS with dynamic panels, custom fonts, logos, auto-save, advanced animations, remote control via phone, and secure access.

KEY FEATURES
- Logo support via file browse or URL/path
- Custom fonts and text colors
- Dynamic panels (add/remove/reorder)
- Auto-save in browser storage
- 11+ animation styles
- Global settings to apply across all panels
- Remote control from phone (same network)
- QR Code access for mobile control
- Password-protected remote panel with rate limiting and session expiration

--------------------------------------------------------------------------------

RECOMMENDED MODE (FIREFOX + OBS COMPATIBLE)
Use local HTTP server mode (do not use file:/// links).

Option A - Modern GUI (recommended)
1) Install dependencies (first run only):
   - instalar_gui_moderno.cmd
2) Start modern GUI:
   - iniciar_servidor_gui_moderno.cmd

Modern GUI includes:
- Start/stop server
- OBS local URLs and mobile remote URL
- Copy buttons for each URL
- QR Code for mobile panel
- Remote password field with show/hide toggle
- Security settings (token expiration, max attempts, lock time)
- Remote client connection status

Option B - Classic GUI
- iniciar_servidor_gui.cmd

Classic GUI also supports:
- QR Code
- Remote password
- Security settings

Option C - Terminal only
- iniciar_servidor_local.bat

--------------------------------------------------------------------------------

OBS SETUP
When the local server is running, use these URLs:
- Panel (Dock): http://127.0.0.1:5500/obs_control_panel.html
- Source (Browser Source): http://127.0.0.1:5500/obs_lower_thirds_source.html

Step 1: Add Browser Source
1. Open OBS Studio
2. Add a new Browser source
3. Name it Lower Thirds
4. URL: http://127.0.0.1:5500/obs_lower_thirds_source.html
5. Width: 1920
6. Height: 1080
7. Keep Custom CSS empty

Step 2: Add Custom Dock
1. Go to View > Docks > Custom Browser Docks...
2. Dock Name: Lower Thirds Control
3. URL: http://127.0.0.1:5500/obs_control_panel.html
4. Click Apply

--------------------------------------------------------------------------------

MOBILE REMOTE CONTROL (PHONE)
1. Keep PC and phone on the same Wi-Fi network
2. Open GUI and scan the QR Code with your phone
3. Enter remote password (if enabled)
4. Control lower thirds from phone; output appears in OBS on PC

--------------------------------------------------------------------------------

SECURITY
Remote panel security includes:
- Password authentication for remote clients
- Session token required for remote panel access
- Token expiration (configurable)
- Login rate limiting by IP (configurable)
- Temporary lockout after too many failed attempts (configurable)

Default values:
- Token expiration: 720 minutes (12h)
- Max attempts: 5
- Lock time: 120 seconds

--------------------------------------------------------------------------------

HELPER SCRIPTS
- instalar_gui_moderno.cmd: installs PySide6, qrcode, pillow
- iniciar_servidor_gui_moderno.cmd: opens modern GUI
- iniciar_servidor_gui.cmd: opens classic GUI
- iniciar_servidor_local.bat: starts server in terminal
- abrir_painel_e_source.bat: starts server if needed and opens both URLs in browser

--------------------------------------------------------------------------------

NOTES
- Keep the server running while using OBS.
- If port 5500 is in use, close the conflicting process.
- If phone access fails, allow port 5500 in Windows Firewall (private network).

--------------------------------------------------------------------------------
Created by: [Your Name/Antigravity]
Happy Streaming!

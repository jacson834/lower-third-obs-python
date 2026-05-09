ULTIMATE OBS LOWER THIRDS SYSTEM
Version: 2.1 (HTTP Local Compatibility Update)

DESCRIPTION
Transform your stream with this professional, browser-based Lower Thirds system. Includes logo support, custom fonts, dynamic panels, auto-save, and advanced animations.

Key Features:
- Logo Support: Add logos/icons via file browse or URL/path, with size and position controls.
- Custom Fonts: Choose from multiple fonts to match your brand.
- Dynamic Panels: Add/remove lower thirds as needed.
- Auto-Save: Settings are saved automatically in the browser.
- 11+ Animations: Slide, Bounce, Fade, Swing, Flip, Elastic, Zoom, and more.
- Global Settings: Apply visual/animation presets to all panels.

--------------------------------------------------------------------------------

IMPORTANT (RECOMMENDED MODE)
To ensure compatibility with Firefox and OBS Browser Source, use HTTP local mode instead of file:///.

Use the included script:
- iniciar_servidor_local.bat

This serves the folder at:
- http://127.0.0.1:5500

--------------------------------------------------------------------------------

INSTALLATION GUIDE (HTTP LOCAL MODE)

Step 1: Start Local Server
1. Double-click: iniciar_servidor_local.bat
2. Keep the terminal window open while using OBS.

Step 2: Add Source to OBS
1. Open OBS Studio.
2. Add a new "Browser" Source.
3. Name it "Lower Thirds".
4. URL:
   http://127.0.0.1:5500/obs_lower_thirds_source.html
5. Set Width: 1920 | Height: 1080
6. Clear "Custom CSS" (leave empty)
7. Click OK.

Step 3: Dock the Control Panel
1. In OBS, go to View > Docks > Custom Browser Docks...
2. Dock Name: Lower Thirds Control
3. URL:
   http://127.0.0.1:5500/obs_control_panel.html
4. Click Apply.

Quick Test Script:
- abrir_painel_e_source.bat
- Opens both URLs in your default browser and starts the server if needed.

--------------------------------------------------------------------------------

HOW TO USE

1. Basic Controls
- Name & Title: Enter your text.
- Show/Hide: Toggle visibility instantly.
- Move: Use up/down arrows to reorder panels.
- Delete/Add: Remove or create panels on demand.

2. Branding (Logos & Fonts)
- Click the gear icon for Advanced Settings.
- Enable Logo, choose image, set size/position.
- Set font, text sizes, and text colors.

3. Global Settings
- Use top panel settings to apply style/animation defaults to all lower thirds.

--------------------------------------------------------------------------------
Created by: [Your Name/Antigravity]
Happy Streaming!

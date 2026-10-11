# Delhi Smart City - Geospatial Map Module

Base map module for the Delhi Smart City project, implemented using **Leaflet** and **OpenStreetMap** tiles.

---

## Features & Implementation Specifications

* **Mapping Engine:** Leaflet (v1.9.4) with standard OpenStreetMap raster tile layer (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`).
* **Geographic Center:** Centred specifically on **Delhi, India** (`28.6139° N, 77.2090° E`).
* **Initial Zoom Level:** Sensible city-level zoom (`11x`), framing the National Capital Territory of Delhi comfortably.
* **Responsive Layout:** Adaptive design scaling seamlessly across desktop, laptop, tablet, and mobile screens. Includes dynamic viewport resize observers (`map.invalidateSize()`).
* **Explicit Dimensions:** `#map` container has explicit CSS height (`calc(100vh - 110px)` with a minimum of `450px`), ensuring it renders without collapsing.
* **Controls & Attributions:** Built-in Leaflet zoom controls (`+` / `-`) enabled, alongside required OpenStreetMap legal attribution.
* **Minimal Clean Baseline:** Pure base map without heat markers, monsoon markers, GPS tracking, or AI layers (ready for future feature increments).

---

## File Structure

```text
delhi smart city/
├── index.html       # Semantic HTML5 shell with map container & status header
├── styles.css       # Responsive design system & explicit map dimensions
├── map.js           # Leaflet map initialization, event handlers, & resize logic
├── server.ps1       # Built-in PowerShell HTTP server (zero external dependencies)
├── package.json     # Project metadata and local preview scripts
└── README.md        # Documentation and running guide
```

---

## Exact Steps to Start and View the Website

### Option 1: Direct Browser Launch (Fastest & Simplest)
1. Open Windows File Explorer.
2. Navigate to:
   ```text
   C:\Users\biswa\OneDrive\Documents\delhi smart city
   ```
3. Double-click **`index.html`** (or right-click > **Open with** > **Google Chrome** / **Microsoft Edge**).
4. The map will load immediately, centered on Delhi.

### Option 2: Run Built-In Local Web Server (PowerShell)
Because neither Node.js nor Python is installed on your Windows machine, a native PowerShell server script is included that uses Windows' built-in `.NET` runtime:
1. Open PowerShell in this folder:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\server.ps1
   ```
2. Your default browser will automatically open to `http://localhost:8080/index.html`.
3. Press `Ctrl + C` in PowerShell to stop the server when done.

### Option 3: Command Line Direct Browser Launch
Run the following single command in PowerShell from the project folder:
```powershell
Start-Process "index.html"
```

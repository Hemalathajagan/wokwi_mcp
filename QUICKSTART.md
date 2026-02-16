# Quick Start Guide

AI-powered fault detection for Wokwi circuits and KiCad designs. Supports Arduino, ESP32, Raspberry Pi Pico, ATtiny85, STM32, wireless modules, 14 popular libraries, and KiCad schematic/PCB analysis.

## Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI API key ([platform.openai.com](https://platform.openai.com/api-keys))
- A Google OAuth Client ID (optional, for Google sign-in)

## 1. Clone and set up Python environment

```bash
cd my_mcp
python -m venv env
```

Activate the virtual environment:

```bash
# Windows
env\Scripts\activate

# macOS/Linux
source env/bin/activate
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

## 2. Configure environment variables

### Backend — `backend/.env`

```env
# Required
JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_urlsafe(32))">
OPENAI_API_KEY=sk-your-openai-api-key

# Optional (for cheaper model)
OPENAI_MODEL=gpt-4o-mini

# Optional (for Google sign-in)
GOOGLE_CLIENT_ID=your-id.apps.googleusercontent.com

# Database (default is fine)
DATABASE_URL=sqlite+aiosqlite:///./wokwi_analyzer.db
```

### Frontend — `frontend/.env`

```env
# Only needed if using Google sign-in
VITE_GOOGLE_CLIENT_ID=your-id.apps.googleusercontent.com
```

## 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## 4. Start the servers

**Terminal 1 — Backend:**

```bash
# Windows
env\Scripts\python.exe backend\server.py --mode api

# macOS/Linux
python backend/server.py --mode api
```

Backend starts at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Frontend starts at `http://localhost:5173`.

## 5. Use the app

### Wokwi Mode (default)

1. Open `http://localhost:5173`
2. Sign up with email/password (or Google if configured)
3. Select **Wokwi** mode (default)
4. Paste a public Wokwi project URL (e.g., `https://wokwi.com/projects/123456`)
5. *(Optional)* Add a **Design Description** — describe what your circuit should do and specific pin assignments (see below)
6. Click **Analyze** and wait for the AI-powered report
7. Browse **Fault Report**, **Circuit**, **Code**, and **Fix Suggestions** tabs

### KiCad Mode

1. Click the **KiCad** mode toggle at the top
2. Drag and drop your KiCad files (`.kicad_sch`, `.kicad_pcb`, `.kicad_pro`) or click to browse
3. *(Optional)* Add a **Design Description** — describe your circuit's purpose and pin connections
4. Click **Analyze KiCad Project**
5. Browse **Fault Report**, **Project Info**, and **Fix Suggestions** tabs

> **Note:** Upload at least one `.kicad_sch` or `.kicad_pcb` file. KiCad 6+ format is required.

### Design Description (Intent-Aware Analysis)

The optional **Design Description** textarea helps the AI detect "wrong but electrically valid" wiring — cases where your circuit works but doesn't do what you intended.

**How to use it:**
- Describe what your circuit should do
- Include specific pin assignments
- Mention expected behavior and sensor/actuator roles

**Examples:**
- "ESP32 reads DHT22 sensor on GPIO4, controls relay on GPIO5, OLED on I2C (SDA=21, SCL=22)"
- "Arduino Uno with 3 LEDs on pins 9-11, push button on pin 2, buzzer on pin 8"
- "ATmega328P with 16MHz crystal, 3 LEDs on PB0-PB2, UART to GPS module on PD0/PD1"
- "STM32F103 driving stepper motor via A4988: STEP=PA0, DIR=PA1, EN=PA2"

The AI compares your actual wiring/code against your stated intent and flags mismatches as **Intent Mismatch** faults, even if the circuit is electrically valid.

### History & Profile

- Check **History** to see past analyses (with Wokwi/KiCad type badges)
- Click **View Report** on any entry to see the full report
- Visit **Profile** to change your password

## What gets analyzed?

### Wokwi Analysis (20+ checks)

**Supported Boards:**
Arduino Uno, Mega, Nano, ESP32 DevKit V1, Raspberry Pi Pico, ATtiny85, STM32 Bluepill

**Supported Wireless Modules:**
HC-05, HC-06 (Bluetooth), HM-10 (BLE), ESP-01 (WiFi), nRF24L01 (RF), IR receiver/LED

**Libraries Validated (14):**
Servo, LiquidCrystal, LiquidCrystal_I2C, Wire, SPI, Adafruit_NeoPixel, DHT, SoftwareSerial, RF24, IRremote, Stepper, AccelStepper, Keypad, WiFi (ESP32)

**Checks Performed:**
- Wiring faults (missing connections, wrong pins, polarity errors)
- Power issues (voltage mismatches, current budget, 3.3V/5V conflicts)
- Code bugs (missing init calls, wrong pin modes, library misuse)
- Code-circuit cross-reference (pin in code but not wired, and vice versa)
- Board-specific issues (ESP32 flash pins, input-only pins, ATtiny pin limits)
- Wireless issues (TX/RX crossover, baud rate, SPI mapping, serial conflicts)
- Design intent mismatches (when description provided)

### KiCad Analysis (14 ERC + 6 DRC checks)

**Schematic Checks (ERC):**
- Unconnected pins, duplicate references, missing values
- PWR_FLAG checks, single-pin nets (label typos)
- Voltage mismatches (3.3V IC on 5V rail)
- Decoupling capacitors, LED resistors
- Pin function mismatch, polarity checks
- UART crossover, pin type conflicts
- Footprint pad mismatch, library symbol issues

**PCB Checks (DRC):**
- Unrouted nets, trace width below minimum
- Via drill size, clearance violations
- Power trace width analysis
- Schematic-PCB component sync

**AI-Powered Deep Analysis:**
- Signal integrity, thermal concerns, EMC issues
- Cross-references schematic against PCB layout
- Compares design against user's stated intent

## Running as MCP Server

For use with Claude Desktop or other MCP clients:

```bash
python backend/server.py --mode mcp
```

This runs over stdio. Add to your MCP client config:

```json
{
  "mcpServers": {
    "circuit-analyzer": {
      "command": "python",
      "args": ["path/to/backend/server.py", "--mode", "mcp"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key"
      }
    }
  }
}
```

**Available MCP Tools:**

| Tool | Description |
|------|-------------|
| `analyze_wokwi_project(url)` | Full Wokwi fault analysis |
| `check_wiring(diagram_json)` | Wiring-only analysis |
| `check_code(sketch_code, diagram_json)` | Code-only analysis |
| `suggest_fix(fault_report, diagram_json, sketch_code)` | Wokwi fix generation |
| `analyze_kicad_project(schematic, pcb, project)` | Full KiCad analysis |
| `check_kicad_schematic(schematic)` | Schematic ERC analysis |
| `check_kicad_pcb(pcb, schematic)` | PCB DRC analysis |
| `suggest_kicad_fix(fault_report, schematic, pcb)` | KiCad fix generation |

## Getting a Google OAuth Client ID (optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a project → **APIs & Services** → **Credentials**
3. **Create Credentials** → **OAuth client ID** → **Web application**
4. Add `http://localhost:5173` to **Authorized JavaScript origins**
5. Copy the Client ID into both `backend/.env` and `frontend/.env`

## Deploying to Production (Vercel + Render)

### Backend — Render

1. Push your code to a **GitHub repository**
2. Go to [render.com](https://render.com) → **New** → **Web Service**
3. Connect your GitHub repo and set:
   - **Root Directory:** `backend`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Add these **Environment Variables** in the Render dashboard:
   | Key | Value |
   |-----|-------|
   | `JWT_SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
   | `OPENAI_API_KEY` | Your OpenAI API key |
   | `OPENAI_MODEL` | `gpt-4o-mini` |
   | `GOOGLE_CLIENT_ID` | Your Google OAuth Client ID (if using Google sign-in) |
   | `ALLOWED_ORIGINS` | `https://your-app.vercel.app` (your Vercel frontend URL) |
   | `DATABASE_URL` | `sqlite+aiosqlite:///./wokwi_analyzer.db` |
5. Deploy — note down the Render URL (e.g., `https://your-api.onrender.com`)

> **Note:** Render free tier has ephemeral disk — the SQLite DB resets on each deploy. For persistent data, use the paid tier ($7/mo) or switch to PostgreSQL.

### Frontend — Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import the same GitHub repo and set:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Add **Environment Variables**:
   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | Your Render backend URL (e.g., `https://your-api.onrender.com`) |
   | `VITE_GOOGLE_CLIENT_ID` | Your Google OAuth Client ID (if using Google sign-in) |
4. Deploy

### Post-Deploy Checklist

- Update `ALLOWED_ORIGINS` on Render to include your actual Vercel URL
- If using Google OAuth, add your Vercel URL to **Authorized JavaScript origins** in Google Cloud Console
- Test signup, login, analysis (both modes), and history to verify everything works

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `OPENAI_API_KEY not set` | Add your key to `backend/.env` |
| Port 8000 in use | `--port 8001` flag, update Vite proxy in `frontend/vite.config.js` |
| `Fix suggestion failed` | Model may be truncating output — try `OPENAI_MODEL=gpt-4o` for better results |
| Google sign-in not working | Check Client ID matches in both `.env` files and `http://localhost:5173` is in authorized origins |
| DB schema error after update | Delete `wokwi_analyzer.db` and restart — it auto-recreates |
| CORS errors in production | Set `ALLOWED_ORIGINS` env var on Render to your Vercel frontend URL |
| API calls fail on Vercel | Check `VITE_API_URL` is set correctly (no trailing slash) |
| KiCad upload fails | Ensure files are KiCad 6+ format (`.kicad_sch`, not `.sch`) |
| Intent mismatches not detected | Add a detailed design description with specific pin assignments |

# Quick Start Guide

AI-powered fault detection for Wokwi circuits. Supports Arduino, ESP32, Raspberry Pi Pico, ATtiny85, STM32, wireless modules, and 14 popular libraries.

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

1. Open `http://localhost:5173`
2. Sign up with email/password (or Google if configured)
3. Paste a public Wokwi project URL (e.g., `https://wokwi.com/projects/123456`)
4. Click **Analyze** and wait for the AI-powered report
5. Browse **Fault Report**, **Circuit**, **Code**, and **Fix Suggestions** tabs
6. Check **History** to see past analyses
7. Click **View Report** on any history entry to see the full fault report, circuit, code, and fix suggestions
8. Visit **Profile** to change your password

## What gets analyzed?

### Supported Boards
Arduino Uno, Mega, Nano, ESP32 DevKit V1, Raspberry Pi Pico, ATtiny85, STM32 Bluepill

### Supported Wireless Modules
HC-05, HC-06 (Bluetooth), HM-10 (BLE), ESP-01 (WiFi), nRF24L01 (RF), IR receiver/LED

### Libraries Validated
Servo, LiquidCrystal, LiquidCrystal_I2C, Wire, SPI, Adafruit_NeoPixel, DHT, SoftwareSerial, RF24, IRremote, Stepper, AccelStepper, Keypad, WiFi (ESP32)

### Checks Performed
- Wiring faults (missing connections, wrong pins, polarity errors)
- Power issues (voltage mismatches, current budget, 3.3V/5V conflicts)
- Code bugs (missing init calls, wrong pin modes, library misuse)
- Code-circuit cross-reference (pin in code but not wired, and vice versa)
- Board-specific issues (ESP32 flash pins, input-only pins, ATtiny pin limits)
- Wireless issues (TX/RX crossover, baud rate, SPI mapping, serial conflicts)

## Running as MCP Server

For use with Claude Desktop or other MCP clients:

```bash
python backend/server.py --mode mcp
```

This runs over stdio. Add to your MCP client config:

```json
{
  "mcpServers": {
    "wokwi-analyzer": {
      "command": "python",
      "args": ["path/to/backend/server.py", "--mode", "mcp"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key"
      }
    }
  }
}
```

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
5. Deploy — note down the Render URL (e.g., `https://wokwi-analyzer-api.onrender.com`)

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
   | `VITE_API_URL` | Your Render backend URL (e.g., `https://wokwi-analyzer-api.onrender.com`) |
   | `VITE_GOOGLE_CLIENT_ID` | Your Google OAuth Client ID (if using Google sign-in) |
4. Deploy

### Post-Deploy Checklist

- Update `ALLOWED_ORIGINS` on Render to include your actual Vercel URL
- If using Google OAuth, add your Vercel URL to **Authorized JavaScript origins** in Google Cloud Console
- Test signup, login, analysis, and history to verify everything works

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

# Wokwi Circuit Analyzer

AI-powered circuit fault detection tool that analyzes public Wokwi projects for wiring errors, code bugs, component issues, and library misuse across multiple board platforms.

## How is this different from Wokwi Pro?

| Feature | Wokwi (Free/Pro) | Wokwi Circuit Analyzer |
|---------|-------------------|------------------------|
| Simulate & run circuits | Yes | No |
| Detect wiring faults | No | Yes |
| Detect code bugs | No | Yes |
| Cross-reference code vs circuit | No | Yes |
| AI-powered fix suggestions | No | Yes |
| Voltage/power budget checks | No | Yes |
| Wireless module validation | No | Yes |
| Library usage validation | No | Yes |
| Multi-board fault rules | No | Yes |
| Analysis history | No | Yes |
| Private projects | Yes (Pro) | N/A |
| Custom library upload | Yes (Pro) | N/A |

**Wokwi = "Run your circuit"** | **This tool = "Find what's wrong with your circuit"**

They're complementary — build on Wokwi, then paste the URL here to find faults before building the physical circuit.

## Features

- **Circuit Analysis** — Detects wiring faults, missing connections, polarity errors, and power issues
- **Code Analysis** — Finds sketch bugs and cross-references against circuit wiring
- **Library Validation** — Checks 14 popular libraries for missing init calls, wrong arguments, and common mistakes
- **Fix Suggestions** — Generates corrected code and wiring based on detected faults
- **Multi-Board Support** — Arduino (Uno/Mega/Nano), ESP32, Raspberry Pi Pico, ATtiny85, STM32 Bluepill
- **Wireless Module Support** — Bluetooth (HC-05/06, HM-10), WiFi (ESP-01), RF (nRF24L01), IR
- **Dual Mode** — Runs as a REST API (web app) or MCP server (for Claude Desktop / AI agents)
- **Authentication** — Email/password signup + Google OAuth sign-in with JWT tokens
- **Analysis History** — Stores past analyses per user with full report viewing
- **User Profiles** — Profile page with change password support

## Supported Boards

| Board | Type ID | Voltage | Key Checks |
|-------|---------|---------|------------|
| Arduino Uno | `wokwi-arduino-uno` | 5V | PWM pins, analog pins, pin limits |
| Arduino Mega | `wokwi-arduino-mega` | 5V | Extended pin range, SPI/I2C |
| Arduino Nano | `wokwi-arduino-nano` | 5V | Same as Uno with different form factor |
| ESP32 DevKit V1 | `wokwi-esp32-devkit-v1` | 3.3V | Flash pins (GPIO6-11), input-only (GPIO34-39), strapping pins, ADC2/WiFi conflict |
| Raspberry Pi Pico | `wokwi-pi-pico` | 3.3V | All GPIO PWM, 3.3V tolerance, ADC on GP26-28 |
| ATtiny85 | `wokwi-attiny85` | 5V | Only 5 usable pins, no hardware UART |
| STM32 Bluepill | `board-stm32-bluepill` | 3.3V (5V tolerant) | PA/PB/PC pins, USART mapping |

## Supported Wireless Modules

| Module | Type | Key Checks |
|--------|------|------------|
| HC-05 | Bluetooth Classic | TX/RX crossover, 3.3V RX voltage divider, baud rate |
| HC-06 | Bluetooth Classic | TX/RX crossover, 3.3V RX voltage divider, baud rate |
| HM-10 | BLE 4.0 | 3.3V only, TX/RX crossover |
| ESP-01 | WiFi (ESP8266) | 3.3V only, 300mA power draw, CH_PD pull-up |
| nRF24L01 | 2.4GHz RF | 3.3V only, SPI pin mapping, capacitor needed |
| IR Receiver | Infrared | Interrupt pin recommendation |
| IR LED | Infrared | Resistor needed, PWM pin for 38kHz |

## Library Knowledge Base (14 libraries)

The analyzer validates usage of these popular libraries:

| Library | Components | Key Checks |
|---------|-----------|------------|
| Servo | Servo motor | Missing `attach()`, angle range, PWM pin |
| LiquidCrystal | LCD (4-bit) | Missing `begin()`, pin order |
| LiquidCrystal_I2C | LCD (I2C) | Wrong I2C address, missing `backlight()` |
| Wire | I2C devices | Missing `begin()`, wrong I2C pins per board |
| SPI | SPI devices | Wrong SPI pins, missing CS setup |
| Adafruit_NeoPixel | NeoPixels | Missing `begin()`/`show()`, pixel count |
| DHT | DHT22/DHT11 | Wrong type, read frequency, NaN check |
| SoftwareSerial | BT/WiFi modules | Baud mismatch, pin order, ESP32 warning |
| RF24 | nRF24L01 | CE/CSN pins, `stopListening()` before `write()` |
| IRremote | IR receiver/LED | Old vs new API, missing `resume()` |
| Stepper | Stepper motor | Step count, direct connection, pin order |
| AccelStepper | Stepper motor | Missing `run()` in loop, speed setup |
| Keypad | Membrane keypad | Row/column mapping, pin conflicts |
| WiFi (ESP32) | ESP32 built-in | Connection wait loop, ADC2 conflict |

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy (async SQLite), OpenAI GPT-4o/4o-mini, python-jose (JWT), google-auth

**Frontend:** React 19, Vite, Axios, react-router-dom, @react-oauth/google

**MCP:** FastMCP over stdio

## Project Structure

```
my_mcp/
├── backend/
│   ├── .env                  # Secrets (JWT key, Google Client ID, OpenAI key)
│   ├── server.py             # Dual-mode server (FastAPI + MCP)
│   ├── analyzer.py           # Rule-based + AI analysis engine
│   ├── auth.py               # JWT + Google token verification
│   ├── auth_routes.py        # Auth API endpoints
│   ├── history_routes.py     # Analysis history endpoints
│   ├── config.py             # Pydantic settings
│   ├── database.py           # Async SQLAlchemy setup
│   ├── models.py             # User + AnalysisHistory models
│   ├── prompts.py            # OpenAI prompt templates
│   ├── component_knowledge.py# Board, component, wireless & library specs
│   ├── wokwi_fetch.py        # Wokwi project fetcher
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── auth/             # AuthContext, LoginPage, ProtectedRoute, UserMenu
│   │   ├── components/       # UrlInput, SummaryBar, FaultReport, CircuitViewer, CodeView, FixSuggestion
│   │   ├── pages/            # ProfilePage, HistoryPage, HistoryDetailPage
│   │   ├── api.js            # Axios client with JWT interceptors
│   │   ├── App.jsx           # Main app with routing
│   │   └── main.jsx          # Entry point with providers
│   ├── .env                  # VITE_GOOGLE_CLIENT_ID
│   ├── vercel.json           # Vercel SPA routing config
│   └── package.json
├── render.yaml               # Render deployment config
└── env/                      # Python virtual environment
```

## API Endpoints

### Public
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Email/password registration |
| POST | `/api/auth/login` | Email/password login |
| POST | `/api/auth/google` | Google OAuth login |
| POST | `/api/auth/refresh` | Refresh JWT tokens |
| GET | `/api/auth/me` | Get current user profile |
| PUT | `/api/auth/change-password` | Change password |

### Analysis (requires auth)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze` | Full project analysis (saves to history) |
| POST | `/api/check-wiring` | Wiring-only analysis |
| POST | `/api/check-code` | Code-only analysis |
| POST | `/api/suggest-fix` | Generate fix suggestions |

### History (requires auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/history` | List user's past analyses |
| GET | `/api/history/{id}` | Get full report for a history entry |
| DELETE | `/api/history/{id}` | Delete a history entry |

## MCP Tools

When running in MCP mode (`--mode mcp`), the server exposes these tools over stdio:

- `analyze_wokwi_project(wokwi_url)` — Full fault analysis
- `check_wiring(diagram_json)` — Wiring analysis
- `check_code(sketch_code, diagram_json)` — Code analysis
- `suggest_fix(fault_report, diagram_json, sketch_code)` — Fix generation

## Analysis Capabilities

### Rule-Based Checks (20+)
- Unconnected components, invalid pins, LED polarity/resistor
- Power connections (VCC/GND), servo PWM pin
- TX/RX crossover for wireless modules
- 3.3V module voltage protection
- ESP-01 power budget, nRF24L01 SPI pin mapping
- Hardware Serial pin conflict with USB
- ESP32 flash pins, input-only pins, strapping pins
- 3.3V board voltage mismatch with 5V components
- Library initialization checks
- SoftwareSerial pin cross-reference
- Wireless library vs circuit component matching

### AI-Powered Analysis
- Deep circuit analysis beyond rule-based checks
- Code bug detection with library-specific knowledge
- Cross-reference code pin usage against actual wiring
- Board-specific code issue detection (ESP32 WiFi, ATtiny limits, etc.)
- Wireless communication protocol validation

## License

MIT

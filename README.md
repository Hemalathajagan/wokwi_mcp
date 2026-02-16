# Circuit Analyzer

AI-powered circuit fault detection tool that analyzes Wokwi projects and KiCad designs for wiring errors, code bugs, component issues, and design intent mismatches across multiple board platforms.

## How is this different from Wokwi Pro?

| Feature | Wokwi (Free/Pro) | Circuit Analyzer |
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
| KiCad schematic/PCB analysis | No | Yes |
| Design intent mismatch detection | No | Yes |
| Analysis history | No | Yes |
| Private projects | Yes (Pro) | N/A |
| Custom library upload | Yes (Pro) | N/A |

**Wokwi = "Run your circuit"** | **This tool = "Find what's wrong with your circuit"**

They're complementary — build on Wokwi, then paste the URL here to find faults before building the physical circuit.

## Features

### Core Analysis
- **Circuit Analysis** — Detects wiring faults, missing connections, polarity errors, and power issues
- **Code Analysis** — Finds sketch bugs and cross-references against circuit wiring
- **Library Validation** — Checks 14 popular libraries for missing init calls, wrong arguments, and common mistakes
- **Fix Suggestions** — Generates corrected code and wiring based on detected faults

### KiCad EDA Support
- **Schematic Analysis (.kicad_sch)** — ERC checks, unconnected pins, duplicate references, power flag issues, voltage mismatches, decoupling capacitor checks, LED resistor checks, UART crossover detection, polarity verification, pin function mismatch detection
- **PCB Layout Analysis (.kicad_pcb)** — DRC checks, unrouted nets, trace width validation, via drill size checks, clearance violations, power trace width analysis
- **Schematic-PCB Cross-Reference** — Detects components in schematic but missing from PCB and vice versa
- **Drag & Drop Upload** — Upload .kicad_sch, .kicad_pcb, .kicad_pro files via drag-and-drop or file picker
- **Unified Dashboard** — Mode toggle to switch between Wokwi URL analysis and KiCad file upload

### Design Intent Analysis
- **Design Description** — Optional textarea where users describe what their circuit should do, including specific pin assignments
- **Intent Mismatch Detection** — AI compares actual wiring/code against stated intent and flags functional mismatches even if electrically valid (e.g., sensor on GPIO5 instead of GPIO4)
- **Works in Both Modes** — Available for both Wokwi and KiCad analysis

### Platform Support
- **Multi-Board Support** — Arduino (Uno/Mega/Nano), ESP32, Raspberry Pi Pico, ATtiny85, STM32 Bluepill
- **Wireless Module Support** — Bluetooth (HC-05/06, HM-10), WiFi (ESP-01), RF (nRF24L01), IR

### Infrastructure
- **Dual Mode** — Runs as a REST API (web app) or MCP server (for Claude Desktop / AI agents)
- **Authentication** — Email/password signup + Google OAuth sign-in with JWT tokens
- **Analysis History** — Stores past analyses per user with full report viewing, project type badges
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

## KiCad Analysis Capabilities

### Schematic Rule-Based Checks (14 checks)
| Check | What It Detects |
|-------|----------------|
| Unconnected pins | Pins not wired and without no-connect markers |
| Duplicate references | Two components with the same designator (e.g., two R1) |
| Missing values | Resistors/capacitors without specified values |
| PWR_FLAG check | Power nets missing PWR_FLAG symbols |
| Single-pin nets | Label typos causing orphaned connections |
| Voltage mismatch | 3.3V IC on 5V rail without level shifting |
| Decoupling capacitors | ICs missing bypass caps on power pins |
| LED resistors | LEDs without current-limiting resistors |
| Pin function mismatch | SDA signal on a non-I2C capable pin |
| Polarity check | Reversed LED/diode/capacitor polarity |
| UART crossover | TX wired to TX instead of TX-to-RX |
| Pin type conflicts | Multiple outputs driving the same net |
| Footprint pad mismatch | Symbol pin count vs footprint pad count |
| Library symbol issues | ICs with missing power pin definitions |

### PCB Rule-Based Checks (6 checks)
| Check | What It Detects |
|-------|----------------|
| Unrouted nets | Nets with pads but no tracks |
| Trace width | Traces below manufacturing minimum |
| Via drill size | Drills too small, annular rings too thin |
| Clearance violations | Traces too close together |
| Power trace width | Power traces too narrow for current |
| Schematic-PCB sync | Components missing between schematic and PCB |

### AI-Powered Deep Analysis
- Analyzes beyond rule-based checks using GPT-4o
- Detects signal integrity issues, thermal concerns, EMC problems
- Cross-references schematic against PCB layout
- Compares actual design against user's stated intent (design description)

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy (async SQLite), OpenAI GPT-4o/4o-mini, python-jose (JWT), google-auth

**Frontend:** React 19, Vite, Axios, react-router-dom, @react-oauth/google

**MCP:** FastMCP over stdio

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              Frontend (React 19 + Vite)     │
                    │                                             │
                    │  UrlInput ─┐                                │
                    │            ├─► Dashboard ──► FaultReport    │
                    │  KiCadUpload┘    │    │ ──► CircuitViewer   │
                    │  (mode toggle)   │    │ ──► SchematicViewer │
                    │                  │    │ ──► CodeView        │
                    │  Design          │    │ ──► FixSuggestion   │
                    │  Description ────┘    │ ──► SummaryBar      │
                    │                       │                     │
                    │  Auth ── LoginPage ── ProtectedRoute        │
                    │  Pages ── HistoryPage ── HistoryDetailPage  │
                    └──────────────┬──────────────────────────────┘
                                   │ Axios + JWT
                    ┌──────────────▼──────────────────────────────┐
                    │              Backend (FastAPI)               │
                    │                                             │
                    │  /api/analyze ──► Wokwi Fetcher             │
                    │       │              │                      │
                    │       ▼              ▼                      │
                    │  Rule Engine ──► AI Analysis (GPT-4o)       │
                    │  (20+ checks)    (circuit + code prompts)   │
                    │       │              │                      │
                    │       └──────┬───────┘                      │
                    │              ▼                               │
                    │  /api/kicad/upload ──► KiCad Parser          │
                    │       │                  │                  │
                    │       ▼                  ▼                  │
                    │  KiCad Rule Engine ── KiCad AI Analysis     │
                    │  (14 ERC + 6 DRC)    (schematic + PCB)     │
                    │                                             │
                    │  Auth (JWT + Google OAuth)                  │
                    │  History (SQLAlchemy + async SQLite)        │
                    └──────────────┬──────────────────────────────┘
                                   │ MCP (stdio)
                    ┌──────────────▼──────────────────────────────┐
                    │         MCP Server (FastMCP)                │
                    │  Tools: analyze_wokwi_project,              │
                    │         analyze_kicad_project,              │
                    │         check_wiring, check_code,           │
                    │         suggest_fix, etc.                   │
                    └─────────────────────────────────────────────┘
```

## Project Structure

```
my_mcp/
├── backend/
│   ├── .env                       # Secrets (JWT key, Google Client ID, OpenAI key)
│   ├── server.py                  # Dual-mode server (FastAPI + MCP)
│   ├── analyzer.py                # Wokwi rule-based + AI analysis engine
│   ├── prompts.py                 # Wokwi OpenAI prompt templates
│   ├── component_knowledge.py     # Board, component, wireless & library specs
│   ├── wokwi_fetch.py             # Wokwi project fetcher
│   ├── kicad_parser.py            # KiCad .kicad_sch/.kicad_pcb file parser
│   ├── kicad_analyzer.py          # KiCad rule-based + AI analysis engine
│   ├── kicad_prompts.py           # KiCad OpenAI prompt templates
│   ├── kicad_component_knowledge.py # KiCad component specs & pin data
│   ├── auth.py                    # JWT + Google token verification
│   ├── auth_routes.py             # Auth API endpoints
│   ├── history_routes.py          # Analysis history endpoints
│   ├── config.py                  # Pydantic settings
│   ├── database.py                # Async SQLAlchemy setup
│   ├── models.py                  # User + AnalysisHistory models
│   └── requirements.txt           # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── auth/                  # AuthContext, LoginPage, ProtectedRoute, UserMenu
│   │   ├── components/
│   │   │   ├── UrlInput.jsx       # Wokwi URL input + design description
│   │   │   ├── KiCadUpload.jsx    # KiCad file drag-and-drop + design description
│   │   │   ├── SummaryBar.jsx     # Fault count summary (errors/warnings/infos)
│   │   │   ├── FaultReport.jsx    # Filterable fault cards with severity badges
│   │   │   ├── CircuitViewer.jsx  # Wokwi circuit parts/connections viewer
│   │   │   ├── SchematicViewer.jsx# KiCad schematic info viewer
│   │   │   ├── CodeView.jsx       # Arduino code with fault annotations
│   │   │   └── FixSuggestion.jsx  # AI-generated fix suggestions
│   │   ├── pages/
│   │   │   ├── ProfilePage.jsx    # User profile + change password
│   │   │   ├── HistoryPage.jsx    # Analysis history with project type badges
│   │   │   └── HistoryDetailPage.jsx # Full report viewer (conditional by type)
│   │   ├── api.js                 # Axios client with JWT interceptors + auto-refresh
│   │   ├── App.jsx                # Dashboard with mode toggle + routing
│   │   └── main.jsx               # Entry point with providers
│   ├── .env                       # VITE_GOOGLE_CLIENT_ID
│   ├── vercel.json                # Vercel SPA routing config
│   └── package.json
├── render.yaml                    # Render deployment config
└── env/                           # Python virtual environment
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

### Wokwi Analysis (requires auth)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze` | Full project analysis (URL + optional design_description) |
| POST | `/api/check-wiring` | Wiring-only analysis |
| POST | `/api/check-code` | Code-only analysis |
| POST | `/api/suggest-fix` | Generate fix suggestions |

### KiCad Analysis (requires auth)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/kicad/upload` | Upload .kicad_sch/.kicad_pcb files + optional design_description |
| POST | `/api/kicad/analyze` | Analyze from raw content |
| POST | `/api/kicad/check-schematic` | Schematic-only analysis |
| POST | `/api/kicad/check-pcb` | PCB-only analysis |
| POST | `/api/kicad/suggest-fix` | Generate KiCad fix suggestions |

### History (requires auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/history` | List user's past analyses (with project type) |
| GET | `/api/history/{id}` | Get full report for a history entry |
| DELETE | `/api/history/{id}` | Delete a history entry |

## MCP Tools

When running in MCP mode (`--mode mcp`), the server exposes these tools over stdio:

**Wokwi:**
- `analyze_wokwi_project(wokwi_url)` — Full fault analysis
- `check_wiring(diagram_json)` — Wiring analysis
- `check_code(sketch_code, diagram_json)` — Code analysis
- `suggest_fix(fault_report, diagram_json, sketch_code)` — Fix generation

**KiCad:**
- `analyze_kicad_project(schematic_content, pcb_content, project_content)` — Full KiCad analysis
- `check_kicad_schematic(schematic_content)` — Schematic ERC analysis
- `check_kicad_pcb(pcb_content, schematic_content)` — PCB DRC analysis
- `suggest_kicad_fix(fault_report, schematic_content, pcb_content)` — Fix generation

## License

MIT

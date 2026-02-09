# Wokwi Circuit Analyzer

AI-powered Arduino circuit fault detection tool that analyzes public Wokwi projects for wiring errors, code bugs, and component issues.

## Features

- **Circuit Analysis** — Detects wiring faults, missing connections, polarity errors, and power issues
- **Code Analysis** — Finds Arduino sketch bugs and cross-references against circuit wiring
- **Fix Suggestions** — Generates corrected code and wiring based on detected faults
- **Dual Mode** — Runs as a REST API (web app) or MCP server (for Claude Desktop / AI agents)
- **Authentication** — Email/password signup + Google OAuth sign-in with JWT tokens
- **Analysis History** — Stores past analyses per user with full report viewing
- **User Profiles** — Profile page with change password support
- **History Detail View** — Click any past analysis to view the full fault report, circuit, code, and fix suggestions

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
│   ├── component_knowledge.py# Arduino component specs
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
│   └── package.json
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

## License

MIT

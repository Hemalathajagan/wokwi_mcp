"""
Wokwi Arduino Circuit Fault Analyzer
Dual-mode server: FastAPI REST API + MCP Server

Usage:
  API mode:  python server.py --mode api
  MCP mode:  python server.py --mode mcp
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file into environment so analyzer can read OPENAI_API_KEY
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from wokwi_fetch import fetch_project
from analyzer import full_analysis, analyze_wiring, analyze_code, suggest_fixes
from auth import get_current_user
from auth_routes import router as auth_router
from history_routes import router as history_router
from database import init_db, get_db
from models import AnalysisHistory, User
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Pydantic models for REST API
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    url: str

class CheckWiringRequest(BaseModel):
    diagram_json: str

class CheckCodeRequest(BaseModel):
    sketch_code: str
    diagram_json: str = ""

class SuggestFixRequest(BaseModel):
    fault_report: str
    diagram_json: str = ""
    sketch_code: str = ""


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Wokwi Circuit Analyzer",
    description="AI-powered Arduino circuit fault detection",
    version="1.0.0",
)

# CORS: allow frontend origins (comma-separated in ALLOWED_ORIGINS env var)
_default_origins = ["http://localhost:5173", "http://localhost:3000"]
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
_origins = _default_origins + [o.strip() for o in _env_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(history_router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/analyze")
async def api_analyze(
    req: AnalyzeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a Wokwi project and perform full fault analysis."""
    try:
        project = await fetch_project(req.url)
        report = await full_analysis(project.diagram, project.sketch_code)
        report["project_id"] = project.project_id

        # Save to history
        summary = report.get("summary", {})
        fault_count = summary.get("total", len(report.get("faults", [])))
        entry = AnalysisHistory(
            user_id=user.id,
            wokwi_url=req.url,
            project_id=project.project_id,
            summary_json=json.dumps(summary),
            report_json=json.dumps(report),
            fault_count=fault_count,
        )
        db.add(entry)
        await db.commit()

        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/check-wiring")
async def api_check_wiring(req: CheckWiringRequest, user: User = Depends(get_current_user)):
    """Analyze diagram.json for wiring faults."""
    try:
        diagram = json.loads(req.diagram_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in diagram_json")
    report = await analyze_wiring(diagram)
    return report


@app.post("/api/check-code")
async def api_check_code(req: CheckCodeRequest, user: User = Depends(get_current_user)):
    """Analyze Arduino sketch code for bugs."""
    diagram = {}
    if req.diagram_json:
        try:
            diagram = json.loads(req.diagram_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in diagram_json")
    report = await analyze_code(req.sketch_code, diagram)
    return report


@app.post("/api/suggest-fix")
async def api_suggest_fix(req: SuggestFixRequest, user: User = Depends(get_current_user)):
    """Generate corrected code/wiring for detected faults."""
    diagram = {}
    if req.diagram_json:
        try:
            diagram = json.loads(req.diagram_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in diagram_json")
    result = await suggest_fixes(req.fault_report, diagram, req.sketch_code)
    return result


# ---------------------------------------------------------------------------
# MCP Server mode
# ---------------------------------------------------------------------------

def run_mcp_server():
    """Run as an MCP server over stdio."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("WokwiAnalyzer")

    @mcp.tool()
    async def analyze_wokwi_project(wokwi_url: str) -> str:
        """Fetch a public Wokwi Arduino project by URL and perform comprehensive
        fault analysis on wiring, components, power, signals, and code.
        Returns a detailed JSON report with explanations and fix suggestions.

        Args:
            wokwi_url: Full Wokwi project URL (e.g., https://wokwi.com/projects/123456)
        """
        try:
            project = await fetch_project(wokwi_url)
            report = await full_analysis(project.diagram, project.sketch_code)
            report["project_id"] = project.project_id
            return json.dumps(report, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def check_wiring(diagram_json: str) -> str:
        """Analyze a Wokwi diagram.json for wiring and circuit faults.
        Detects missing connections, polarity errors, power issues, and more.

        Args:
            diagram_json: Raw JSON string of a Wokwi diagram.json file
        """
        try:
            diagram = json.loads(diagram_json)
            report = await analyze_wiring(diagram)
            return json.dumps(report, indent=2)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON"})

    @mcp.tool()
    async def check_code(sketch_code: str, diagram_json: str = "") -> str:
        """Analyze Arduino sketch code for bugs and cross-reference against circuit wiring.

        Args:
            sketch_code: The Arduino .ino sketch source code
            diagram_json: Optional diagram.json to cross-check pin assignments
        """
        diagram = json.loads(diagram_json) if diagram_json else {}
        report = await analyze_code(sketch_code, diagram)
        return json.dumps(report, indent=2)

    @mcp.tool()
    async def suggest_fix(fault_report: str, diagram_json: str = "", sketch_code: str = "") -> str:
        """Given a fault report, generate corrected Arduino code and/or circuit wiring.

        Args:
            fault_report: The fault analysis text from a previous analysis
            diagram_json: Original diagram.json (for wiring fixes)
            sketch_code: Original sketch code (for code fixes)
        """
        diagram = json.loads(diagram_json) if diagram_json else {}
        result = await suggest_fixes(fault_report, diagram, sketch_code)
        return json.dumps(result, indent=2)

    mcp.run()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wokwi Circuit Analyzer Server")
    parser.add_argument(
        "--mode",
        choices=["api", "mcp"],
        default="api",
        help="Run mode: 'api' for FastAPI REST server, 'mcp' for MCP stdio server",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for API mode")
    parser.add_argument("--host", default="0.0.0.0", help="Host for API mode")

    args = parser.parse_args()

    if args.mode == "mcp":
        run_mcp_server()
    else:
        print(f"Starting Wokwi Circuit Analyzer API on http://{args.host}:{args.port}")
        print("Docs available at http://localhost:8000/docs")
        uvicorn.run(app, host=args.host, port=args.port)

"""
Circuit Fault Analyzer (Wokwi + KiCad)
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
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from wokwi_fetch import fetch_project
from analyzer import full_analysis, analyze_wiring, analyze_code, suggest_fixes
from kicad_parser import load_from_path, load_from_content
from kicad_analyzer import (
    full_kicad_analysis,
    analyze_kicad_schematic,
    analyze_kicad_pcb,
    suggest_kicad_fixes,
)
from auth import get_current_user
from auth_routes import router as auth_router
from history_routes import router as history_router
from database import init_db, migrate_db, get_db
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


class KiCadAnalyzeRequest(BaseModel):
    project_path: str | None = None
    schematic_content: str | None = None
    pcb_content: str | None = None
    project_content: str | None = None


class KiCadCheckSchematicRequest(BaseModel):
    schematic_content: str


class KiCadCheckPcbRequest(BaseModel):
    pcb_content: str
    schematic_content: str | None = None


class KiCadSuggestFixRequest(BaseModel):
    fault_report: str
    schematic_content: str | None = None
    pcb_content: str | None = None


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Circuit Analyzer",
    description="AI-powered circuit fault detection for Wokwi and KiCad projects",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(history_router)


@app.on_event("startup")
async def startup():
    await init_db()
    await migrate_db()


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
# KiCad REST API endpoints
# ---------------------------------------------------------------------------


@app.post("/api/kicad/analyze")
async def api_kicad_analyze(
    req: KiCadAnalyzeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze a KiCad project (from local path or pasted file content)."""
    try:
        if req.project_path:
            project = load_from_path(req.project_path)
        elif req.schematic_content or req.pcb_content:
            project = load_from_content(
                schematic_content=req.schematic_content or "",
                pcb_content=req.pcb_content or "",
                project_content=req.project_content or "",
            )
        else:
            raise ValueError("Provide either project_path or schematic_content/pcb_content")

        report = await full_kicad_analysis(project)

        # Save to history
        summary = report.get("summary", {})
        fault_count = summary.get("total", len(report.get("faults", [])))
        entry = AnalysisHistory(
            user_id=user.id,
            project_type="kicad",
            project_name=project.project_name,
            source_path=project.source_path,
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
        raise HTTPException(status_code=500, detail=f"KiCad analysis failed: {str(e)}")


@app.post("/api/kicad/check-schematic")
async def api_kicad_check_schematic(
    req: KiCadCheckSchematicRequest,
    user: User = Depends(get_current_user),
):
    """Analyze a KiCad schematic for ERC errors."""
    try:
        project = load_from_content(schematic_content=req.schematic_content)
        report = await analyze_kicad_schematic(project.schematic, project.raw_schematic)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schematic analysis failed: {str(e)}")


@app.post("/api/kicad/check-pcb")
async def api_kicad_check_pcb(
    req: KiCadCheckPcbRequest,
    user: User = Depends(get_current_user),
):
    """Analyze a KiCad PCB layout for DRC errors."""
    try:
        project = load_from_content(
            pcb_content=req.pcb_content,
            schematic_content=req.schematic_content or "",
        )
        report = await analyze_kicad_pcb(
            project.pcb, project.schematic, project.raw_pcb, project.raw_schematic
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PCB analysis failed: {str(e)}")


@app.post("/api/kicad/suggest-fix")
async def api_kicad_suggest_fix(
    req: KiCadSuggestFixRequest,
    user: User = Depends(get_current_user),
):
    """Generate fix suggestions for KiCad design issues."""
    try:
        result = await suggest_kicad_fixes(
            req.fault_report,
            raw_sch=req.schematic_content or "",
            raw_pcb=req.pcb_content or "",
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fix suggestion failed: {str(e)}")


# ---------------------------------------------------------------------------
# MCP Server mode
# ---------------------------------------------------------------------------

def run_mcp_server():
    """Run as an MCP server over stdio."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("CircuitAnalyzer")

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

    @mcp.tool()
    async def analyze_kicad_project(
        project_path: str = "",
        schematic_content: str = "",
        pcb_content: str = "",
        project_content: str = "",
    ) -> str:
        """Analyze a KiCad EDA project for schematic (ERC) and PCB (DRC) errors.
        Provide either a local project_path OR paste schematic/pcb content directly.

        Args:
            project_path: Local path to a KiCad project directory or file
            schematic_content: Raw content of a .kicad_sch file
            pcb_content: Raw content of a .kicad_pcb file
            project_content: Raw content of a .kicad_pro file (optional)
        """
        try:
            if project_path:
                project = load_from_path(project_path)
            elif schematic_content or pcb_content:
                project = load_from_content(
                    schematic_content=schematic_content,
                    pcb_content=pcb_content,
                    project_content=project_content,
                )
            else:
                return json.dumps({"error": "Provide project_path or schematic_content/pcb_content"})
            report = await full_kicad_analysis(project)
            return json.dumps(report, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def check_kicad_schematic(schematic_content: str) -> str:
        """Analyze a KiCad schematic (.kicad_sch) for electrical rule check (ERC) errors.
        Detects unconnected pins, power issues, duplicate references, and more.

        Args:
            schematic_content: Raw content of a .kicad_sch file
        """
        try:
            project = load_from_content(schematic_content=schematic_content)
            report = await analyze_kicad_schematic(project.schematic, project.raw_schematic)
            return json.dumps(report, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def check_kicad_pcb(pcb_content: str, schematic_content: str = "") -> str:
        """Analyze a KiCad PCB layout (.kicad_pcb) for design rule check (DRC) errors.
        Detects clearance violations, trace width issues, unrouted nets, and more.

        Args:
            pcb_content: Raw content of a .kicad_pcb file
            schematic_content: Optional .kicad_sch content for cross-reference checks
        """
        try:
            project = load_from_content(
                pcb_content=pcb_content,
                schematic_content=schematic_content,
            )
            report = await analyze_kicad_pcb(
                project.pcb, project.schematic, project.raw_pcb, project.raw_schematic
            )
            return json.dumps(report, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def suggest_kicad_fix(
        fault_report: str, schematic_content: str = "", pcb_content: str = ""
    ) -> str:
        """Generate fix suggestions for KiCad schematic and PCB design issues.

        Args:
            fault_report: The fault analysis text from a previous KiCad analysis
            schematic_content: Original .kicad_sch content (for schematic fixes)
            pcb_content: Original .kicad_pcb content (for PCB fixes)
        """
        try:
            result = await suggest_kicad_fixes(fault_report, schematic_content, pcb_content)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    mcp.run()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Circuit Analyzer Server")
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
        print(f"Starting Circuit Analyzer API on http://{args.host}:{args.port}")
        print("Docs available at http://localhost:8000/docs")
        uvicorn.run(app, host=args.host, port=args.port)

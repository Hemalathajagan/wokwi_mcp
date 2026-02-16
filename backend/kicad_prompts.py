"""
OpenAI prompt templates for KiCad schematic and PCB analysis.
"""


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

KICAD_SCHEMATIC_ANALYSIS_SYSTEM = """You are an expert electronics engineer and PCB designer. Your job is to analyze KiCad schematics for design errors, following professional ERC (Electrical Rules Check) standards.

You will receive:
1. Parsed component and net information from a .kicad_sch file
2. Component reference data with known requirements and common mistakes
3. Pre-analysis findings from automated rule-based checks

Analyze for these fault categories:

### 1. Electrical Rule Violations (ERC)
- Unconnected pins without no-connect markers
- Output-to-output driver conflicts on the same net
- Power pins not connected to power nets
- Missing PWR_FLAG symbols on power nets
- Single-pin nets (orphaned labels likely from typos)

### 2. Power Design Issues
- Missing decoupling capacitors on IC power pins
- Incorrect voltage regulator input/output capacitors
- Voltage rail mismatches (3.3V IC connected to 5V rail without level shifting)
- Missing bulk capacitors on power input
- AVCC/VREF pins left floating on MCUs

### 3. Signal Integrity
- Missing pull-up resistors on I2C bus (SDA/SCL)
- Missing pull-up on reset pins
- Missing termination resistors on high-speed signals
- Crystal load capacitor value mismatch
- Analog signals routed near noisy digital signals

### 4. Component Issues
- Resistors/capacitors with missing or invalid values
- Polarized component polarity errors
- Wrong component for the application
- Missing protection components (ESD diodes, TVS, fuses)

### 5. Connectivity Issues
- Nets that should be connected but have different names
- Bus naming inconsistencies
- Hierarchical sheet port mismatches

For each fault, return a JSON object with these exact fields:
{
  "category": "erc" | "power" | "signal" | "component" | "connectivity" | "intent_mismatch",
  "severity": "error" | "warning" | "info",
  "component": "reference designator or net name",
  "title": "short one-line description",
  "explanation": "detailed technical explanation of the issue and its consequences",
  "fix": {"type": "schematic", "description": "specific steps to fix the issue"}
}

Return ONLY a JSON array of fault objects. Do NOT duplicate findings already reported in the pre-analysis. Focus on issues the automated checks may have missed."""


KICAD_PCB_ANALYSIS_SYSTEM = """You are an expert PCB layout engineer. Analyze a KiCad PCB layout for manufacturing, signal integrity, and reliability issues following professional DRC (Design Rule Check) standards.

You will receive:
1. Parsed footprint, track, via, and zone data from a .kicad_pcb file
2. Net information and design rule settings
3. Pre-analysis findings from automated rule-based checks

Analyze for these fault categories:

### 1. Design Rule Violations (DRC)
- Trace-to-trace clearance violations
- Pad-to-pad clearance violations
- Via drill size below manufacturing minimum
- Trace width below minimum
- Unrouted nets (ratsnest)
- Copper too close to board edge

### 2. Manufacturing Issues
- Silkscreen overlapping pads
- Component courtyard overlaps (physical collision)
- Via-in-pad without proper fill/cap specification
- Small annular rings on vias
- Drill holes too close together

### 3. Signal Integrity
- Power traces too narrow for expected current
- Long parallel high-speed traces (crosstalk risk)
- Missing ground return path for signal traces
- Impedance discontinuities on controlled impedance traces
- Missing stitching vias between ground planes

### 4. Thermal Issues
- Insufficient copper pour for heat dissipation
- Missing thermal relief on power plane connections (solderability)
- Heat-generating components too close together
- Missing thermal vias under thermal pads

### 5. EMC Issues
- Split ground planes under high-speed signals
- Long traces without ground plane reference
- Missing bypass capacitors close to IC power pins (placement)
- Clock traces not properly routed

For each fault, return a JSON object with these exact fields:
{
  "category": "drc" | "manufacturing" | "signal" | "thermal" | "emc" | "intent_mismatch",
  "severity": "error" | "warning" | "info",
  "component": "reference designator, net name, or location",
  "title": "short one-line description",
  "explanation": "detailed technical explanation",
  "fix": {"type": "pcb", "description": "specific steps to fix"}
}

Return ONLY a JSON array of fault objects. Do NOT duplicate pre-analysis findings."""


KICAD_FIX_SUGGESTION_SYSTEM = """You are an expert PCB designer. Given a fault report from a KiCad project analysis, suggest specific, actionable fixes.

Rules:
- Be specific: reference exact component designators, net names, pin numbers
- For schematic fixes: describe exactly what to add, change, reconnect, or remove
- For PCB fixes: describe trace changes, component placement moves, via additions
- Clearly distinguish between schematic changes and PCB changes
- Prioritize errors over warnings
- If a fix requires adding new components, specify the component type and value

Return a JSON object:
{
  "schematic_changes": [
    {"description": "what to change", "component": "affected ref designator", "action": "add|modify|remove|reconnect"}
  ],
  "pcb_changes": [
    {"description": "what to change", "location": "component or area", "action": "reroute|move|add_via|widen_trace|add_copper"}
  ],
  "new_components": [
    {"type": "component type", "value": "value if applicable", "purpose": "why it's needed", "connection": "where to connect it"}
  ],
  "summary": "brief overall summary of all changes needed"
}

Return ONLY valid JSON."""


# ---------------------------------------------------------------------------
# User prompt builders
# ---------------------------------------------------------------------------

def build_schematic_analysis_prompt(
    parsed_data: dict,
    component_knowledge: str,
    rule_findings: list[dict],
    design_description: str = "",
) -> str:
    """Build the user prompt for schematic AI analysis."""
    symbols_text = _format_symbols(parsed_data.get("symbols", []))
    power_text = _format_power_symbols(parsed_data.get("power_symbols", []))
    nets_text = _format_nets(parsed_data.get("nets", {}))
    findings_text = _format_rule_findings(rule_findings)
    desc_text = design_description if design_description else "No description provided."

    return f"""## Design Description (User's Intended Behavior)
{desc_text}

## KiCad Schematic Analysis

### Components ({len(parsed_data.get('symbols', []))} total)
{symbols_text}

### Power Symbols
{power_text}

### Net Connectivity
{nets_text}

### Component Reference Data
{component_knowledge}

### Pre-Analysis Findings ({len(rule_findings)} issues found by automated checks)
{findings_text}

Analyze this schematic for additional issues beyond the pre-analysis findings. If a design description is provided above, compare the actual wiring and pin assignments against the user's stated intent. Flag any mismatches as "intent_mismatch" category faults even if the wiring is electrically valid. Return a JSON array of fault objects."""


def build_pcb_analysis_prompt(
    parsed_pcb: dict,
    parsed_sch: dict | None,
    rule_findings: list[dict],
    design_description: str = "",
) -> str:
    """Build the user prompt for PCB AI analysis."""
    footprints_text = _format_footprints(parsed_pcb.get("footprints", []))
    nets_text = _format_pcb_nets(parsed_pcb.get("nets", {}))
    segments_summary = _format_segments_summary(parsed_pcb.get("segments", []))
    vias_summary = _format_vias_summary(parsed_pcb.get("vias", []))
    zones_text = _format_zones(parsed_pcb.get("zones", []))
    findings_text = _format_rule_findings(rule_findings)
    desc_text = design_description if design_description else "No description provided."

    sch_section = ""
    if parsed_sch:
        sch_nets = parsed_sch.get("nets", {})
        sch_section = f"\n### Schematic Nets (for cross-reference)\n{_format_nets(sch_nets)}"

    return f"""## Design Description (User's Intended Behavior)
{desc_text}

## KiCad PCB Layout Analysis

### Footprints ({len(parsed_pcb.get('footprints', []))} components)
{footprints_text}

### Nets ({len(parsed_pcb.get('nets', {}))} total)
{nets_text}

### Tracks Summary
{segments_summary}

### Vias Summary
{vias_summary}

### Copper Zones
{zones_text}
{sch_section}

### Pre-Analysis Findings ({len(rule_findings)} issues)
{findings_text}

Analyze this PCB layout for additional issues. If a design description is provided above, compare the actual layout against the user's stated intent and flag mismatches as "intent_mismatch" category faults. Return a JSON array of fault objects."""


def build_fix_suggestion_prompt(
    fault_report: str,
    raw_sch: str = "",
    raw_pcb: str = "",
) -> str:
    """Build the user prompt for fix suggestions."""
    context = f"## Fault Report\n{fault_report}\n"

    if raw_sch:
        # Include a truncated version to stay within token limits
        sch_preview = raw_sch[:8000] + ("..." if len(raw_sch) > 8000 else "")
        context += f"\n## Schematic Content (preview)\n```\n{sch_preview}\n```\n"

    if raw_pcb:
        pcb_preview = raw_pcb[:8000] + ("..." if len(raw_pcb) > 8000 else "")
        context += f"\n## PCB Content (preview)\n```\n{pcb_preview}\n```\n"

    context += "\nGenerate specific fix suggestions. Return JSON."
    return context


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_symbols(symbols: list[dict]) -> str:
    if not symbols:
        return "No components found."
    lines = []
    for s in symbols:
        ref = s.get("reference", "?")
        value = s.get("value", "")
        lib_id = s.get("lib_id", "")
        pin_count = len(s.get("pins", []))
        lines.append(f"- {ref}: {value} ({lib_id}) — {pin_count} pins")
    return "\n".join(lines)


def _format_power_symbols(power_symbols: list[dict]) -> str:
    if not power_symbols:
        return "No power symbols found."
    lines = []
    for s in power_symbols:
        lines.append(f"- {s.get('value', '?')} ({s.get('reference', '')})")
    return "\n".join(lines)


def _format_nets(nets: dict) -> str:
    if not nets:
        return "No nets found."
    lines = []
    for name, pins in sorted(nets.items()):
        pins_str = ", ".join(pins[:10])
        extra = f" ... and {len(pins) - 10} more" if len(pins) > 10 else ""
        lines.append(f"- **{name}**: {pins_str}{extra}")
    return "\n".join(lines)


def _format_pcb_nets(nets: dict) -> str:
    if not nets:
        return "No nets found."
    lines = []
    for num, name in sorted(nets.items()):
        if name:  # skip unconnected net 0
            lines.append(f"- Net {num}: {name}")
    return "\n".join(lines[:50])  # limit output


def _format_footprints(footprints: list[dict]) -> str:
    if not footprints:
        return "No footprints found."
    lines = []
    for fp in footprints:
        ref = fp.get("reference", "?")
        value = fp.get("value", "")
        lib = fp.get("library", "")
        pad_count = len(fp.get("pads", []))
        layer = fp.get("layer", "")
        lines.append(f"- {ref}: {value} ({lib}) on {layer} — {pad_count} pads")
    return "\n".join(lines)


def _format_segments_summary(segments: list[dict]) -> str:
    if not segments:
        return "No tracks routed."
    widths: dict[float, int] = {}
    layers: dict[str, int] = {}
    for seg in segments:
        w = seg.get("width", 0)
        widths[w] = widths.get(w, 0) + 1
        layer = seg.get("layer", "")
        layers[layer] = layers.get(layer, 0) + 1

    lines = [f"Total segments: {len(segments)}"]
    lines.append("Width distribution:")
    for w, count in sorted(widths.items()):
        lines.append(f"  {w:.3f}mm: {count} segments")
    lines.append("Layer distribution:")
    for layer, count in sorted(layers.items()):
        lines.append(f"  {layer}: {count} segments")
    return "\n".join(lines)


def _format_vias_summary(vias: list[dict]) -> str:
    if not vias:
        return "No vias."
    drills: dict[float, int] = {}
    for v in vias:
        d = v.get("drill", 0)
        drills[d] = drills.get(d, 0) + 1
    lines = [f"Total vias: {len(vias)}"]
    for drill, count in sorted(drills.items()):
        lines.append(f"  Drill {drill:.2f}mm: {count} vias")
    return "\n".join(lines)


def _format_zones(zones: list[dict]) -> str:
    if not zones:
        return "No copper zones."
    lines = []
    for z in zones:
        name = z.get("net_name", "unnamed")
        layers = ", ".join(z.get("layers", []))
        lines.append(f"- Net '{name}' on {layers}")
    return "\n".join(lines)


def _format_rule_findings(findings: list[dict]) -> str:
    if not findings:
        return "No issues found by automated checks."
    lines = []
    for f in findings:
        severity = f.get("severity", "info").upper()
        title = f.get("title", "Unknown issue")
        comp = f.get("component", "")
        lines.append(f"- [{severity}] {comp}: {title}")
    return "\n".join(lines)

"""
Core analysis engine: rule-based checks + OpenAI-powered deep analysis.
Detects wiring faults, component issues, power problems, signal integrity,
code bugs, and code-circuit cross-reference mismatches.
"""

import json
import os
import re
from collections import defaultdict

import openai

from component_knowledge import (
    COMPONENT_PINS,
    ARDUINO_BOARDS,
    POWER_PIN_TYPES,
    GROUND_PIN_TYPES,
    get_relevant_knowledge,
    get_pwm_pins,
    get_analog_pins,
    get_board_from_parts,
)
from prompts import (
    build_circuit_analysis_prompt,
    build_code_analysis_prompt,
    build_fix_suggestion_prompt,
)


# ---------------------------------------------------------------------------
# OpenAI helper
# ---------------------------------------------------------------------------

async def call_openai(system_prompt: str, user_message: str) -> str:
    """Call OpenAI chat completion API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")

    client = openai.AsyncOpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=8192,
    )
    return response.choices[0].message.content


def _try_repair_json(text: str):
    """Attempt to repair truncated JSON by closing open strings, arrays, and objects."""
    # Try as-is first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try closing an unterminated string, then close braces/brackets
    repairs = [
        text + '"}',
        text + '"}]',
        text + '"}}',
        text + '"}]}',
        text + '}',
        text + '}]',
        text + ']',
    ]
    for attempt in repairs:
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    return None


def parse_openai_json(text: str) -> list[dict]:
    """Parse JSON array from OpenAI response, handling markdown code fences."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (the fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []
    except json.JSONDecodeError:
        # Try repairing truncated JSON
        result = _try_repair_json(text)
        if result is not None:
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return [result]
        return []


# ---------------------------------------------------------------------------
# Rule-based analysis helpers
# ---------------------------------------------------------------------------

def _build_connection_graph(diagram: dict) -> tuple[dict, set, dict]:
    """Parse diagram connections into useful data structures.

    Returns:
        adjacency: dict mapping "partId:pin" -> set of "partId:pin"
        connected_parts: set of part IDs that appear in at least one connection
        pin_connections: dict mapping "partId:pin" -> list of connections it appears in
    """
    connections = diagram.get("connections", [])
    adjacency = defaultdict(set)
    connected_parts = set()
    pin_connections = defaultdict(list)

    for conn in connections:
        if len(conn) < 2:
            continue
        src, tgt = conn[0], conn[1]
        adjacency[src].add(tgt)
        adjacency[tgt].add(src)
        pin_connections[src].append(conn)
        pin_connections[tgt].append(conn)

        # Track which parts have connections
        if ":" in src:
            connected_parts.add(src.split(":")[0])
        if ":" in tgt:
            connected_parts.add(tgt.split(":")[0])

    return dict(adjacency), connected_parts, dict(pin_connections)


def _check_unconnected_parts(parts: list[dict], connected_parts: set) -> list[dict]:
    """Find parts that have no connections at all."""
    faults = []
    for part in parts:
        pid = part.get("id", "")
        ptype = part.get("type", "")
        if ptype in ARDUINO_BOARDS:
            continue  # Board is always "connected"
        if pid not in connected_parts:
            faults.append({
                "category": "wiring",
                "severity": "warning",
                "component": pid,
                "title": f"Unconnected component: {pid} ({ptype})",
                "explanation": f"Part '{pid}' of type '{ptype}' has no wires connected to it. It will have no effect in the circuit.",
                "fix": {"type": "wiring", "description": f"Connect {pid} to the appropriate Arduino pins and power/ground."},
            })
    return faults


def _check_invalid_pins(parts: list[dict], connections: list) -> list[dict]:
    """Check for pin references that don't exist on the component."""
    faults = []
    parts_map = {p["id"]: p for p in parts}

    for conn in connections:
        if len(conn) < 2:
            continue
        for endpoint in [conn[0], conn[1]]:
            if ":" not in endpoint:
                continue
            part_id, pin_name = endpoint.split(":", 1)
            if part_id not in parts_map:
                continue
            ptype = parts_map[part_id].get("type", "")
            comp_info = COMPONENT_PINS.get(ptype)
            if comp_info and pin_name not in comp_info["pins"]:
                faults.append({
                    "category": "wiring",
                    "severity": "error",
                    "component": part_id,
                    "title": f"Invalid pin '{pin_name}' on {ptype}",
                    "explanation": f"Pin '{pin_name}' does not exist on component type '{ptype}'. Valid pins: {', '.join(comp_info['pins'].keys())}",
                    "fix": {"type": "wiring", "description": f"Use one of the valid pins for {ptype}: {', '.join(comp_info['pins'].keys())}"},
                })
    return faults


def _check_led_polarity(parts: list[dict], adjacency: dict) -> list[dict]:
    """Check if LEDs have reversed polarity (anode to GND, cathode to VCC/digital pin)."""
    faults = []
    parts_map = {p["id"]: p for p in parts}

    for part in parts:
        if part.get("type") not in ("wokwi-led", "wokwi-rgb-led"):
            continue
        pid = part["id"]

        # Check cathode connections - should go to GND
        cathode_key = f"{pid}:C" if part["type"] == "wokwi-led" else f"{pid}:COM"
        for neighbor in adjacency.get(cathode_key, []):
            if ":" not in neighbor:
                continue
            npart_id, npin = neighbor.split(":", 1)
            if npart_id in parts_map:
                ntype = parts_map[npart_id].get("type", "")
                ncomp = COMPONENT_PINS.get(ntype, {})
                npin_info = ncomp.get("pins", {}).get(npin, {})
                pin_type = npin_info.get("type", "")
                # Cathode connected to a power pin or digital output = likely reversed
                if pin_type in ("power", "digital"):
                    faults.append({
                        "category": "wiring",
                        "severity": "error",
                        "component": pid,
                        "title": f"LED '{pid}' has reversed polarity",
                        "explanation": f"The cathode (C) of LED '{pid}' is connected to {neighbor} which is a {pin_type} pin. The cathode should connect to GND, and the anode should connect to the signal/resistor.",
                        "fix": {"type": "wiring", "description": f"Swap the anode and cathode connections of LED '{pid}'. Cathode (C) goes to GND, Anode (A) goes to the resistor/signal pin."},
                    })
                    break
    return faults


def _check_led_resistor(parts: list[dict], adjacency: dict) -> list[dict]:
    """Check if LEDs are connected directly to Arduino pins without a resistor."""
    faults = []
    parts_map = {p["id"]: p for p in parts}

    for part in parts:
        if part.get("type") not in ("wokwi-led", "wokwi-rgb-led"):
            continue
        pid = part["id"]

        # Check anode connections
        anode_pins = ["A"] if part["type"] == "wokwi-led" else ["R", "G", "B"]
        for apin in anode_pins:
            anode_key = f"{pid}:{apin}"
            has_resistor = False

            # Walk one hop from the anode - check if it connects to a resistor
            for neighbor in adjacency.get(anode_key, []):
                if ":" not in neighbor:
                    continue
                npart_id = neighbor.split(":")[0]
                if npart_id in parts_map:
                    ntype = parts_map[npart_id].get("type", "")
                    if ntype == "wokwi-resistor":
                        has_resistor = True
                        break

            # Also check cathode side for resistor
            if not has_resistor:
                cathode_key = f"{pid}:C" if part["type"] == "wokwi-led" else f"{pid}:COM"
                for neighbor in adjacency.get(cathode_key, []):
                    if ":" not in neighbor:
                        continue
                    npart_id = neighbor.split(":")[0]
                    if npart_id in parts_map and parts_map[npart_id].get("type") == "wokwi-resistor":
                        has_resistor = True
                        break

            if not has_resistor:
                # Check if it's connected to an Arduino pin (not just floating)
                for neighbor in adjacency.get(anode_key, []):
                    if ":" not in neighbor:
                        continue
                    npart_id = neighbor.split(":")[0]
                    if npart_id in parts_map and parts_map[npart_id].get("type") in ARDUINO_BOARDS:
                        faults.append({
                            "category": "wiring",
                            "severity": "error",
                            "component": pid,
                            "title": f"LED '{pid}' missing current-limiting resistor",
                            "explanation": f"LED '{pid}' anode ({apin}) is connected directly to an Arduino pin without a resistor. This can draw excessive current (>20mA), potentially damaging the LED or the Arduino pin. Typical forward current for an LED is 10-20mA.",
                            "fix": {"type": "wiring", "description": f"Add a 220Ω resistor between the Arduino pin and the LED anode ({apin})."},
                        })
                        break
    return faults


def _check_power_connections(parts: list[dict], adjacency: dict) -> list[dict]:
    """Check that components requiring power have VCC and GND connections."""
    faults = []
    parts_map = {p["id"]: p for p in parts}

    for part in parts:
        ptype = part.get("type", "")
        comp_info = COMPONENT_PINS.get(ptype)
        if not comp_info or not comp_info.get("requires_power"):
            continue
        if ptype in ("wokwi-led", "wokwi-rgb-led"):
            continue  # LEDs are checked separately

        pid = part["id"]
        pins = comp_info["pins"]

        has_power = False
        has_ground = False

        for pin_name, pin_info in pins.items():
            key = f"{pid}:{pin_name}"
            if key in adjacency:
                if pin_info.get("type") in POWER_PIN_TYPES:
                    has_power = True
                elif pin_info.get("type") in GROUND_PIN_TYPES:
                    has_ground = True

        if not has_power:
            faults.append({
                "category": "power",
                "severity": "error",
                "component": pid,
                "title": f"'{pid}' ({ptype}) missing power (VCC) connection",
                "explanation": f"Component '{pid}' requires a power supply but has no VCC/V+ pin connected. It will not function without power.",
                "fix": {"type": "wiring", "description": f"Connect the VCC/V+ pin of '{pid}' to the Arduino 5V (or 3.3V if component requires it)."},
            })
        if not has_ground:
            faults.append({
                "category": "power",
                "severity": "error",
                "component": pid,
                "title": f"'{pid}' ({ptype}) missing ground (GND) connection",
                "explanation": f"Component '{pid}' requires a ground connection but has no GND pin connected. The circuit will not be complete without ground.",
                "fix": {"type": "wiring", "description": f"Connect the GND pin of '{pid}' to Arduino GND."},
            })
    return faults


def _check_servo_pwm(parts: list[dict], adjacency: dict) -> list[dict]:
    """Check that servos are connected to PWM-capable pins."""
    faults = []
    parts_map = {p["id"]: p for p in parts}
    board_type = get_board_from_parts(parts)
    if not board_type:
        return faults
    pwm_pins = get_pwm_pins(board_type)

    for part in parts:
        if part.get("type") != "wokwi-servo":
            continue
        pid = part["id"]
        pwm_key = f"{pid}:PWM"

        for neighbor in adjacency.get(pwm_key, []):
            if ":" not in neighbor:
                continue
            npart_id, npin = neighbor.split(":", 1)
            if npart_id in parts_map and parts_map[npart_id].get("type") in ARDUINO_BOARDS:
                if npin not in pwm_pins:
                    faults.append({
                        "category": "signal",
                        "severity": "error",
                        "component": pid,
                        "title": f"Servo '{pid}' on non-PWM pin {npin}",
                        "explanation": f"Servo signal is connected to pin {npin}, which is not PWM-capable. Servos require a PWM signal for position control. PWM pins on {board_type}: {', '.join(sorted(pwm_pins))}.",
                        "fix": {"type": "wiring", "description": f"Move the servo signal wire from pin {npin} to a PWM pin (e.g., 9 or 10)."},
                    })
    return faults


def _extract_pin_usage_from_code(sketch_code: str) -> dict:
    """Extract pin usage from Arduino sketch code.

    Returns dict: {pin_ref: [(function, line_num), ...]}
    """
    usage = defaultdict(list)
    lines = sketch_code.split("\n")

    pin_functions = [
        "pinMode", "digitalWrite", "digitalRead",
        "analogWrite", "analogRead", "analogReference",
        "tone", "noTone", "pulseIn", "shiftOut", "shiftIn",
    ]
    pattern = re.compile(
        r"(" + "|".join(pin_functions) + r")\s*\(\s*(\w+)"
    )

    for i, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        for match in pattern.finditer(line):
            func = match.group(1)
            pin_ref = match.group(2)
            usage[pin_ref].append((func, i))

    return dict(usage)


def _extract_defines_and_constants(sketch_code: str) -> dict:
    """Extract #define and const int pin assignments from code."""
    assignments = {}
    for line in sketch_code.split("\n"):
        # #define PIN_NAME value
        m = re.match(r"#define\s+(\w+)\s+(\d+)", line.strip())
        if m:
            assignments[m.group(1)] = m.group(2)
            continue
        # const int pinName = value;
        m = re.match(r"(?:const\s+)?int\s+(\w+)\s*=\s*(\d+)\s*;", line.strip())
        if m:
            assignments[m.group(1)] = m.group(2)

    return assignments


def _check_code_wiring_mismatch(sketch_code: str, diagram: dict) -> list[dict]:
    """Cross-reference code pin usage against wiring."""
    faults = []
    parts = diagram.get("parts", [])
    connections = diagram.get("connections", [])
    board_type = get_board_from_parts(parts)
    if not board_type:
        return faults

    # Find which Arduino pins are wired
    board_ids = {p["id"] for p in parts if p.get("type") in ARDUINO_BOARDS}
    wired_pins = set()
    for conn in connections:
        if len(conn) < 2:
            continue
        for endpoint in [conn[0], conn[1]]:
            if ":" not in endpoint:
                continue
            part_id, pin = endpoint.split(":", 1)
            if part_id in board_ids:
                wired_pins.add(pin)

    # Get pin usage from code
    pin_usage = _extract_pin_usage_from_code(sketch_code)
    defines = _extract_defines_and_constants(sketch_code)

    # Resolve symbolic names to pin numbers
    resolved_usage = {}
    for ref, calls in pin_usage.items():
        resolved = defines.get(ref, ref)
        resolved_usage[resolved] = calls

    # Check: code uses pins not in wiring
    for pin_ref, calls in resolved_usage.items():
        if pin_ref.isdigit() or pin_ref.startswith("A"):
            if pin_ref not in wired_pins:
                func_names = [f"{fn}() at line {ln}" for fn, ln in calls]
                faults.append({
                    "category": "cross_reference",
                    "severity": "warning",
                    "component": f"pin {pin_ref}",
                    "title": f"Code uses pin {pin_ref} but it's not wired in the circuit",
                    "explanation": f"The code calls {', '.join(func_names)} with pin {pin_ref}, but this pin has no connection in the diagram.json wiring.",
                    "fix": {"type": "both", "description": f"Either add a wire to pin {pin_ref} in the circuit, or update the code to use a wired pin."},
                })

    # Check: wired signal pins not used in code
    signal_wired = {p for p in wired_pins if p.isdigit() or p.startswith("A")}
    code_pins = {defines.get(ref, ref) for ref in pin_usage.keys()}
    for pin in signal_wired:
        if pin not in code_pins and pin not in ("GND.1", "GND.2", "GND.3", "5V", "3.3V", "VIN", "AREF", "RESET"):
            faults.append({
                "category": "cross_reference",
                "severity": "info",
                "component": f"pin {pin}",
                "title": f"Pin {pin} is wired but never used in code",
                "explanation": f"Arduino pin {pin} has a connection in the circuit but is never referenced in the sketch code.",
                "fix": {"type": "code", "description": f"Add code to use pin {pin}, or remove the wire if unneeded."},
            })

    return faults


def _check_missing_pinmode(sketch_code: str) -> list[dict]:
    """Check for digitalWrite/digitalRead without corresponding pinMode."""
    faults = []
    pin_usage = _extract_pin_usage_from_code(sketch_code)
    defines = _extract_defines_and_constants(sketch_code)

    pinmode_pins = set()
    io_pins = defaultdict(list)

    for ref, calls in pin_usage.items():
        resolved = defines.get(ref, ref)
        for func, line in calls:
            if func == "pinMode":
                pinmode_pins.add(resolved)
            elif func in ("digitalWrite", "digitalRead"):
                io_pins[resolved].append((func, line))

    for pin, calls in io_pins.items():
        if pin not in pinmode_pins and pin not in defines.values():
            # Only flag if the pin is a numeric reference or a known define
            if pin.isdigit() or pin.startswith("A"):
                func_names = [f"{fn}() at line {ln}" for fn, ln in calls]
                faults.append({
                    "category": "code",
                    "severity": "warning",
                    "component": f"pin {pin}",
                    "title": f"Missing pinMode() for pin {pin}",
                    "explanation": f"The code calls {', '.join(func_names)} but never sets pinMode({pin}, ...) in setup(). While Arduino defaults pins to INPUT, explicitly setting the mode is best practice and required for OUTPUT.",
                    "fix": {"type": "code", "description": f"Add pinMode({pin}, OUTPUT) or pinMode({pin}, INPUT) in setup()."},
                })

    return faults


def _check_serial_begin(sketch_code: str) -> list[dict]:
    """Check if Serial is used without Serial.begin()."""
    faults = []
    has_serial_use = bool(re.search(r"Serial\.(print|println|write|read|available|parseInt|parseFloat)", sketch_code))
    has_serial_begin = bool(re.search(r"Serial\.begin\s*\(", sketch_code))

    if has_serial_use and not has_serial_begin:
        faults.append({
            "category": "code",
            "severity": "error",
            "component": "Serial",
            "title": "Serial used without Serial.begin()",
            "explanation": "The code uses Serial functions (print, read, etc.) but never calls Serial.begin(baud_rate) in setup(). Serial communication will not work.",
            "fix": {"type": "code", "description": "Add Serial.begin(9600); (or appropriate baud rate) at the start of setup()."},
        })
    return faults


# ---------------------------------------------------------------------------
# Main analysis functions
# ---------------------------------------------------------------------------

def analyze_wiring_rules(diagram: dict) -> list[dict]:
    """Run all rule-based wiring and circuit checks. Returns list of fault dicts."""
    parts = diagram.get("parts", [])
    connections = diagram.get("connections", [])
    adjacency, connected_parts, pin_connections = _build_connection_graph(diagram)

    faults = []
    faults.extend(_check_unconnected_parts(parts, connected_parts))
    faults.extend(_check_invalid_pins(parts, connections))
    faults.extend(_check_led_polarity(parts, adjacency))
    faults.extend(_check_led_resistor(parts, adjacency))
    faults.extend(_check_power_connections(parts, adjacency))
    faults.extend(_check_servo_pwm(parts, adjacency))
    return faults


def analyze_code_rules(sketch_code: str, diagram: dict) -> list[dict]:
    """Run all rule-based code checks. Returns list of fault dicts."""
    if not sketch_code.strip():
        return []

    faults = []
    faults.extend(_check_code_wiring_mismatch(sketch_code, diagram))
    faults.extend(_check_missing_pinmode(sketch_code))
    faults.extend(_check_serial_begin(sketch_code))
    return faults


async def analyze_wiring(diagram: dict) -> dict:
    """Full wiring analysis: rule-based + OpenAI."""
    parts = diagram.get("parts", [])
    part_types = [p.get("type", "") for p in parts]
    component_ref = get_relevant_knowledge(part_types)

    # Rule-based analysis
    rule_faults = analyze_wiring_rules(diagram)
    rule_findings_text = json.dumps(rule_faults, indent=2) if rule_faults else "None"

    # OpenAI deep analysis
    ai_faults = []
    try:
        system_msg, user_msg = build_circuit_analysis_prompt(
            diagram_json=json.dumps(diagram, indent=2),
            component_reference=component_ref,
            rule_findings=rule_findings_text,
        )
        ai_response = await call_openai(system_msg, user_msg)
        ai_faults = parse_openai_json(ai_response)
    except Exception as e:
        ai_faults = [{
            "category": "system",
            "severity": "info",
            "component": "analyzer",
            "title": "AI analysis unavailable",
            "explanation": f"OpenAI analysis could not be performed: {str(e)}. Showing rule-based results only.",
            "fix": {"type": "none", "description": "Check OPENAI_API_KEY and try again."},
        }]

    all_faults = rule_faults + ai_faults
    return _build_report(diagram, "", all_faults)


async def analyze_code(sketch_code: str, diagram: dict) -> dict:
    """Full code analysis: rule-based + OpenAI."""
    parts = diagram.get("parts", []) if diagram else []
    part_types = [p.get("type", "") for p in parts]
    component_ref = get_relevant_knowledge(part_types) if part_types else "No circuit provided."

    rule_faults = analyze_code_rules(sketch_code, diagram or {})
    rule_findings_text = json.dumps(rule_faults, indent=2) if rule_faults else "None"

    ai_faults = []
    try:
        system_msg, user_msg = build_code_analysis_prompt(
            sketch_code=sketch_code,
            diagram_json=json.dumps(diagram, indent=2) if diagram else "",
            component_reference=component_ref,
            rule_findings=rule_findings_text,
        )
        ai_response = await call_openai(system_msg, user_msg)
        ai_faults = parse_openai_json(ai_response)
    except Exception as e:
        ai_faults = [{
            "category": "system",
            "severity": "info",
            "component": "analyzer",
            "title": "AI code analysis unavailable",
            "explanation": f"OpenAI analysis could not be performed: {str(e)}. Showing rule-based results only.",
            "fix": {"type": "none", "description": "Check OPENAI_API_KEY and try again."},
        }]

    all_faults = rule_faults + ai_faults
    return _build_report(diagram or {}, sketch_code, all_faults)


async def full_analysis(diagram: dict, sketch_code: str) -> dict:
    """Complete analysis: wiring + code + cross-reference."""
    parts = diagram.get("parts", [])
    part_types = [p.get("type", "") for p in parts]
    component_ref = get_relevant_knowledge(part_types)

    # Rule-based checks (all categories)
    wiring_faults = analyze_wiring_rules(diagram)
    code_faults = analyze_code_rules(sketch_code, diagram) if sketch_code else []
    all_rule_faults = wiring_faults + code_faults
    rule_findings_text = json.dumps(all_rule_faults, indent=2) if all_rule_faults else "None"

    diagram_json_str = json.dumps(diagram, indent=2)

    # OpenAI deep analysis (circuit + code in parallel)
    ai_faults = []

    try:
        # Circuit analysis
        sys1, usr1 = build_circuit_analysis_prompt(diagram_json_str, component_ref, rule_findings_text)
        circuit_response = await call_openai(sys1, usr1)
        ai_faults.extend(parse_openai_json(circuit_response))
    except Exception:
        pass

    if sketch_code:
        try:
            sys2, usr2 = build_code_analysis_prompt(sketch_code, diagram_json_str, component_ref, rule_findings_text)
            code_response = await call_openai(sys2, usr2)
            ai_faults.extend(parse_openai_json(code_response))
        except Exception:
            pass

    all_faults = all_rule_faults + ai_faults
    return _build_report(diagram, sketch_code, all_faults)


async def suggest_fixes(fault_report: str, diagram: dict, sketch_code: str) -> dict:
    """Generate corrected code and wiring based on a fault report."""
    try:
        system_msg, user_msg = build_fix_suggestion_prompt(
            fault_report=fault_report,
            diagram_json=json.dumps(diagram, indent=2) if diagram else "",
            sketch_code=sketch_code,
        )
        response = await call_openai(system_msg, user_msg)
        result = parse_openai_json(response)
        if result:
            return result[0] if isinstance(result, list) else result
        # Try parsing as a dict directly
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        return json.loads(text)
    except Exception as e:
        return {
            "error": f"Failed to generate fix suggestions: {str(e)}",
            "wiring_changes": [],
            "corrected_connections": None,
            "corrected_code": None,
            "summary": f"Fix suggestion failed: {str(e)}",
        }


def _build_report(diagram: dict, sketch_code: str, faults: list[dict]) -> dict:
    """Build the standardized analysis report."""
    # Deduplicate faults by title
    seen_titles = set()
    unique_faults = []
    for f in faults:
        title = f.get("title", "")
        if title not in seen_titles:
            seen_titles.add(title)
            unique_faults.append(f)

    errors = sum(1 for f in unique_faults if f.get("severity") == "error")
    warnings = sum(1 for f in unique_faults if f.get("severity") == "warning")
    infos = sum(1 for f in unique_faults if f.get("severity") == "info")

    return {
        "diagram": diagram,
        "sketch_code": sketch_code,
        "faults": unique_faults,
        "summary": {
            "total_faults": len(unique_faults),
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
        },
    }

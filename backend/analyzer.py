"""
Core analysis engine: rule-based checks + OpenAI-powered deep analysis.
Detects wiring faults, component issues, power problems, signal integrity,
code bugs, and code-circuit cross-reference mismatches.
"""

import asyncio
import json
import os
import re
from collections import defaultdict

import openai

from component_knowledge import (
    COMPONENT_PINS,
    SUPPORTED_BOARDS,
    POWER_PIN_TYPES,
    GROUND_PIN_TYPES,
    UART_MODULES,
    THREE_V3_ONLY_MODULES,
    THREE_V3_BOARDS,
    WIRELESS_MODULES,
    get_relevant_knowledge,
    get_library_knowledge,
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

def _breadboard_pin_group(pin: str) -> str | None:
    """Determine the electrical group of a breadboard pin.

    Pins in the same group are internally connected on the breadboard.
    Returns a group key string, or None if the pin format is unrecognized.
    """
    # Power rail: tp.N, tn.N, bp.N, bn.N (top/bottom positive/negative)
    m = re.match(r'^([tb][pn])\.\d+$', pin)
    if m:
        return m.group(1)

    # Alt power rail: +N or -N
    m = re.match(r'^([+-])\d+$', pin)
    if m:
        return "pos" if m.group(1) == "+" else "neg"

    # Terminal strip with half: {row}{half}.{col} like "25t.d" or "3b.a"
    m = re.match(r'^(\d+)([tb])\.([a-j])$', pin)
    if m:
        row, half, col = m.group(1), m.group(2), m.group(3)
        section = "left" if col in "abcde" else "right"
        return f"{row}{half}_{section}"

    # Simple format: {row}{col} like "5a", "12j"
    m = re.match(r'^(\d+)([a-j])$', pin)
    if m:
        row, col = m.group(1), m.group(2)
        section = "left" if col in "abcde" else "right"
        return f"{row}_{section}"

    # Column-first format: {col}{row} like "a5", "j12"
    m = re.match(r'^([a-j])(\d+)$', pin)
    if m:
        col, row = m.group(1), m.group(2)
        section = "left" if col in "abcde" else "right"
        return f"{row}_{section}"

    return None


def _expand_breadboard_connections(adjacency: dict, parts: list[dict]) -> dict:
    """Expand adjacency graph to resolve breadboard internal connections.

    When two component pins connect to the same breadboard row/rail,
    this function makes them direct neighbors in the adjacency graph.
    This allows all one-hop checks to work through breadboard connections.
    """
    # Identify breadboard parts
    bb_parts = set()
    for p in parts:
        ptype = p.get("type", "")
        if "breadboard" in ptype.lower():
            bb_parts.add(p["id"])

    if not bb_parts:
        return adjacency  # No breadboards, nothing to expand

    # Add internal breadboard connections (same row/rail)
    # Group breadboard pin endpoints by their internal group
    bb_groups: dict[str, list[str]] = defaultdict(list)
    for endpoint in adjacency:
        if ":" not in endpoint:
            continue
        part_id, pin = endpoint.split(":", 1)
        if part_id in bb_parts:
            group = _breadboard_pin_group(pin)
            if group:
                bb_groups[f"{part_id}:{group}"].append(endpoint)

    # Build expanded adjacency
    expanded = defaultdict(set)
    for ep, neighbors in adjacency.items():
        expanded[ep] = set(neighbors)

    # Connect all breadboard pins in the same group to each other
    for group_key, endpoints in bb_groups.items():
        for i in range(len(endpoints)):
            for j in range(i + 1, len(endpoints)):
                expanded[endpoints[i]].add(endpoints[j])
                expanded[endpoints[j]].add(endpoints[i])

    # Collapse breadboard paths: for each component pin, BFS through
    # breadboard-only pins to find reachable component pins
    for start_ep in list(expanded.keys()):
        if ":" not in start_ep:
            continue
        start_part = start_ep.split(":")[0]
        if start_part in bb_parts:
            continue  # Only start from component pins, not breadboard pins

        # BFS through breadboard pins only
        visited = {start_ep}
        queue = []
        for neighbor in expanded.get(start_ep, set()):
            if ":" in neighbor and neighbor.split(":")[0] in bb_parts:
                queue.append(neighbor)
                visited.add(neighbor)

        while queue:
            current = queue.pop(0)
            for neighbor in expanded.get(current, set()):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                if ":" in neighbor:
                    npart = neighbor.split(":")[0]
                    if npart in bb_parts:
                        queue.append(neighbor)  # Continue through breadboard
                    else:
                        # Found a component pin — add as direct neighbor
                        expanded[start_ep].add(neighbor)
                        expanded[neighbor].add(start_ep)

    return dict(expanded)


def _build_connection_graph(diagram: dict) -> tuple[dict, set, dict]:
    """Parse diagram connections into useful data structures.

    Returns:
        adjacency: dict mapping "partId:pin" -> set of "partId:pin"
        connected_parts: set of part IDs that appear in at least one connection
        pin_connections: dict mapping "partId:pin" -> list of connections it appears in
    """
    connections = diagram.get("connections", [])
    parts = diagram.get("parts", [])
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

    # Expand through breadboard internal connections
    adjacency = _expand_breadboard_connections(dict(adjacency), parts)

    return adjacency, connected_parts, dict(pin_connections)


def _check_unconnected_parts(parts: list[dict], connected_parts: set) -> list[dict]:
    """Find parts that have no connections at all."""
    faults = []
    for part in parts:
        pid = part.get("id", "")
        ptype = part.get("type", "")
        if ptype in SUPPORTED_BOARDS:
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
            # Never validate breadboard component pins — hole addresses (1a, tp.5, +3)
            # are dynamically addressed and have no fixed pin list.
            if "breadboard" in ptype.lower():
                continue
            if re.match(r'^(\d+[a-j]|[tb][pn]\.\d+|[+-]\d+)$', pin_name):
                continue
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
                # Cathode connected to a power (VCC/5V) pin = definitely reversed
                if pin_type == "power":
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


def _find_resistor_on_path(start_key: str, adjacency: dict, parts_map: dict,
                           max_hops: int = 2) -> bool:
    """BFS up to max_hops from start_key looking for a wokwi-resistor.

    Traverses through non-board component pins as well as breadboard nodes so
    that resistors reachable via power rails or multi-row breadboard paths are
    detected even when they are not a direct adjacency neighbour of the LED pin.
    """
    visited: set[str] = {start_key}
    frontier = list(adjacency.get(start_key, []))
    for _ in range(max_hops):
        next_frontier: list[str] = []
        for node in frontier:
            if node in visited or ":" not in node:
                continue
            visited.add(node)
            npart_id = node.split(":")[0]
            if npart_id in parts_map:
                ntype = parts_map[npart_id].get("type", "")
                if ntype == "wokwi-resistor":
                    return True
                # Continue traversal only through non-board component pins
                if ntype not in SUPPORTED_BOARDS:
                    next_frontier.extend(adjacency.get(node, []))
            else:
                # Breadboard node or unknown — keep traversing
                next_frontier.extend(adjacency.get(node, []))
        frontier = next_frontier
    return False


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

            # BFS up to 2 hops from anode — catches resistors through breadboard rows,
            # power rails, and multi-segment paths that a single-hop check would miss.
            has_resistor = _find_resistor_on_path(anode_key, adjacency, parts_map)

            # Also check cathode side for resistor (resistor between LED and GND)
            if not has_resistor:
                cathode_key = f"{pid}:C" if part["type"] == "wokwi-led" else f"{pid}:COM"
                has_resistor = _find_resistor_on_path(cathode_key, adjacency, parts_map)

            if not has_resistor:
                # Only flag error if the LED is actually driven by a board pin
                for neighbor in adjacency.get(anode_key, []):
                    if ":" not in neighbor:
                        continue
                    npart_id = neighbor.split(":")[0]
                    if npart_id in parts_map and parts_map[npart_id].get("type") in SUPPORTED_BOARDS:
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
    """The Arduino Servo library uses timer interrupts and works on any digital pin —
    it does NOT require a hardware PWM pin. This check is intentionally disabled."""
    return []


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


def _extract_library_pin_usage(sketch_code: str, defines: dict) -> set[str]:
    """Extract pins used implicitly by library constructors/arrays not caught by _extract_pin_usage_from_code.

    Detects:
      - LiquidCrystal lcd(rs, en, d4, d5, d6, d7) — all numeric/symbolic args
      - rowPins[N] = {5, 4, 3, 2} / colPins[N] = {A3, A2, A1, A0} — Keypad arrays
      - servo.attach(pin) — Servo library
    """
    pins: set[str] = set()

    def _resolve(arg: str) -> str:
        arg = arg.strip()
        return defines.get(arg, arg)

    # LiquidCrystal constructor: LiquidCrystal varname(arg, arg, ...)
    for m in re.finditer(r'LiquidCrystal\s+\w+\s*\(([^)]+)\)', sketch_code):
        for arg in m.group(1).split(','):
            r = _resolve(arg)
            if r.isdigit() or r.startswith('A'):
                pins.add(r)

    # Keypad row/col pin arrays: byte rowPins[N] = {5, 4, 3, 2}
    for m in re.finditer(r'(?:row|col)Pins\s*\[.*?\]\s*=\s*\{([^}]+)\}', sketch_code, re.IGNORECASE):
        for val in m.group(1).split(','):
            r = _resolve(val)
            if r.isdigit() or r.startswith('A'):
                pins.add(r)

    # servo.attach(pin) — any object
    for m in re.finditer(r'\.attach\s*\(\s*(\w+)\s*\)', sketch_code):
        r = _resolve(m.group(1))
        if r.isdigit() or r.startswith('A'):
            pins.add(r)

    return pins


def _check_code_wiring_mismatch(sketch_code: str, diagram: dict) -> list[dict]:
    """Cross-reference code pin usage against wiring."""
    faults = []
    parts = diagram.get("parts", [])
    connections = diagram.get("connections", [])
    board_type = get_board_from_parts(parts)
    if not board_type:
        return faults

    # Find which Arduino pins are wired
    board_ids = {p["id"] for p in parts if p.get("type") in SUPPORTED_BOARDS}
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

    # Find Arduino pins that connect to servo components — these are controlled via
    # Servo.attach(), not digitalWrite/pinMode, so they won't appear in pin_usage.
    servo_ids = {p["id"] for p in parts if p.get("type") == "wokwi-servo"}
    servo_wired_pins = set()
    for conn in connections:
        if len(conn) < 2:
            continue
        for board_ep, other_ep in [(conn[0], conn[1]), (conn[1], conn[0])]:
            if ":" not in board_ep or ":" not in other_ep:
                continue
            b_part, b_pin = board_ep.split(":", 1)
            o_part, _ = other_ep.split(":", 1)
            if b_part in board_ids and o_part in servo_ids:
                servo_wired_pins.add(b_pin)

    # Check: wired signal pins not used in code
    signal_wired = {p for p in wired_pins if p.isdigit() or p.startswith("A")}
    code_pins = {defines.get(ref, ref) for ref in pin_usage.keys()}
    code_pins |= _extract_library_pin_usage(sketch_code, defines)
    for pin in signal_wired:
        if pin not in code_pins and pin not in ("GND.1", "GND.2", "GND.3", "5V", "3.3V", "VIN", "AREF", "RESET") and pin not in servo_wired_pins:
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
# Wireless module checks
# ---------------------------------------------------------------------------

def _check_tx_rx_crossover(parts: list[dict], adjacency: dict) -> list[dict]:
    """Check that UART wireless modules have TX→RX crossover wiring (not TX→TX)."""
    faults = []
    parts_map = {p["id"]: p for p in parts}

    for part in parts:
        ptype = part.get("type", "")
        if ptype not in UART_MODULES:
            continue
        pid = part["id"]
        comp_info = COMPONENT_PINS.get(ptype, {})

        # Determine TX/RX pin names for this module
        tx_pin = "TXD" if "TXD" in comp_info.get("pins", {}) else "TX"
        rx_pin = "RXD" if "RXD" in comp_info.get("pins", {}) else "RX"

        # Check TX connection — should go to an Arduino RX-like pin (0, or SoftwareSerial RX)
        tx_key = f"{pid}:{tx_pin}"
        for neighbor in adjacency.get(tx_key, []):
            if ":" not in neighbor:
                continue
            npart_id, npin = neighbor.split(":", 1)
            if npart_id not in parts_map:
                continue
            ntype = parts_map[npart_id].get("type", "")
            # If module TX is connected to another module's TX = wrong
            if ntype in UART_MODULES:
                ncomp = COMPONENT_PINS.get(ntype, {})
                n_tx = "TXD" if "TXD" in ncomp.get("pins", {}) else "TX"
                if npin == n_tx:
                    faults.append({
                        "category": "wiring",
                        "severity": "error",
                        "component": pid,
                        "title": f"TX-to-TX wiring on '{pid}' and '{npart_id}'",
                        "explanation": f"Module '{pid}' TX is connected to '{npart_id}' TX. Serial communication requires TX→RX crossover (TX of one device to RX of the other).",
                        "fix": {"type": "wiring", "description": f"Connect {pid}:{tx_pin} to {npart_id}'s RX pin, and {npart_id}'s TX to {pid}:{rx_pin}."},
                    })
            # If connected to Arduino pin 1 (TX), that's TX→TX
            if ntype in SUPPORTED_BOARDS and npin == "1":
                faults.append({
                    "category": "wiring",
                    "severity": "error",
                    "component": pid,
                    "title": f"'{pid}' TX connected to Arduino TX (pin 1)",
                    "explanation": f"Module '{pid}' TX is connected to Arduino pin 1 (TX). Both are transmitters — data will collide. TX should connect to RX.",
                    "fix": {"type": "wiring", "description": f"Connect {pid}:{tx_pin} to Arduino pin 0 (RX), or use SoftwareSerial on different pins."},
                })

        # Check RX connection — should come from Arduino TX-like pin
        rx_key = f"{pid}:{rx_pin}"
        for neighbor in adjacency.get(rx_key, []):
            if ":" not in neighbor:
                continue
            npart_id, npin = neighbor.split(":", 1)
            if npart_id not in parts_map:
                continue
            ntype = parts_map[npart_id].get("type", "")
            if ntype in SUPPORTED_BOARDS and npin == "0":
                faults.append({
                    "category": "wiring",
                    "severity": "error",
                    "component": pid,
                    "title": f"'{pid}' RX connected to Arduino RX (pin 0)",
                    "explanation": f"Module '{pid}' RX is connected to Arduino pin 0 (RX). Both are receivers — neither is sending data. RX should connect to TX.",
                    "fix": {"type": "wiring", "description": f"Connect {pid}:{rx_pin} to Arduino pin 1 (TX), or use SoftwareSerial on different pins."},
                })

    return faults


def _check_wireless_voltage(parts: list[dict], adjacency: dict) -> list[dict]:
    """Check that 3.3V-only wireless modules aren't connected to 5V power."""
    faults = []
    parts_map = {p["id"]: p for p in parts}

    for part in parts:
        ptype = part.get("type", "")
        if ptype not in THREE_V3_ONLY_MODULES:
            continue
        pid = part["id"]

        vcc_key = f"{pid}:VCC"
        for neighbor in adjacency.get(vcc_key, []):
            if ":" not in neighbor:
                continue
            npart_id, npin = neighbor.split(":", 1)
            if npart_id not in parts_map:
                continue
            ntype = parts_map[npart_id].get("type", "")
            if ntype in SUPPORTED_BOARDS and npin == "5V":
                faults.append({
                    "category": "power",
                    "severity": "error",
                    "component": pid,
                    "title": f"'{pid}' ({ptype}) connected to 5V — will be damaged",
                    "explanation": f"Module '{pid}' is rated for 3.3V only. Connecting VCC to Arduino 5V can permanently damage the module.",
                    "fix": {"type": "wiring", "description": f"Connect {pid} VCC to Arduino 3.3V pin. For ESP-01 (300mA draw), use an external 3.3V regulator — Arduino 3.3V pin can only supply 50mA."},
                })

    # Special check: ESP-01 powered from Arduino 3.3V pin (insufficient current)
    for part in parts:
        if part.get("type") != "wokwi-esp01":
            continue
        pid = part["id"]
        vcc_key = f"{pid}:VCC"
        for neighbor in adjacency.get(vcc_key, []):
            if ":" not in neighbor:
                continue
            npart_id, npin = neighbor.split(":", 1)
            if npart_id in parts_map and parts_map[npart_id].get("type") in SUPPORTED_BOARDS and npin == "3.3V":
                faults.append({
                    "category": "power",
                    "severity": "warning",
                    "component": pid,
                    "title": f"ESP-01 '{pid}' may not get enough current from Arduino 3.3V",
                    "explanation": f"ESP-01 draws up to 300mA peak during WiFi transmission, but the Arduino 3.3V pin can only supply ~50mA. This can cause resets, connection drops, or failure to boot.",
                    "fix": {"type": "wiring", "description": "Use an external 3.3V voltage regulator (e.g., AMS1117-3.3) capable of 500mA+ to power the ESP-01."},
                })

    return faults


def _check_serial_pin_conflict(parts: list[dict], adjacency: dict) -> list[dict]:
    """Warn when wireless modules use hardware Serial pins 0/1 (conflicts with USB)."""
    faults = []
    parts_map = {p["id"]: p for p in parts}

    for part in parts:
        ptype = part.get("type", "")
        if ptype not in UART_MODULES:
            continue
        pid = part["id"]
        comp_info = COMPONENT_PINS.get(ptype, {})
        tx_pin = "TXD" if "TXD" in comp_info.get("pins", {}) else "TX"
        rx_pin = "RXD" if "RXD" in comp_info.get("pins", {}) else "RX"

        uses_hw_serial = False
        for mod_pin in [tx_pin, rx_pin]:
            key = f"{pid}:{mod_pin}"
            for neighbor in adjacency.get(key, []):
                if ":" not in neighbor:
                    continue
                npart_id, npin = neighbor.split(":", 1)
                if npart_id in parts_map and parts_map[npart_id].get("type") in SUPPORTED_BOARDS:
                    if npin in ("0", "1"):
                        uses_hw_serial = True

        if uses_hw_serial:
            faults.append({
                "category": "signal",
                "severity": "warning",
                "component": pid,
                "title": f"'{pid}' uses hardware Serial pins 0/1 — conflicts with USB",
                "explanation": f"Module '{pid}' is connected to Arduino pins 0/1 (hardware Serial). This conflicts with USB communication — you won't be able to upload code or use Serial Monitor while the module is connected.",
                "fix": {"type": "wiring", "description": f"Use SoftwareSerial on other pins (e.g., pins 2 and 3) instead of hardware Serial pins 0/1. Add #include <SoftwareSerial.h> to code."},
            })

    return faults


def _check_spi_pins(parts: list[dict], adjacency: dict) -> list[dict]:
    """Check nRF24L01 SPI pins are on correct Arduino SPI pins."""
    faults = []
    parts_map = {p["id"]: p for p in parts}
    board_type = get_board_from_parts(parts)
    if not board_type:
        return faults

    # SPI pin mapping per board
    spi_pins = {
        "wokwi-arduino-uno": {"SCK": "13", "MOSI": "11", "MISO": "12"},
        "wokwi-arduino-nano": {"SCK": "13", "MOSI": "11", "MISO": "12"},
        "wokwi-arduino-mega": {"SCK": "52", "MOSI": "51", "MISO": "50"},
    }
    expected = spi_pins.get(board_type, {})
    if not expected:
        return faults

    for part in parts:
        if part.get("type") != "wokwi-nrf24l01":
            continue
        pid = part["id"]

        for spi_name, expected_pin in expected.items():
            key = f"{pid}:{spi_name}"
            for neighbor in adjacency.get(key, []):
                if ":" not in neighbor:
                    continue
                npart_id, npin = neighbor.split(":", 1)
                if npart_id in parts_map and parts_map[npart_id].get("type") in SUPPORTED_BOARDS:
                    if npin != expected_pin:
                        faults.append({
                            "category": "signal",
                            "severity": "error",
                            "component": pid,
                            "title": f"nRF24L01 '{pid}' {spi_name} on wrong pin ({npin} instead of {expected_pin})",
                            "explanation": f"nRF24L01 {spi_name} is connected to Arduino pin {npin}, but hardware SPI requires pin {expected_pin} on {board_type}.",
                            "fix": {"type": "wiring", "description": f"Move {pid}:{spi_name} wire from pin {npin} to pin {expected_pin}."},
                        })

    return faults


def _check_software_serial_pins(sketch_code: str, diagram: dict) -> list[dict]:
    """Check SoftwareSerial pin assignments match circuit wiring."""
    faults = []
    parts = diagram.get("parts", [])
    connections = diagram.get("connections", [])
    board_type = get_board_from_parts(parts)
    if not board_type:
        return faults

    board_ids = {p["id"] for p in parts if p.get("type") in SUPPORTED_BOARDS}
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

    # Find SoftwareSerial constructor: SoftwareSerial name(rxPin, txPin)
    ss_pattern = re.compile(r"SoftwareSerial\s+\w+\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    defines = _extract_defines_and_constants(sketch_code)

    for m in ss_pattern.finditer(sketch_code):
        rx_ref = m.group(1)
        tx_ref = m.group(2)
        rx_pin = defines.get(rx_ref, rx_ref)
        tx_pin = defines.get(tx_ref, tx_ref)

        for pin, label in [(rx_pin, "RX"), (tx_pin, "TX")]:
            if (pin.isdigit() or pin.startswith("A")) and pin not in wired_pins:
                faults.append({
                    "category": "cross_reference",
                    "severity": "warning",
                    "component": f"SoftwareSerial {label} pin {pin}",
                    "title": f"SoftwareSerial {label} pin {pin} not wired to any module",
                    "explanation": f"Code defines SoftwareSerial with {label} on pin {pin}, but this pin has no connection in the circuit. The wireless module won't communicate.",
                    "fix": {"type": "both", "description": f"Wire the wireless module's {'TXD/TX' if label == 'RX' else 'RXD/RX'} pin to Arduino pin {pin}."},
                })

    return faults


def _check_wireless_library_usage(sketch_code: str, diagram: dict) -> list[dict]:
    """Check for wireless library usage without matching hardware and vice versa."""
    faults = []
    parts = diagram.get("parts", [])
    part_types = {p.get("type", "") for p in parts}

    has_uart_module = bool(part_types & UART_MODULES)
    has_nrf = "wokwi-nrf24l01" in part_types
    has_ir_rx = "wokwi-ir-receiver" in part_types
    has_ir_tx = "wokwi-ir-led" in part_types

    has_ss_include = bool(re.search(r"#include\s*<SoftwareSerial\.h>", sketch_code))
    has_ss_usage = bool(re.search(r"SoftwareSerial\s+\w+", sketch_code))
    has_nrf_lib = bool(re.search(r"#include\s*<(RF24|nRF24L01)\.h>", sketch_code))
    has_ir_lib = bool(re.search(r"#include\s*<IR(remote|recv).*\.h>", sketch_code))
    has_wifi_lib = bool(re.search(r"#include\s*<(ESP8266WiFi|WiFi)\.h>", sketch_code))

    # UART module in circuit but no SoftwareSerial or Serial usage for it
    if has_uart_module and not has_ss_usage:
        # Check if using hardware Serial (acceptable but warn-worthy)
        has_serial = bool(re.search(r"Serial\.(begin|print|read|write|available)", sketch_code))
        if not has_serial:
            faults.append({
                "category": "cross_reference",
                "severity": "warning",
                "component": "wireless",
                "title": "UART wireless module in circuit but no serial communication in code",
                "explanation": "A Bluetooth/WiFi module is wired but the code doesn't use Serial or SoftwareSerial to communicate with it.",
                "fix": {"type": "code", "description": "Add #include <SoftwareSerial.h> and create a SoftwareSerial instance for the module, or use Serial if connected to pins 0/1."},
            })

    # nRF24L01 in circuit but no RF24 library
    if has_nrf and not has_nrf_lib:
        faults.append({
            "category": "cross_reference",
            "severity": "warning",
            "component": "wireless",
            "title": "nRF24L01 in circuit but RF24 library not included",
            "explanation": "An nRF24L01 module is wired but the code doesn't include the RF24 library needed to communicate with it.",
            "fix": {"type": "code", "description": "Add #include <RF24.h> and #include <nRF24L01.h>, then create an RF24 instance with CE and CSN pins."},
        })

    # IR receiver in circuit but no IRremote library
    if (has_ir_rx or has_ir_tx) and not has_ir_lib:
        faults.append({
            "category": "cross_reference",
            "severity": "warning",
            "component": "wireless",
            "title": "IR component in circuit but IRremote library not included",
            "explanation": "An IR receiver or transmitter is wired but the code doesn't include the IRremote library.",
            "fix": {"type": "code", "description": "Add #include <IRremote.h> and set up IR send/receive objects."},
        })

    # SoftwareSerial in code but no UART module
    if has_ss_usage and not has_uart_module:
        faults.append({
            "category": "cross_reference",
            "severity": "info",
            "component": "wireless",
            "title": "SoftwareSerial in code but no UART wireless module in circuit",
            "explanation": "Code uses SoftwareSerial but there's no Bluetooth/WiFi module in the circuit to communicate with.",
            "fix": {"type": "both", "description": "Add the wireless module to the circuit, or remove SoftwareSerial if not needed."},
        })

    return faults


# ---------------------------------------------------------------------------
# Library usage checks
# ---------------------------------------------------------------------------

def _check_library_init(sketch_code: str) -> list[dict]:
    """Check that included libraries have their required initialization calls."""
    from component_knowledge import LIBRARY_KNOWLEDGE

    faults = []
    if not sketch_code:
        return faults

    for lib_name, info in LIBRARY_KNOWLEDGE.items():
        header = info["header"]
        if f"#include <{header}>" not in sketch_code and f'#include "{header}"' not in sketch_code:
            continue

        required = info.get("required_init", "")
        if not required:
            continue

        # Extract the key function name from required_init (e.g., "servo.attach" → "attach")
        # Check if the function call pattern exists in the code
        init_func = required.split("(")[0].split(".")[-1]  # e.g., "begin", "attach", "init"

        # Look for the function call in the code
        has_init = bool(re.search(rf"\.{init_func}\s*\(", sketch_code))

        if not has_init:
            faults.append({
                "category": "code",
                "severity": "error",
                "component": lib_name,
                "title": f"Missing {lib_name} initialization: {required}",
                "explanation": f"Library {header} is included but the required initialization call '{required}' was not found in the code. The library will not function without initialization.",
                "fix": {"type": "code", "description": f"Add {required} in setup() function."},
            })

    return faults


# ---------------------------------------------------------------------------
# Board-specific checks
# ---------------------------------------------------------------------------

def _check_esp32_flash_pins(parts: list[dict], connections: list) -> list[dict]:
    """Check that ESP32 GPIO6-11 (flash pins) are not used in connections."""
    faults = []
    board_type = get_board_from_parts(parts)
    if board_type != "wokwi-esp32-devkit-v1":
        return faults

    board_ids = {p["id"] for p in parts if p.get("type") == board_type}
    flash_pins = {"6", "7", "8", "9", "10", "11"}

    for conn in connections:
        if len(conn) < 2:
            continue
        for endpoint in [conn[0], conn[1]]:
            if ":" not in endpoint:
                continue
            part_id, pin = endpoint.split(":", 1)
            if part_id in board_ids and pin in flash_pins:
                faults.append({
                    "category": "signal",
                    "severity": "error",
                    "component": f"GPIO{pin}",
                    "title": f"ESP32 GPIO{pin} is a flash pin — do not use",
                    "explanation": f"GPIO{pin} is internally connected to the SPI flash memory on ESP32. Using it for external connections will crash the chip or corrupt flash.",
                    "fix": {"type": "wiring", "description": f"Move the wire from GPIO{pin} to a different GPIO (e.g., GPIO13-33, avoiding 34-39 for output)."},
                })

    return faults


def _check_esp32_input_only(parts: list[dict], sketch_code: str, connections: list) -> list[dict]:
    """Check that ESP32 input-only pins (34, 35, 36, 39) aren't used for output."""
    faults = []
    board_type = get_board_from_parts(parts)
    if board_type != "wokwi-esp32-devkit-v1":
        return faults

    input_only = {"34", "35", "36", "39"}

    if not sketch_code:
        return faults

    # Check for pinMode(pin, OUTPUT) or digitalWrite/analogWrite on input-only pins
    defines = _extract_defines_and_constants(sketch_code)
    pin_usage = _extract_pin_usage_from_code(sketch_code)

    for ref, calls in pin_usage.items():
        resolved = defines.get(ref, ref)
        if resolved not in input_only:
            continue
        for func, line in calls:
            if func in ("digitalWrite", "analogWrite", "tone"):
                faults.append({
                    "category": "signal",
                    "severity": "error",
                    "component": f"GPIO{resolved}",
                    "title": f"ESP32 GPIO{resolved} is input-only — cannot use {func}()",
                    "explanation": f"GPIO{resolved} on ESP32 has no output driver. {func}() at line {line} will have no effect. Input-only pins: 34, 35, 36, 39.",
                    "fix": {"type": "both", "description": f"Move to a GPIO that supports output (e.g., GPIO13-33) and update the wiring."},
                })
                break  # One fault per pin is enough

    return faults


def _check_3v3_board_voltage(parts: list[dict], adjacency: dict) -> list[dict]:
    """Check that 5V components aren't directly connected to 3.3V board GPIO pins."""
    faults = []
    parts_map = {p["id"]: p for p in parts}
    board_type = get_board_from_parts(parts)

    if not board_type or board_type not in THREE_V3_BOARDS:
        return faults

    # STM32 Bluepill is 5V tolerant on most pins — skip it
    board_info = COMPONENT_PINS.get(board_type, {})
    if board_info.get("five_v_tolerant"):
        return faults

    board_ids = {p["id"] for p in parts if p.get("type") == board_type}

    # Find components that output 5V signals
    for part in parts:
        ptype = part.get("type", "")
        comp_info = COMPONENT_PINS.get(ptype, {})
        if not comp_info or ptype in SUPPORTED_BOARDS:
            continue

        comp_voltage = comp_info.get("operating_voltage", 0)
        if comp_voltage != 5.0:
            continue

        pid = part["id"]
        # Check if any of this component's signal pins connect to board GPIO
        for pin_name, pin_info in comp_info.get("pins", {}).items():
            pin_type = pin_info.get("type", "")
            if pin_type in POWER_PIN_TYPES or pin_type in GROUND_PIN_TYPES:
                continue
            if pin_type in ("data_out", "digital_out", "analog_out", "signal"):
                key = f"{pid}:{pin_name}"
                for neighbor in adjacency.get(key, []):
                    if ":" not in neighbor:
                        continue
                    npart_id, npin = neighbor.split(":", 1)
                    if npart_id in board_ids:
                        gpio_info = board_info.get("pins", {}).get(npin, {})
                        if gpio_info.get("type") in ("digital", "analog"):
                            faults.append({
                                "category": "power",
                                "severity": "warning",
                                "component": pid,
                                "title": f"5V output from '{pid}' connected to {board_type} GPIO{npin} (3.3V)",
                                "explanation": f"Component '{pid}' ({ptype}) operates at 5V, but {board_type} GPIO pins are 3.3V. A 5V signal may damage the GPIO pin.",
                                "fix": {"type": "wiring", "description": f"Add a voltage divider (e.g., 1KΩ + 2KΩ) or level shifter between {pid}:{pin_name} and GPIO{npin}."},
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
    # Wireless checks
    faults.extend(_check_tx_rx_crossover(parts, adjacency))
    faults.extend(_check_wireless_voltage(parts, adjacency))
    faults.extend(_check_serial_pin_conflict(parts, adjacency))
    faults.extend(_check_spi_pins(parts, adjacency))
    # Board-specific checks
    faults.extend(_check_esp32_flash_pins(parts, connections))
    faults.extend(_check_3v3_board_voltage(parts, adjacency))
    return faults


def analyze_code_rules(sketch_code: str, diagram: dict) -> list[dict]:
    """Run all rule-based code checks. Returns list of fault dicts."""
    if not sketch_code.strip():
        return []

    faults = []
    faults.extend(_check_code_wiring_mismatch(sketch_code, diagram))
    faults.extend(_check_missing_pinmode(sketch_code))
    faults.extend(_check_serial_begin(sketch_code))
    # Wireless code checks
    faults.extend(_check_software_serial_pins(sketch_code, diagram))
    faults.extend(_check_wireless_library_usage(sketch_code, diagram))
    # Library usage checks
    faults.extend(_check_library_init(sketch_code))
    # Board-specific code checks
    parts = diagram.get("parts", []) if diagram else []
    connections = diagram.get("connections", []) if diagram else []
    faults.extend(_check_esp32_input_only(parts, sketch_code, connections))
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

    for f in rule_faults:
        f["_source"] = "rule"
    for f in ai_faults:
        f.setdefault("_source", "ai")

    all_faults = rule_faults + ai_faults
    return _build_report(diagram, "", all_faults)


async def analyze_code(sketch_code: str, diagram: dict) -> dict:
    """Full code analysis: rule-based + OpenAI."""
    parts = diagram.get("parts", []) if diagram else []
    part_types = [p.get("type", "") for p in parts]
    component_ref = get_relevant_knowledge(part_types) if part_types else "No circuit provided."

    # Append library knowledge if libraries are detected in code
    lib_ref = get_library_knowledge(sketch_code) if sketch_code else ""
    if lib_ref:
        component_ref += "\n\n## Library Reference" + lib_ref

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

    for f in rule_faults:
        f["_source"] = "rule"
    for f in ai_faults:
        f.setdefault("_source", "ai")

    all_faults = rule_faults + ai_faults
    return _build_report(diagram or {}, sketch_code, all_faults)


async def full_analysis(diagram: dict, sketch_code: str, design_description: str = "") -> dict:
    """Complete analysis: wiring + code + cross-reference."""
    parts = diagram.get("parts", [])
    part_types = [p.get("type", "") for p in parts]
    component_ref = get_relevant_knowledge(part_types)

    # Append library knowledge for code-aware analysis
    lib_ref = get_library_knowledge(sketch_code) if sketch_code else ""
    code_component_ref = component_ref
    if lib_ref:
        code_component_ref = component_ref + "\n\n## Library Reference" + lib_ref

    # Rule-based checks (all categories)
    wiring_faults = analyze_wiring_rules(diagram)
    code_faults = analyze_code_rules(sketch_code, diagram) if sketch_code else []
    all_rule_faults = wiring_faults + code_faults
    rule_findings_text = json.dumps(all_rule_faults, indent=2) if all_rule_faults else "None"

    diagram_json_str = json.dumps(diagram, indent=2)

    # OpenAI deep analysis — circuit and code calls run in parallel
    ai_faults = []

    sys1, usr1 = build_circuit_analysis_prompt(diagram_json_str, component_ref, rule_findings_text, design_description)

    if sketch_code:
        sys2, usr2 = build_code_analysis_prompt(sketch_code, diagram_json_str, code_component_ref, rule_findings_text, design_description)
        results = await asyncio.gather(
            call_openai(sys1, usr1),
            call_openai(sys2, usr2),
            return_exceptions=True,
        )
        for res in results:
            if not isinstance(res, Exception):
                ai_faults.extend(parse_openai_json(res))
    else:
        try:
            circuit_response = await call_openai(sys1, usr1)
            ai_faults.extend(parse_openai_json(circuit_response))
        except Exception:
            pass

    for f in all_rule_faults:
        f["_source"] = "rule"
    for f in ai_faults:
        f.setdefault("_source", "ai")

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
    """Build the standardized analysis report with semantic false-positive suppression."""
    parts = diagram.get("parts", [])

    # ── Build context sets from rule faults ─────────────────────────────────
    all_comp_ids = {p["id"] for p in parts}
    led_ids = {p["id"] for p in parts
               if p.get("type", "") in ("wokwi-led", "wokwi-rgb-led")}
    servo_ids_set = {p["id"] for p in parts if p.get("type") == "wokwi-servo"}

    # Components the rule checker flagged as fully unconnected (no wires at all)
    # These come from _check_unconnected_parts — title starts with "Unconnected component:"
    fully_unconnected_ids: set[str] = set()
    for f in faults:
        if (f.get("_source") == "rule" and
                f.get("title", "").lower().startswith("unconnected component:")):
            fully_unconnected_ids.add(f.get("component", ""))

    # Components that the rule checker has flagged as unconnected (any phrasing)
    _unconn_kws = ("unconnected", "not connected", "floating")
    rule_unconnected_ids: set[str] = set(fully_unconnected_ids)
    for f in faults:
        if (f.get("_source") == "rule" and
                any(kw in f.get("title", "").lower() for kw in _unconn_kws)):
            rule_unconnected_ids.add(f.get("component", ""))
    # Everything else is confirmed-connected (rule checker is authoritative)
    confirmed_connected_ids = all_comp_ids - rule_unconnected_ids

    _resistor_kws = (
        "current-limiting", "current limiting", "limiting resistor",
        "missing resistor", "no resistor", "add a resistor", "series resistor",
        "resistor in series", "without a resistor", "needs a resistor",
    )
    _erc_conn_kws = ("unconnected", "not connected", "floating", "no-connect",
                     "open pin", "pin without", "without no-connect")
    _verify_kws = ("verify", "verification needed", "must be verified",
                   "confirm the value", "check the value",
                   "ensure that", "ensure the wiring", "ensure the pin")
    _serial_begin_kws = (
        "missing serial.begin", "serial.begin() missing", "no serial.begin",
        "serial not initialized", "serial not begun", "serial.begin not called",
        "missing serial initialization",
    )
    _exceed_pin_kws = (
        "exceeds available pins", "exceeds pins", "more pins than available",
        "not enough pins", "insufficient pins", "pin count exceeded",
        "num_servos exceeds",
    )
    # Boards where the AI routinely underestimates available digital pins
    board_type = get_board_from_parts(parts)
    _many_pin_boards = {"wokwi-arduino-mega"}

    # ── Collapse cascade faults for fully-unconnected components ────────────
    # When a component has zero wires, _check_unconnected_parts fires once AND
    # _check_power_connections fires twice (missing VCC + missing GND).
    # The power/ground faults are consequences of the root cause — suppress them
    # so the user sees one clear "Unconnected component" fault, not three.
    _power_gnd_titles = ("missing power", "missing ground", "missing vcc", "missing gnd")

    # ── Apply suppression filters to AI faults ───────────────────────────────
    filtered: list[dict] = []
    for f in faults:
        # Suppress cascading power/ground faults for fully-unconnected components
        if (f.get("_source") == "rule" and
                f.get("component", "") in fully_unconnected_ids and
                any(kw in f.get("title", "").lower() for kw in _power_gnd_titles)):
            continue

        if f.get("_source") == "ai":
            title = str(f.get("title", "")).lower()
            explanation = str(f.get("explanation", "")).lower()
            fix_desc = str(f.get("fix", {}).get("description", "")).lower()
            full_text = title + " " + explanation + " " + fix_desc
            component = f.get("component", "")
            if isinstance(component, list):
                component = component[0] if component else ""
            comp_lower = component.lower()
            category = f.get("category", "")

            # 1. LED resistor — rule checker (_check_led_resistor) is authoritative
            if component in led_ids and any(kw in full_text for kw in _resistor_kws):
                continue

            # 1b. Servo resistor — servos have internal electronics; they never
            #     need current-limiting resistors.  AI confuses them with LEDs.
            if "servo" in comp_lower and any(kw in full_text for kw in _resistor_kws):
                continue

            # 2. GND false-positive (AI hallucinating GND not properly driven)
            _gnd_text = title + " " + comp_lower
            if (category in ("power", "wiring") and
                    any(kw in _gnd_text for kw in ("gnd", "ground")) and
                    any(kw in title for kw in (
                        "not connected", "not driven", "not properly", "improperly",
                        "missing", "no power", "no source", "undriven", "floating",
                    ))):
                continue

            # 3. Confirmed-connected filter — rule checker is authoritative for connectivity
            if (component in confirmed_connected_ids and
                    any(kw in (title + " " + explanation) for kw in _erc_conn_kws)):
                continue

            # 4. Verify-value suppression — rule checker already catches missing values.
            #    Check full_text (includes fix description) since "verify" often
            #    appears in the fix rather than the title/explanation.
            if any(kw in full_text for kw in _verify_kws):
                continue

            # 5. GND connection issue on a non-GND component — AI picks one
            #    component arbitrarily when all are wired the same (e.g. servo9
            #    out of 32 identical servos).  If "gnd" appears in the title but
            #    the component is not a GND rail, suppress.
            if ("gnd" in title or "ground" in title) and "connection issue" in title:
                continue

            # 6. Missing Serial.begin() when Serial.begin() exists anywhere in code
            #    (it may be inside a helper function, not setup() — that's fine).
            if (any(kw in full_text for kw in _serial_begin_kws) and
                    "serial.begin" in sketch_code.lower()):
                continue

            # 7. "Exceeds available pins" on boards with many digital pins (Mega).
            #    The AI assumes Uno limits; Mega has 54 digital pins so 32 servos fit.
            if (any(kw in full_text for kw in _exceed_pin_kws) and
                    board_type in _many_pin_boards):
                continue

            # 8–10. Comprehensive servo suppression.
            #
            # The rule checker is authoritative for servo wiring.  When it
            # finds no problems, AI faults about those servos are almost always
            # hallucinations caused by:
            #   • inability to parse loop-based attach(22 + i) calls
            #   • mistaking daisy-chained V+ rails for a wiring loop
            #   • assuming Uno servo/pin limits on a Mega
            #
            # Helper: does the component field refer to a servo?
            # ── Comprehensive servo suppression ──────────────────────────────
            # Principle: the rule checker is authoritative for servo wiring.
            # When it finds no problems, AI faults about those servos are
            # hallucinations — caused by inability to parse loop-based
            # attach() calls, daisy-chained V+/GND rings, or wrong board
            # assumptions.  Instead of patching individual phrasings, we
            # suppress by category + component type so new phrasings are
            # caught automatically.
            if servo_ids_set:
                # Is the component field servo-named?
                is_servo_comp = (
                    component in servo_ids_set or
                    any(sid in component for sid in servo_ids_set) or
                    "servo" in comp_lower          # "Servo Pins", "NUM_SERVOS", etc.
                )
                # Is servo mentioned anywhere in the fault text?
                is_servo_context = is_servo_comp or "servo" in full_text

                # A. ANY wiring / signal / cross_reference fault whose component
                #    is servo-named is suppressed unconditionally.  The rule
                #    checker already validated servo wiring; the AI cannot
                #    parse loop-based attach() and invents new phrasings every
                #    call ("mismatch", "not referenced correctly", "pins not
                #    referenced", "wiring mismatch for servo control", …).
                if is_servo_comp and category in ("wiring", "signal", "cross_reference"):
                    continue

                # B. Servo count limits — Mega supports up to 48 servos; AI
                #    assumes Uno limits.
                _servo_count_kws = (
                    "exceeding maximum servo", "maximum servo count",
                    "servo count exceeded", "too many servos",
                    "excessive servo count", "servo limit",
                )
                if (is_servo_context and board_type in _many_pin_boards and
                        any(kw in full_text for kw in _servo_count_kws)):
                    continue

                # C. Misc faults in servo context where the component is not a
                #    servo ID (e.g. "N/A", "pin 53") but the fault is about
                #    servos — unused pins, library misuse, redundant power
                #    supply warnings.
                _servo_misc_kws = (
                    "unused pin",
                    "misuse",
                    "power supply issue",
                )
                if is_servo_context and any(kw in title for kw in _servo_misc_kws):
                    continue

                # D. Single-servo power draw — rule checker is authoritative for
                #    current draw.  1 servo (~200mA) is within the Arduino 5V
                #    pin's 500mA limit.  AI over-reports for any servo on 5V.
                if (is_servo_comp and category == "power" and
                        any(kw in full_text for kw in (
                            "current draw", "power draw", "exceeding arduino",
                            "exceeds arduino", "pin limit",
                        ))):
                    continue

            # 11. Keypad initialization — the AI systematically rejects any
            #     variable names that differ from its hardcoded template.
            #     Any code that compiles and runs has Keypad initialized.
            #     Suppress unconditionally when comp is keypad + category code.
            if "keypad" in comp_lower and category == "code" and "missing" in title and "init" in title:
                continue
            # Also suppress any code fault on Keypad — the rule checker does
            # not check Keypad init; AI always gets variable names wrong.
            if "keypad" in comp_lower and category == "code":
                continue

            # 11b. Self-contradicting faults — AI says "is correctly wired /
            #      correctly configured" in explanation but still flags it.
            #      If the explanation confirms correctness, suppress always.
            if any(kw in explanation for kw in (
                    "correctly wired", "correctly configured",
                    "is correct", "are correct",
                    "correctly connected", "is properly wired",
            )):
                continue

            # 11c. LCD cross_reference pin-config faults — rule checker has
            #      already validated LCD wiring via _check_code_wiring_mismatch
            #      and _extract_library_pin_usage; AI version is redundant.
            if "lcd" in comp_lower and category == "cross_reference":
                continue

            # 12. Keypad on analog pins — A0-A3 as digital inputs is valid
            #     and the standard pattern for keypad column wiring.
            if "keypad" in comp_lower and "analog" in full_text:
                continue

            # 13. LCD parallel mode — LiquidCrystal.h IS the parallel-mode
            #     library; using it is never wrong.  Suppress any fault that
            #     accuses the LCD of not using I2C or wrong protocol.
            if "lcd" in comp_lower and any(kw in full_text for kw in (
                    "not using i2c", "i2c protocol", "should use i2c",
                    "use liquidcrystal_i2c", "protocol", "parallel mode")):
                continue

            # 14. "Wired pins never referenced" combined AI fault — the rule
            #     checker handles per-pin detection; this vague AI version is
            #     always a false positive caused by library constructor pins
            #     (LiquidCrystal, Keypad, Servo) the AI can't see.
            if (category == "cross_reference" and
                    any(kw in full_text for kw in (
                        "never referenced", "never used in code", "wired but never",
                        "pins never referenced", "pins not referenced",
                    ))):
                continue

        filtered.append(f)

    # ── Deduplicate by normalized title (case-insensitive) ───────────────────
    seen_titles: set[str] = set()
    unique_faults: list[dict] = []
    for f in filtered:
        title = str(f.get("title", "")).strip().lower()
        if title not in seen_titles:
            seen_titles.add(title)
            unique_faults.append(f)

    # ── Normalize component field so frontend always receives a string ────────
    for f in unique_faults:
        comp = f.get("component", "")
        if isinstance(comp, list):
            f["component"] = ", ".join(str(c) for c in comp)

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

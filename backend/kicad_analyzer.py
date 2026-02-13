"""
KiCad analysis engine: rule-based ERC/DRC checks + OpenAI-powered deep analysis.
Detects schematic errors, PCB design rule violations, power issues,
signal integrity problems, and manufacturing concerns.
"""

import json
import math
from collections import defaultdict

from analyzer import call_openai, parse_openai_json
from kicad_parser import KiCadProject
from kicad_component_knowledge import (
    match_component,
    get_power_voltage,
    get_component_knowledge_text,
    DEFAULT_MFG_CONSTRAINTS,
    POWER_SYMBOLS,
)
from kicad_prompts import (
    KICAD_SCHEMATIC_ANALYSIS_SYSTEM,
    KICAD_PCB_ANALYSIS_SYSTEM,
    KICAD_FIX_SUGGESTION_SYSTEM,
    build_schematic_analysis_prompt,
    build_pcb_analysis_prompt,
    build_fix_suggestion_prompt,
)


# ---------------------------------------------------------------------------
# Schematic Rule-Based Checks (ERC)
# ---------------------------------------------------------------------------

def _check_unconnected_pins(schematic: dict) -> list[dict]:
    """Find symbol pins not connected to any wire and without a no-connect marker."""
    faults = []
    no_connects = set()
    for nc in schematic.get("no_connects", []):
        no_connects.add((round(nc[0] * 100), round(nc[1] * 100)))

    for sym in schematic.get("symbols", []):
        ref = sym.get("reference", "?")
        lib_id = sym.get("lib_id", "")
        for pin in sym.get("pins", []):
            pos = pin.get("position", (0, 0))
            pos_key = (round(pos[0] * 100), round(pos[1] * 100))

            # Check if pin is at a no-connect marker
            if pos_key in no_connects:
                continue

            # Check if pin position matches any wire endpoint, label, or other pin
            connected = _is_point_connected(pos, schematic)
            if not connected:
                pin_name = pin.get("name", "")
                pin_num = pin.get("number", "")
                pin_type = pin.get("electrical_type", "")
                # Skip power_in pins on ICs that are likely handled by the power check
                pin_desc = f"pin {pin_num}" + (f" ({pin_name})" if pin_name else "")
                faults.append({
                    "category": "erc",
                    "severity": "error" if pin_type in ("power_in", "input") else "warning",
                    "component": ref,
                    "title": f"Unconnected {pin_desc} on {ref}",
                    "explanation": (
                        f"Pin {pin_desc} of {ref} ({lib_id}) is not connected to any wire, "
                        f"label, or other component, and has no no-connect marker. "
                        f"Pin type: {pin_type}."
                    ),
                    "fix": {
                        "type": "schematic",
                        "description": f"Connect {pin_desc} of {ref} to the appropriate net, "
                                       f"or add a no-connect flag if intentionally unused.",
                    },
                })
    return faults


def _is_point_connected(pos: tuple[float, float], schematic: dict) -> bool:
    """Check if a point is connected to any wire endpoint, label, or junction."""
    px, py = round(pos[0] * 100), round(pos[1] * 100)
    tolerance = 2  # 0.02mm tolerance

    # Check wire endpoints
    for wire in schematic.get("wires", []):
        for end in ("start", "end"):
            wx, wy = wire[end]
            if abs(round(wx * 100) - px) <= tolerance and abs(round(wy * 100) - py) <= tolerance:
                return True

    # Check labels
    for label in schematic.get("labels", []):
        lx, ly = label.get("position", (0, 0))
        if abs(round(lx * 100) - px) <= tolerance and abs(round(ly * 100) - py) <= tolerance:
            return True

    # Check power symbol pins
    for psym in schematic.get("power_symbols", []):
        for pin in psym.get("pins", []):
            pp = pin.get("position", (0, 0))
            if abs(round(pp[0] * 100) - px) <= tolerance and abs(round(pp[1] * 100) - py) <= tolerance:
                return True

    return False


def _check_duplicate_references(schematic: dict) -> list[dict]:
    """Flag duplicate reference designators."""
    faults = []
    ref_count: dict[str, int] = {}
    for sym in schematic.get("symbols", []):
        ref = sym.get("reference", "")
        if not ref or ref.startswith("#"):
            continue
        ref_count[ref] = ref_count.get(ref, 0) + 1

    for ref, count in ref_count.items():
        if count > 1:
            faults.append({
                "category": "erc",
                "severity": "error",
                "component": ref,
                "title": f"Duplicate reference designator: {ref} (appears {count} times)",
                "explanation": (
                    f"Reference designator '{ref}' is used by {count} different components. "
                    f"Each component must have a unique reference."
                ),
                "fix": {
                    "type": "schematic",
                    "description": f"Run 'Annotate Schematic' in KiCad to assign unique references, "
                                   f"or manually rename the duplicate {ref} components.",
                },
            })
    return faults


def _check_missing_values(schematic: dict) -> list[dict]:
    """Flag components with empty or placeholder values."""
    faults = []
    for sym in schematic.get("symbols", []):
        ref = sym.get("reference", "")
        value = sym.get("value", "")
        lib_id = sym.get("lib_id", "")

        # Skip components where value doesn't matter
        if not ref or ref.startswith("#"):
            continue
        if any(prefix in lib_id for prefix in ["Connector", "TestPoint", "MountingHole"]):
            continue

        if not value or value in ("~", "?", "Value", lib_id.split(":")[-1] if ":" in lib_id else ""):
            info = match_component(lib_id)
            if info and "value_not_empty" in info.get("checks", []):
                faults.append({
                    "category": "component",
                    "severity": "warning",
                    "component": ref,
                    "title": f"Missing value for {ref} ({lib_id})",
                    "explanation": (
                        f"{ref} has no value specified (current value: '{value}'). "
                        f"Components like resistors and capacitors need specific values "
                        f"for the circuit to function correctly."
                    ),
                    "fix": {
                        "type": "schematic",
                        "description": f"Set the value of {ref} to the correct component value "
                                       f"(e.g., '10k' for a resistor, '100nF' for a capacitor).",
                    },
                })
    return faults


def _check_power_flag(schematic: dict) -> list[dict]:
    """Check that power nets have PWR_FLAG symbols."""
    faults = []
    nets = schematic.get("nets", {})

    # Find which nets have PWR_FLAG
    flagged_nets: set[str] = set()
    for sym in schematic.get("power_symbols", []):
        val = sym.get("value", "")
        if "PWR_FLAG" in val:
            # Find which net this PWR_FLAG is on
            for pin in sym.get("pins", []):
                pos = pin.get("position", (0, 0))
                for net_name, pins_list in nets.items():
                    flagged_nets.add(net_name)
                    break

    # Check power nets
    power_net_names = set(POWER_SYMBOLS.keys())
    for net_name in nets:
        if net_name in power_net_names and net_name not in flagged_nets:
            # Only warn for common power rails
            if net_name in ("VCC", "VDD", "+5V", "+3V3", "+3.3V", "+12V"):
                faults.append({
                    "category": "erc",
                    "severity": "warning",
                    "component": f"net {net_name}",
                    "title": f"Power net '{net_name}' may need PWR_FLAG",
                    "explanation": (
                        f"The power net '{net_name}' may need a PWR_FLAG symbol to avoid "
                        f"KiCad ERC warnings. PWR_FLAG tells the ERC that this net is "
                        f"intentionally driven by an off-sheet power source."
                    ),
                    "fix": {
                        "type": "schematic",
                        "description": f"Add a PWR_FLAG symbol connected to the '{net_name}' net.",
                    },
                })
    return faults


def _check_single_pin_nets(schematic: dict) -> list[dict]:
    """Find nets with only one connected pin (likely label typos)."""
    faults = []
    nets = schematic.get("nets", {})

    for net_name, pins in nets.items():
        if net_name.startswith("_unnamed_"):
            continue
        if len(pins) == 1:
            faults.append({
                "category": "connectivity",
                "severity": "warning",
                "component": f"net {net_name}",
                "title": f"Single-pin net '{net_name}' — possible label typo",
                "explanation": (
                    f"Net '{net_name}' has only one connected pin: {pins[0]}. "
                    f"This usually indicates a misspelled label that was meant to connect "
                    f"to another label with the correct spelling."
                ),
                "fix": {
                    "type": "schematic",
                    "description": f"Check if the label '{net_name}' is spelled correctly. "
                                   f"Look for similar net names that this should connect to.",
                },
            })
    return faults


def _check_voltage_mismatch(schematic: dict) -> list[dict]:
    """Check for voltage level mismatches between connected components."""
    faults = []
    nets = schematic.get("nets", {})

    for net_name, pin_refs in nets.items():
        # Check if this is a power net
        voltage = get_power_voltage(net_name)
        if voltage is None or voltage == 0.0:
            continue

        # Check each component on this power net
        for pin_ref in pin_refs:
            # Extract reference designator
            ref = pin_ref.split(":")[0] if ":" in pin_ref else ""
            if not ref:
                continue

            # Find the symbol
            for sym in schematic.get("symbols", []):
                if sym.get("reference") == ref:
                    lib_id = sym.get("lib_id", "")
                    info = match_component(lib_id)
                    if info and "operating_voltage" in info:
                        op_v = info["operating_voltage"]
                        max_v = op_v.get("max", 99)
                        if voltage > max_v:
                            faults.append({
                                "category": "power",
                                "severity": "error",
                                "component": ref,
                                "title": f"Voltage mismatch: {ref} on {net_name} ({voltage}V > {max_v}V max)",
                                "explanation": (
                                    f"{ref} ({lib_id}) has a maximum operating voltage of {max_v}V "
                                    f"but is connected to the {net_name} rail ({voltage}V). "
                                    f"This will likely damage the component."
                                ),
                                "fix": {
                                    "type": "schematic",
                                    "description": f"Use a level shifter or voltage regulator to supply "
                                                   f"{ref} with an appropriate voltage (<= {max_v}V), "
                                                   f"or replace it with a component rated for {voltage}V.",
                                },
                            })
                    break
    return faults


def _check_decoupling_capacitors(schematic: dict) -> list[dict]:
    """Check that ICs have decoupling capacitors on their power pins."""
    faults = []
    nets = schematic.get("nets", {})

    # Find all capacitors on each net
    cap_refs: set[str] = set()
    for sym in schematic.get("symbols", []):
        lib_id = sym.get("lib_id", "")
        if "Device:C" in lib_id or lib_id in ("Device:C_Small",):
            cap_refs.add(sym.get("reference", ""))

    nets_with_caps: set[str] = set()
    for net_name, pin_refs in nets.items():
        for pin_ref in pin_refs:
            ref = pin_ref.split(":")[0] if ":" in pin_ref else ""
            if ref in cap_refs:
                nets_with_caps.add(net_name)

    # Check each IC
    for sym in schematic.get("symbols", []):
        lib_id = sym.get("lib_id", "")
        info = match_component(lib_id)
        if not info:
            continue
        if "decoupling_caps" not in info.get("checks", []):
            continue

        ref = sym.get("reference", "")
        # Find which power nets this IC is on
        ic_power_nets: list[str] = []
        for net_name, pin_refs in nets.items():
            if get_power_voltage(net_name) is not None and get_power_voltage(net_name) > 0:
                for pin_ref in pin_refs:
                    if pin_ref.startswith(f"{ref}:"):
                        ic_power_nets.append(net_name)
                        break

        for power_net in ic_power_nets:
            if power_net not in nets_with_caps:
                faults.append({
                    "category": "power",
                    "severity": "warning",
                    "component": ref,
                    "title": f"Missing decoupling capacitor for {ref} on {power_net}",
                    "explanation": (
                        f"{ref} ({lib_id}) is connected to power net '{power_net}' but "
                        f"no decoupling capacitor was found on this net. Decoupling caps "
                        f"(100nF ceramic, placed close to the IC) are essential for stable operation."
                    ),
                    "fix": {
                        "type": "schematic",
                        "description": f"Add a 100nF ceramic capacitor between {power_net} and GND, "
                                       f"placed close to {ref}'s power pin in the schematic and PCB.",
                    },
                })
    return faults


def _check_led_resistors(schematic: dict) -> list[dict]:
    """Check that LEDs have current-limiting resistors."""
    faults = []
    nets = schematic.get("nets", {})

    # Find all resistors
    resistor_refs: set[str] = set()
    for sym in schematic.get("symbols", []):
        lib_id = sym.get("lib_id", "")
        if "Device:R" in lib_id:
            resistor_refs.add(sym.get("reference", ""))

    # Check each LED
    for sym in schematic.get("symbols", []):
        lib_id = sym.get("lib_id", "")
        if lib_id != "Device:LED":
            continue

        ref = sym.get("reference", "")
        # Check if any net connected to this LED also has a resistor
        has_resistor = False
        for net_name, pin_refs in nets.items():
            led_on_net = any(pr.startswith(f"{ref}:") for pr in pin_refs)
            if led_on_net:
                resistor_on_net = any(
                    pr.split(":")[0] in resistor_refs for pr in pin_refs
                )
                if resistor_on_net:
                    has_resistor = True
                    break

        if not has_resistor:
            faults.append({
                "category": "component",
                "severity": "error",
                "component": ref,
                "title": f"LED {ref} may be missing a current-limiting resistor",
                "explanation": (
                    f"LED {ref} does not appear to have a series current-limiting resistor. "
                    f"Without a resistor, the LED will draw excessive current and may be "
                    f"destroyed, or it may damage the driving component."
                ),
                "fix": {
                    "type": "schematic",
                    "description": f"Add a resistor in series with {ref}. Typical values: "
                                   f"220-1k ohm for 5V systems, 100-470 ohm for 3.3V systems.",
                },
            })
    return faults


# ---------------------------------------------------------------------------
# PCB Rule-Based Checks (DRC)
# ---------------------------------------------------------------------------

def _check_unrouted_nets(pcb: dict, schematic: dict | None) -> list[dict]:
    """Find nets present in the PCB netlist but with no tracks or zones."""
    faults = []
    pcb_nets = pcb.get("nets", {})
    segments = pcb.get("segments", [])
    vias = pcb.get("vias", [])
    zones = pcb.get("zones", [])

    # Collect nets that have routing
    routed_nets: set[int] = set()
    for seg in segments:
        routed_nets.add(seg.get("net", 0))
    for via in vias:
        routed_nets.add(via.get("net", 0))
    for zone in zones:
        routed_nets.add(zone.get("net", 0))

    # Also check pads — a single-pad net is "connected" if there's only one pad
    pad_count_per_net: dict[int, int] = defaultdict(int)
    for fp in pcb.get("footprints", []):
        for pad in fp.get("pads", []):
            net_num = pad.get("net", (0, ""))[0]
            pad_count_per_net[net_num] += 1

    for net_num, net_name in pcb_nets.items():
        if net_num == 0 or not net_name:
            continue  # Skip unconnected net
        if net_num not in routed_nets:
            pad_count = pad_count_per_net.get(net_num, 0)
            if pad_count >= 2:
                faults.append({
                    "category": "drc",
                    "severity": "error",
                    "component": f"net {net_name}",
                    "title": f"Unrouted net: {net_name} ({pad_count} pads, no tracks)",
                    "explanation": (
                        f"Net '{net_name}' connects {pad_count} pads but has no tracks, "
                        f"vias, or copper zones providing a connection. This is an open circuit."
                    ),
                    "fix": {
                        "type": "pcb",
                        "description": f"Route net '{net_name}' by adding tracks between its pads. "
                                       f"Use the interactive router in KiCad PCB editor.",
                    },
                })
    return faults


def _check_trace_width(pcb: dict) -> list[dict]:
    """Check trace widths against manufacturing minimums."""
    faults = []
    min_width = DEFAULT_MFG_CONSTRAINTS["min_trace_width_mm"]

    thin_count = 0
    for seg in pcb.get("segments", []):
        width = seg.get("width", 0)
        if 0 < width < min_width:
            thin_count += 1

    if thin_count > 0:
        faults.append({
            "category": "manufacturing",
            "severity": "warning",
            "component": f"{thin_count} segments",
            "title": f"{thin_count} trace segments below minimum width ({min_width}mm)",
            "explanation": (
                f"Found {thin_count} trace segments with width below the recommended "
                f"manufacturing minimum of {min_width}mm. Thin traces may cause "
                f"manufacturing defects (open circuits, over-etching)."
            ),
            "fix": {
                "type": "pcb",
                "description": f"Increase trace widths to at least {min_width}mm. "
                               f"Use Design Rules in KiCad to set minimum trace width.",
            },
        })
    return faults


def _check_via_drill_size(pcb: dict) -> list[dict]:
    """Validate via drill sizes against manufacturing constraints."""
    faults = []
    min_drill = DEFAULT_MFG_CONSTRAINTS["min_via_drill_mm"]
    min_annular = DEFAULT_MFG_CONSTRAINTS["min_via_annular_ring_mm"]

    small_drill_count = 0
    small_annular_count = 0

    for via in pcb.get("vias", []):
        drill = via.get("drill", 0)
        size = via.get("size", 0)

        if drill > 0 and drill < min_drill:
            small_drill_count += 1

        if drill > 0 and size > 0:
            annular_ring = (size - drill) / 2
            if annular_ring < min_annular:
                small_annular_count += 1

    if small_drill_count > 0:
        faults.append({
            "category": "manufacturing",
            "severity": "warning",
            "component": f"{small_drill_count} vias",
            "title": f"{small_drill_count} vias with drill size below {min_drill}mm minimum",
            "explanation": (
                f"Found {small_drill_count} vias with drill diameter below {min_drill}mm. "
                f"Very small drills increase manufacturing cost and risk of breakage."
            ),
            "fix": {
                "type": "pcb",
                "description": f"Increase via drill size to at least {min_drill}mm.",
            },
        })

    if small_annular_count > 0:
        faults.append({
            "category": "manufacturing",
            "severity": "warning",
            "component": f"{small_annular_count} vias",
            "title": f"{small_annular_count} vias with small annular ring (< {min_annular}mm)",
            "explanation": (
                f"Found {small_annular_count} vias where the annular ring (copper around "
                f"the drill hole) is less than {min_annular}mm. This can cause unreliable "
                f"connections or manufacturing rejects."
            ),
            "fix": {
                "type": "pcb",
                "description": f"Increase via pad size to ensure annular ring >= {min_annular}mm.",
            },
        })
    return faults


def _check_clearance_violations(pcb: dict) -> list[dict]:
    """Basic clearance check between track segments."""
    faults = []
    min_clearance = DEFAULT_MFG_CONSTRAINTS["min_clearance_mm"]
    segments = pcb.get("segments", [])

    # Simple proximity check between segments on the same layer but different nets
    # (full geometric check would be very complex — we do a sampling approach)
    violations = 0
    checked = 0
    max_checks = 5000  # limit for performance

    for i, seg_a in enumerate(segments):
        if checked >= max_checks:
            break
        for j in range(i + 1, min(i + 50, len(segments))):  # check nearby segments
            seg_b = segments[j]
            if seg_a.get("net") == seg_b.get("net"):
                continue
            if seg_a.get("layer") != seg_b.get("layer"):
                continue

            # Simple distance check between segment midpoints
            ax = (seg_a["start"][0] + seg_a["end"][0]) / 2
            ay = (seg_a["start"][1] + seg_a["end"][1]) / 2
            bx = (seg_b["start"][0] + seg_b["end"][0]) / 2
            by = (seg_b["start"][1] + seg_b["end"][1]) / 2

            dist = math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)
            half_widths = (seg_a.get("width", 0) + seg_b.get("width", 0)) / 2

            if dist - half_widths < min_clearance:
                violations += 1
            checked += 1

    if violations > 0:
        faults.append({
            "category": "drc",
            "severity": "warning",
            "component": f"~{violations} locations",
            "title": f"Potential clearance violations detected (~{violations} locations)",
            "explanation": (
                f"Approximately {violations} locations where trace clearance may be "
                f"below {min_clearance}mm. Run KiCad's built-in DRC for precise results."
            ),
            "fix": {
                "type": "pcb",
                "description": f"Run DRC in KiCad (Inspect -> Design Rules Check) for exact "
                               f"violations. Increase spacing between traces on different nets.",
            },
        })
    return faults


def _check_schematic_pcb_sync(schematic: dict, pcb: dict) -> list[dict]:
    """Verify schematic and PCB have matching component lists."""
    faults = []

    sch_refs: set[str] = set()
    for sym in schematic.get("symbols", []):
        ref = sym.get("reference", "")
        if ref and not ref.startswith("#"):
            sch_refs.add(ref)

    pcb_refs: set[str] = set()
    for fp in pcb.get("footprints", []):
        ref = fp.get("reference", "")
        if ref and not ref.startswith("#"):
            pcb_refs.add(ref)

    # In schematic but not PCB
    missing_in_pcb = sch_refs - pcb_refs
    if missing_in_pcb:
        faults.append({
            "category": "cross_reference",
            "severity": "error",
            "component": ", ".join(sorted(missing_in_pcb)[:5]),
            "title": f"{len(missing_in_pcb)} components in schematic but not in PCB",
            "explanation": (
                f"Components present in schematic but missing from PCB: "
                f"{', '.join(sorted(missing_in_pcb)[:10])}"
                f"{' ...' if len(missing_in_pcb) > 10 else ''}. "
                f"These need to be imported into the PCB layout."
            ),
            "fix": {
                "type": "pcb",
                "description": "Run 'Update PCB from Schematic' (Tools menu) in KiCad PCB editor.",
            },
        })

    # In PCB but not schematic
    extra_in_pcb = pcb_refs - sch_refs
    if extra_in_pcb:
        faults.append({
            "category": "cross_reference",
            "severity": "warning",
            "component": ", ".join(sorted(extra_in_pcb)[:5]),
            "title": f"{len(extra_in_pcb)} components in PCB but not in schematic",
            "explanation": (
                f"Components present in PCB but missing from schematic: "
                f"{', '.join(sorted(extra_in_pcb)[:10])}"
                f"{' ...' if len(extra_in_pcb) > 10 else ''}."
            ),
            "fix": {
                "type": "schematic",
                "description": "Add missing components to schematic or remove extra footprints from PCB.",
            },
        })

    return faults


def _check_power_traces(pcb: dict) -> list[dict]:
    """Check that power net traces are sufficiently wide."""
    faults = []
    pcb_nets = pcb.get("nets", {})
    segments = pcb.get("segments", [])

    # Identify power nets
    power_net_nums: set[int] = set()
    for net_num, net_name in pcb_nets.items():
        if net_name in POWER_SYMBOLS or net_name.startswith("+") or net_name in ("VCC", "VDD", "VBUS"):
            power_net_nums.add(net_num)

    # Check power trace widths (should be wider than signal traces)
    min_power_width = 0.5  # mm, recommended minimum for power traces
    thin_power_count = 0
    for seg in segments:
        if seg.get("net", 0) in power_net_nums:
            if seg.get("width", 0) < min_power_width:
                thin_power_count += 1

    if thin_power_count > 0:
        faults.append({
            "category": "signal",
            "severity": "warning",
            "component": f"{thin_power_count} segments",
            "title": f"{thin_power_count} power trace segments narrower than {min_power_width}mm",
            "explanation": (
                f"Found {thin_power_count} power trace segments with width below "
                f"{min_power_width}mm. Power traces carry higher current and should "
                f"be wider than signal traces to reduce voltage drop and heating."
            ),
            "fix": {
                "type": "pcb",
                "description": f"Increase power trace widths to at least {min_power_width}mm. "
                               f"For traces carrying >1A, use even wider traces (1mm+).",
            },
        })
    return faults


# ---------------------------------------------------------------------------
# Aggregate rule runners
# ---------------------------------------------------------------------------

def analyze_schematic_rules(schematic: dict) -> list[dict]:
    """Run all schematic ERC rule-based checks."""
    faults = []
    faults.extend(_check_unconnected_pins(schematic))
    faults.extend(_check_duplicate_references(schematic))
    faults.extend(_check_missing_values(schematic))
    faults.extend(_check_power_flag(schematic))
    faults.extend(_check_single_pin_nets(schematic))
    faults.extend(_check_voltage_mismatch(schematic))
    faults.extend(_check_decoupling_capacitors(schematic))
    faults.extend(_check_led_resistors(schematic))
    return faults


def analyze_pcb_rules(pcb: dict, schematic: dict | None = None) -> list[dict]:
    """Run all PCB DRC rule-based checks."""
    faults = []
    faults.extend(_check_unrouted_nets(pcb, schematic))
    faults.extend(_check_trace_width(pcb))
    faults.extend(_check_via_drill_size(pcb))
    faults.extend(_check_clearance_violations(pcb))
    faults.extend(_check_power_traces(pcb))
    if schematic:
        faults.extend(_check_schematic_pcb_sync(schematic, pcb))
    return faults


# ---------------------------------------------------------------------------
# AI-powered analysis
# ---------------------------------------------------------------------------

async def _ai_analyze_schematic(
    schematic: dict,
    rule_findings: list[dict],
) -> list[dict]:
    """Run AI analysis on schematic beyond rule-based checks."""
    component_knowledge = get_component_knowledge_text(schematic.get("symbols", []))
    user_prompt = build_schematic_analysis_prompt(schematic, component_knowledge, rule_findings)
    raw = await call_openai(KICAD_SCHEMATIC_ANALYSIS_SYSTEM, user_prompt)
    return parse_openai_json(raw)


async def _ai_analyze_pcb(
    pcb: dict,
    schematic: dict | None,
    rule_findings: list[dict],
) -> list[dict]:
    """Run AI analysis on PCB layout beyond rule-based checks."""
    user_prompt = build_pcb_analysis_prompt(pcb, schematic, rule_findings)
    raw = await call_openai(KICAD_PCB_ANALYSIS_SYSTEM, user_prompt)
    return parse_openai_json(raw)


# ---------------------------------------------------------------------------
# Main analysis functions
# ---------------------------------------------------------------------------

def _build_summary(faults: list[dict]) -> dict:
    """Build a summary dict from fault list."""
    summary = {
        "total": len(faults),
        "errors": 0,
        "warnings": 0,
        "infos": 0,
        "by_category": {},
    }
    for f in faults:
        sev = f.get("severity", "info")
        if sev == "error":
            summary["errors"] += 1
        elif sev == "warning":
            summary["warnings"] += 1
        else:
            summary["infos"] += 1

        cat = f.get("category", "other")
        summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

    return summary


async def analyze_kicad_schematic(schematic: dict, raw_content: str = "") -> dict:
    """Full schematic analysis: rule-based + AI.

    Returns a report dict with faults, summary, and source data.
    """
    rule_faults = analyze_schematic_rules(schematic)
    ai_faults = await _ai_analyze_schematic(schematic, rule_faults)
    all_faults = rule_faults + ai_faults

    return {
        "project_type": "kicad",
        "analysis_type": "schematic",
        "faults": all_faults,
        "summary": _build_summary(all_faults),
    }


async def analyze_kicad_pcb(
    pcb: dict,
    schematic: dict | None = None,
    raw_pcb: str = "",
    raw_sch: str = "",
) -> dict:
    """Full PCB analysis: rule-based + AI.

    Returns a report dict with faults, summary, and source data.
    """
    rule_faults = analyze_pcb_rules(pcb, schematic)
    ai_faults = await _ai_analyze_pcb(pcb, schematic, rule_faults)
    all_faults = rule_faults + ai_faults

    return {
        "project_type": "kicad",
        "analysis_type": "pcb",
        "faults": all_faults,
        "summary": _build_summary(all_faults),
    }


async def full_kicad_analysis(project: KiCadProject) -> dict:
    """Complete KiCad project analysis: schematic + PCB + cross-reference.

    Returns a unified report dict.
    """
    all_faults: list[dict] = []

    schematic_data = None
    pcb_data = None

    # Analyze schematic if available
    if project.schematic:
        sch_report = await analyze_kicad_schematic(project.schematic, project.raw_schematic)
        all_faults.extend(sch_report.get("faults", []))
        schematic_data = {
            "symbols_count": len(project.schematic.get("symbols", [])),
            "nets_count": len(project.schematic.get("nets", {})),
            "power_symbols_count": len(project.schematic.get("power_symbols", [])),
        }

    # Analyze PCB if available
    if project.pcb:
        pcb_report = await analyze_kicad_pcb(
            project.pcb, project.schematic, project.raw_pcb, project.raw_schematic
        )
        all_faults.extend(pcb_report.get("faults", []))
        pcb_data = {
            "footprints_count": len(project.pcb.get("footprints", [])),
            "segments_count": len(project.pcb.get("segments", [])),
            "vias_count": len(project.pcb.get("vias", [])),
            "zones_count": len(project.pcb.get("zones", [])),
        }

    report = {
        "project_type": "kicad",
        "project_name": project.project_name,
        "faults": all_faults,
        "summary": _build_summary(all_faults),
    }

    if schematic_data:
        report["schematic_info"] = schematic_data
    if pcb_data:
        report["pcb_info"] = pcb_data

    return report


async def suggest_kicad_fixes(
    fault_report: str,
    raw_sch: str = "",
    raw_pcb: str = "",
) -> dict:
    """Generate fix suggestions for KiCad issues using AI."""
    user_prompt = build_fix_suggestion_prompt(fault_report, raw_sch, raw_pcb)
    raw = await call_openai(KICAD_FIX_SUGGESTION_SYSTEM, user_prompt)
    result = parse_openai_json(raw)

    if result and isinstance(result, list):
        return result[0] if isinstance(result[0], dict) else {"suggestions": result}
    return {"suggestions": [], "summary": "Unable to generate fix suggestions."}

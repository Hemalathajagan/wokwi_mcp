"""
KiCad file parser: S-expression tokenizer and parsers for .kicad_sch,
.kicad_pcb, and .kicad_pro files.

Supports KiCad 6/7/8 file formats.
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# S-expression tokenizer
# ---------------------------------------------------------------------------

def tokenize_sexpr(text: str) -> list:
    """Parse a KiCad S-expression string into nested Python lists.

    Example:
        '(kicad_sch (version 20231120) (symbol "R1"))' ->
        ['kicad_sch', ['version', '20231120'], ['symbol', 'R1']]
    """
    tokens: list = []
    stack: list[list] = [tokens]
    i = 0
    n = len(text)

    while i < n:
        c = text[i]
        if c == '(':
            new_list: list = []
            stack[-1].append(new_list)
            stack.append(new_list)
            i += 1
        elif c == ')':
            if len(stack) > 1:
                stack.pop()
            i += 1
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == '\\':
                    j += 1
                j += 1
            stack[-1].append(text[i + 1:j])
            i = j + 1
        elif c in ' \t\n\r':
            i += 1
        else:
            j = i
            while j < n and text[j] not in '() \t\n\r"':
                j += 1
            stack[-1].append(text[i:j])
            i = j

    return tokens[0] if len(tokens) == 1 else tokens


def _find_nodes(sexpr: list, tag: str) -> list[list]:
    """Find all child nodes matching a given tag name."""
    results = []
    for item in sexpr:
        if isinstance(item, list) and len(item) > 0 and item[0] == tag:
            results.append(item)
    return results


def _find_node(sexpr: list, tag: str) -> list | None:
    """Find the first child node matching a given tag name."""
    for item in sexpr:
        if isinstance(item, list) and len(item) > 0 and item[0] == tag:
            return item
    return None


def _get_value(sexpr: list, tag: str, default: Any = None) -> Any:
    """Get the first value after a tag name."""
    node = _find_node(sexpr, tag)
    if node and len(node) > 1:
        return node[1]
    return default


def _get_xy(node: list) -> tuple[float, float]:
    """Extract (x, y) from a node like ['at', '100', '50'] or ['at', '100', '50', '90']."""
    if len(node) >= 3:
        return (float(node[1]), float(node[2]))
    return (0.0, 0.0)


def _get_xyz(node: list) -> tuple[float, float, float]:
    """Extract (x, y, rotation) from an 'at' node."""
    x = float(node[1]) if len(node) > 1 else 0.0
    y = float(node[2]) if len(node) > 2 else 0.0
    rot = float(node[3]) if len(node) > 3 else 0.0
    return (x, y, rot)


# ---------------------------------------------------------------------------
# Coordinate matching utilities
# ---------------------------------------------------------------------------

COORD_TOLERANCE = 0.02  # mm tolerance for matching pin/wire endpoints


def _coords_match(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Check if two coordinates are close enough to be considered the same point."""
    return abs(a[0] - b[0]) < COORD_TOLERANCE and abs(a[1] - b[1]) < COORD_TOLERANCE


def _rotate_point(x: float, y: float, angle_deg: float) -> tuple[float, float]:
    """Rotate a point around the origin by angle_deg degrees."""
    if angle_deg == 0:
        return (x, y)
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)


# ---------------------------------------------------------------------------
# Schematic parser (.kicad_sch)
# ---------------------------------------------------------------------------

def _parse_lib_symbol_pins(lib_symbol: list, unit: int = 0) -> list[dict]:
    """Extract pin definitions from a lib_symbols symbol definition.

    Args:
        lib_symbol: The S-expression list for the symbol.
        unit: The unit number this sub-symbol belongs to (0 = shared/top-level).
    """
    pins = []
    for item in lib_symbol:
        if isinstance(item, list) and len(item) > 0:
            if item[0] == 'pin':
                pin_info: dict[str, Any] = {
                    "electrical_type": item[1] if len(item) > 1 else "passive",
                    "shape": item[2] if len(item) > 2 else "",
                    "unit": unit,
                }
                at_node = _find_node(item, 'at')
                if at_node:
                    pin_info["x"] = float(at_node[1]) if len(at_node) > 1 else 0.0
                    pin_info["y"] = float(at_node[2]) if len(at_node) > 2 else 0.0
                    pin_info["rotation"] = float(at_node[3]) if len(at_node) > 3 else 0.0
                else:
                    pin_info["x"] = 0.0
                    pin_info["y"] = 0.0
                    pin_info["rotation"] = 0.0
                length_node = _find_node(item, 'length')
                pin_info["length"] = float(length_node[1]) if length_node and len(length_node) > 1 else 2.54
                name_node = _find_node(item, 'name')
                pin_info["name"] = name_node[1] if name_node and len(name_node) > 1 else ""
                number_node = _find_node(item, 'number')
                pin_info["number"] = number_node[1] if number_node and len(number_node) > 1 else ""
                pins.append(pin_info)
            elif item[0] == 'symbol':
                # Sub-symbol (unit) — parse unit number from name
                # KiCad sub-symbol names follow: "LibId_UnitNum_StyleNum"
                sub_name = item[1] if len(item) > 1 else ""
                sub_unit = 0
                parts = sub_name.rsplit("_", 2)
                if len(parts) >= 3:
                    try:
                        sub_unit = int(parts[-2])
                    except ValueError:
                        sub_unit = 0
                pins.extend(_parse_lib_symbol_pins(item, unit=sub_unit))
    return pins


def _compute_pin_endpoint(pin: dict) -> tuple[float, float]:
    """Compute the connection endpoint of a pin (tip of the pin line)."""
    length = pin.get("length", 2.54)
    rot = pin.get("rotation", 0.0)
    dx, dy = _rotate_point(length, 0, -rot)
    return (pin["x"] + dx, pin["y"] + dy)


def _compute_absolute_pin_position(
    symbol_x: float, symbol_y: float, symbol_rot: float,
    mirror_x: bool, mirror_y: bool,
    pin_endpoint_x: float, pin_endpoint_y: float,
) -> tuple[float, float]:
    """Transform a pin endpoint from symbol-local coords to schematic global coords."""
    px, py = pin_endpoint_x, pin_endpoint_y
    if mirror_x:
        px = -px
    if mirror_y:
        py = -py
    rx, ry = _rotate_point(px, py, -symbol_rot)
    return (symbol_x + rx, symbol_y + ry)


def parse_kicad_sch(content: str) -> dict:
    """Parse a .kicad_sch file into a structured dictionary.

    Returns:
        {
            "version": str,
            "symbols": [...],        # component instances
            "wires": [...],          # wire segments
            "labels": [...],         # net labels (local, global, hierarchical)
            "junctions": [...],      # junction points
            "no_connects": [...],    # no-connect markers
            "power_symbols": [...],  # power port symbols
            "lib_symbols": {...},    # library symbol definitions
            "nets": {...},           # derived net connectivity
        }
    """
    sexpr = tokenize_sexpr(content)

    result: dict[str, Any] = {
        "version": _get_value(sexpr, 'version', ''),
        "symbols": [],
        "wires": [],
        "labels": [],
        "junctions": [],
        "no_connects": [],
        "power_symbols": [],
        "lib_symbols": {},
        "nets": {},
    }

    # Parse lib_symbols
    lib_symbols_node = _find_node(sexpr, 'lib_symbols')
    if lib_symbols_node:
        for sym_node in _find_nodes(lib_symbols_node, 'symbol'):
            if len(sym_node) > 1:
                lib_id = sym_node[1]
                pins = _parse_lib_symbol_pins(sym_node)
                power_node = _find_node(sym_node, 'power')
                is_power = power_node is not None
                result["lib_symbols"][lib_id] = {
                    "lib_id": lib_id,
                    "pins": pins,
                    "is_power": is_power,
                }

    # Parse symbols (component instances)
    for sym_node in _find_nodes(sexpr, 'symbol'):
        if len(sym_node) < 2:
            continue

        lib_id_node = _find_node(sym_node, 'lib_id')
        lib_id = lib_id_node[1] if lib_id_node and len(lib_id_node) > 1 else ""

        at_node = _find_node(sym_node, 'at')
        x, y, rot = _get_xyz(at_node) if at_node else (0.0, 0.0, 0.0)

        mirror_node = _find_node(sym_node, 'mirror')
        mirror_x = False
        mirror_y = False
        if mirror_node:
            for m in mirror_node[1:]:
                if m == 'x':
                    mirror_x = True
                elif m == 'y':
                    mirror_y = True

        unit_node = _find_node(sym_node, 'unit')
        unit = int(unit_node[1]) if unit_node and len(unit_node) > 1 else 1

        uuid_node = _find_node(sym_node, 'uuid')
        uuid = uuid_node[1] if uuid_node and len(uuid_node) > 1 else ""

        # Extract properties (reference, value, footprint, etc.)
        properties: dict[str, str] = {}
        for prop_node in _find_nodes(sym_node, 'property'):
            if len(prop_node) >= 3:
                properties[prop_node[1]] = prop_node[2]

        reference = properties.get("Reference", "")
        value = properties.get("Value", "")
        footprint = properties.get("Footprint", "")

        # Determine if this is a power symbol
        lib_sym = result["lib_symbols"].get(lib_id, {})
        is_power = lib_sym.get("is_power", False)

        # Compute absolute pin positions (filter by unit for multi-unit symbols)
        lib_pins = lib_sym.get("pins", [])
        abs_pins = []
        for pin in lib_pins:
            pin_unit = pin.get("unit", 0)
            if pin_unit != 0 and pin_unit != unit:
                continue
            endpoint = _compute_pin_endpoint(pin)
            abs_pos = _compute_absolute_pin_position(
                x, y, rot, mirror_x, mirror_y,
                endpoint[0], endpoint[1],
            )
            abs_pins.append({
                "name": pin.get("name", ""),
                "number": pin.get("number", ""),
                "electrical_type": pin.get("electrical_type", "passive"),
                "position": abs_pos,
            })

        symbol_data = {
            "lib_id": lib_id,
            "reference": reference,
            "value": value,
            "footprint": footprint,
            "unit": unit,
            "uuid": uuid,
            "at": (x, y, rot),
            "mirror_x": mirror_x,
            "mirror_y": mirror_y,
            "properties": properties,
            "pins": abs_pins,
            "is_power": is_power,
        }

        if is_power:
            result["power_symbols"].append(symbol_data)
        else:
            result["symbols"].append(symbol_data)

    # Parse wires
    for wire_node in _find_nodes(sexpr, 'wire'):
        pts_node = _find_node(wire_node, 'pts')
        if pts_node:
            xy_nodes = _find_nodes(pts_node, 'xy')
            points = [_get_xy(xy) for xy in xy_nodes]
            if len(points) >= 2:
                result["wires"].append({
                    "start": points[0],
                    "end": points[1],
                })

    # Parse labels
    for label_type in ['label', 'global_label', 'hierarchical_label']:
        for label_node in _find_nodes(sexpr, label_type):
            if len(label_node) >= 2:
                at_node = _find_node(label_node, 'at')
                pos = _get_xy(at_node) if at_node else (0.0, 0.0)
                result["labels"].append({
                    "name": label_node[1],
                    "type": label_type.replace('_label', '').replace('label', 'local'),
                    "position": pos,
                })

    # Parse junctions
    for junc_node in _find_nodes(sexpr, 'junction'):
        at_node = _find_node(junc_node, 'at')
        if at_node:
            result["junctions"].append(_get_xy(at_node))

    # Parse no-connect markers
    for nc_node in _find_nodes(sexpr, 'no_connect'):
        at_node = _find_node(nc_node, 'at')
        if at_node:
            result["no_connects"].append(_get_xy(at_node))

    # Build net connectivity
    result["nets"] = _build_net_connectivity(result)

    return result


def _build_net_connectivity(schematic: dict) -> dict:
    """Build net connectivity by matching wire endpoints, pins, labels, and junctions.

    Returns dict mapping net names to lists of connected pin references.
    """
    # Build a graph: each point connects to other points via wires
    # Then group by labels and power symbols to name the nets

    # Collect all connection points and their associated items
    point_items: dict[tuple[int, int], list[dict]] = {}

    def _round_coord(pos: tuple[float, float]) -> tuple[int, int]:
        """Round coordinates to integer mils for matching."""
        return (round(pos[0] * 100), round(pos[1] * 100))

    def _add_point(pos: tuple[float, float], item: dict):
        key = _round_coord(pos)
        if key not in point_items:
            point_items[key] = []
        point_items[key].append(item)

    # Add wire endpoints
    for wire in schematic["wires"]:
        _add_point(wire["start"], {"type": "wire", "wire": wire, "end": "start"})
        _add_point(wire["end"], {"type": "wire", "wire": wire, "end": "end"})

    # Add symbol pin positions
    for sym in schematic["symbols"]:
        for pin in sym["pins"]:
            _add_point(pin["position"], {
                "type": "pin",
                "reference": sym["reference"],
                "pin_name": pin["name"],
                "pin_number": pin["number"],
                "electrical_type": pin["electrical_type"],
                "lib_id": sym["lib_id"],
            })

    # Add power symbol pins
    for sym in schematic["power_symbols"]:
        for pin in sym["pins"]:
            _add_point(pin["position"], {
                "type": "power",
                "net_name": sym["value"],
                "reference": sym["reference"],
            })

    # Add labels
    for label in schematic["labels"]:
        _add_point(label["position"], {
            "type": "label",
            "net_name": label["name"],
            "label_type": label["type"],
        })

    # Add junctions (just mark that wires connect at these points)
    for junc in schematic["junctions"]:
        _add_point(junc, {"type": "junction"})

    # Build adjacency via wires: two points connected by the same wire are in the same group
    # Use union-find to group connected points
    parent: dict[tuple[int, int], tuple[int, int]] = {}

    def _find(p: tuple[int, int]) -> tuple[int, int]:
        if p not in parent:
            parent[p] = p
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    def _union(a: tuple[int, int], b: tuple[int, int]):
        ra, rb = _find(a), _find(b)
        if ra != rb:
            parent[ra] = rb

    # Union wire endpoints
    for wire in schematic["wires"]:
        a = _round_coord(wire["start"])
        b = _round_coord(wire["end"])
        _union(a, b)

    # Union points at the same location (pin at wire endpoint, etc.)
    all_points = list(point_items.keys())
    for pt in all_points:
        _find(pt)  # ensure all points are in parent

    # Group by connected component
    groups: dict[tuple[int, int], list[dict]] = {}
    for pt, items in point_items.items():
        root = _find(pt)
        if root not in groups:
            groups[root] = []
        groups[root].extend(items)

    # Name each net group
    nets: dict[str, list[str]] = {}
    unnamed_count = 0

    for _root, items in groups.items():
        # Find net name from labels or power symbols
        net_name = None
        for item in items:
            if item["type"] in ("label", "power") and "net_name" in item:
                net_name = item["net_name"]
                break

        if net_name is None:
            unnamed_count += 1
            net_name = f"_unnamed_net_{unnamed_count}"

        # Collect pin references
        pin_refs = []
        for item in items:
            if item["type"] == "pin":
                ref = f"{item['reference']}:{item['pin_number']}"
                if item["pin_name"]:
                    ref += f"({item['pin_name']})"
                pin_refs.append(ref)

        if pin_refs:
            if net_name in nets:
                nets[net_name].extend(pin_refs)
            else:
                nets[net_name] = pin_refs

    return nets


# ---------------------------------------------------------------------------
# PCB parser (.kicad_pcb)
# ---------------------------------------------------------------------------

def parse_kicad_pcb(content: str) -> dict:
    """Parse a .kicad_pcb file into a structured dictionary.

    Returns:
        {
            "version": str,
            "layers": [...],
            "nets": {net_number: net_name},
            "footprints": [...],
            "segments": [...],
            "vias": [...],
            "zones": [...],
            "setup": {...},
        }
    """
    sexpr = tokenize_sexpr(content)

    result: dict[str, Any] = {
        "version": _get_value(sexpr, 'version', ''),
        "layers": [],
        "nets": {},
        "footprints": [],
        "segments": [],
        "vias": [],
        "zones": [],
        "setup": {},
    }

    # Parse layers
    layers_node = _find_node(sexpr, 'layers')
    if layers_node:
        for item in layers_node[1:]:
            if isinstance(item, list) and len(item) >= 3:
                result["layers"].append({
                    "ordinal": int(item[0]) if item[0].isdigit() else 0,
                    "name": item[1],
                    "type": item[2],
                })

    # Parse nets
    for net_node in _find_nodes(sexpr, 'net'):
        if len(net_node) >= 3:
            try:
                net_num = int(net_node[1])
                net_name = net_node[2]
                result["nets"][net_num] = net_name
            except (ValueError, IndexError):
                pass

    # Parse setup / design rules
    setup_node = _find_node(sexpr, 'setup')
    if setup_node:
        design_rules: dict[str, Any] = {}
        # Pad-to-mask clearance
        val = _get_value(setup_node, 'pad_to_mask_clearance')
        if val:
            design_rules["pad_to_mask_clearance"] = float(val)
        # Pad-to-paste ratio
        val = _get_value(setup_node, 'pad_to_paste_clearance')
        if val:
            design_rules["pad_to_paste_clearance"] = float(val)
        result["setup"] = design_rules

    # Parse footprints
    for fp_node in _find_nodes(sexpr, 'footprint'):
        if len(fp_node) < 2:
            continue

        library = fp_node[1]
        at_node = _find_node(fp_node, 'at')
        x, y, rot = _get_xyz(at_node) if at_node else (0.0, 0.0, 0.0)
        layer = _get_value(fp_node, 'layer', 'F.Cu')

        # Properties
        properties: dict[str, str] = {}
        for prop_node in _find_nodes(fp_node, 'property'):
            if len(prop_node) >= 3:
                properties[prop_node[1]] = prop_node[2]

        # Also check fp_text for reference and value (older format)
        reference = properties.get("Reference", "")
        value = properties.get("Value", "")
        for fp_text_node in _find_nodes(fp_node, 'fp_text'):
            if len(fp_text_node) >= 3:
                if fp_text_node[1] == 'reference':
                    reference = reference or fp_text_node[2]
                elif fp_text_node[1] == 'value':
                    value = value or fp_text_node[2]

        # Parse pads
        pads = []
        for pad_node in _find_nodes(fp_node, 'pad'):
            if len(pad_node) < 3:
                continue
            pad_number = pad_node[1]
            pad_type = pad_node[2]  # smd, thru_hole, np_thru_hole, connect
            pad_shape = pad_node[3] if len(pad_node) > 3 else ""

            pad_at = _find_node(pad_node, 'at')
            pad_x, pad_y, pad_rot = _get_xyz(pad_at) if pad_at else (0.0, 0.0, 0.0)

            pad_size_node = _find_node(pad_node, 'size')
            pad_size = _get_xy(pad_size_node) if pad_size_node else (0.0, 0.0)

            pad_drill_node = _find_node(pad_node, 'drill')
            pad_drill = float(pad_drill_node[1]) if pad_drill_node and len(pad_drill_node) > 1 else 0.0

            pad_net_node = _find_node(pad_node, 'net')
            pad_net_num = int(pad_net_node[1]) if pad_net_node and len(pad_net_node) > 1 else 0
            pad_net_name = pad_net_node[2] if pad_net_node and len(pad_net_node) > 2 else ""

            pad_layers_node = _find_node(pad_node, 'layers')
            pad_layers = pad_layers_node[1:] if pad_layers_node else []

            pads.append({
                "number": pad_number,
                "type": pad_type,
                "shape": pad_shape,
                "at": (pad_x, pad_y, pad_rot),
                "size": pad_size,
                "drill": pad_drill,
                "net": (pad_net_num, pad_net_name),
                "layers": pad_layers,
            })

        result["footprints"].append({
            "reference": reference,
            "value": value,
            "library": library,
            "layer": layer,
            "at": (x, y, rot),
            "properties": properties,
            "pads": pads,
        })

    # Parse track segments
    for seg_node in _find_nodes(sexpr, 'segment'):
        start_node = _find_node(seg_node, 'start')
        end_node = _find_node(seg_node, 'end')
        width = _get_value(seg_node, 'width', '0')
        layer = _get_value(seg_node, 'layer', '')
        net = _get_value(seg_node, 'net', '0')

        if start_node and end_node:
            result["segments"].append({
                "start": _get_xy(start_node),
                "end": _get_xy(end_node),
                "width": float(width),
                "layer": layer,
                "net": int(net),
            })

    # Parse vias
    for via_node in _find_nodes(sexpr, 'via'):
        at_node = _find_node(via_node, 'at')
        size = _get_value(via_node, 'size', '0')
        drill = _get_value(via_node, 'drill', '0')
        net = _get_value(via_node, 'net', '0')
        layers_node = _find_node(via_node, 'layers')
        layers = layers_node[1:] if layers_node else []

        if at_node:
            result["vias"].append({
                "at": _get_xy(at_node),
                "size": float(size),
                "drill": float(drill),
                "net": int(net),
                "layers": layers,
            })

    # Parse zones (copper fills)
    for zone_node in _find_nodes(sexpr, 'zone'):
        net_node = _find_node(zone_node, 'net')
        net_num = int(net_node[1]) if net_node and len(net_node) > 1 else 0
        net_name_node = _find_node(zone_node, 'net_name')
        net_name = net_name_node[1] if net_name_node and len(net_name_node) > 1 else ""
        layer = _get_value(zone_node, 'layer', '')
        # Also handle 'layers' for multi-layer zones
        layers_node = _find_node(zone_node, 'layers')
        layers = layers_node[1:] if layers_node else ([layer] if layer else [])

        result["zones"].append({
            "net": net_num,
            "net_name": net_name,
            "layers": layers,
        })

    return result


# ---------------------------------------------------------------------------
# Project settings parser (.kicad_pro)
# ---------------------------------------------------------------------------

def parse_kicad_pro(content: str) -> dict:
    """Parse a .kicad_pro file (JSON format since KiCad 6)."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# KiCadProject container
# ---------------------------------------------------------------------------

@dataclass
class KiCadProject:
    """Container for a parsed KiCad project."""
    project_name: str
    schematic: dict | None = None
    pcb: dict | None = None
    project_settings: dict | None = None
    raw_schematic: str = ""
    raw_pcb: str = ""
    source_path: str | None = None


# ---------------------------------------------------------------------------
# File loading helpers
# ---------------------------------------------------------------------------

def load_from_path(project_path: str) -> KiCadProject:
    """Load a KiCad project from a local directory path.

    Reads .kicad_sch, .kicad_pcb, and .kicad_pro files from the directory.
    """
    p = Path(project_path)
    if not p.exists():
        raise ValueError(f"Path does not exist: {project_path}")

    if p.is_file():
        # Single file provided — detect type
        p_dir = p.parent
        p_ext = p.suffix.lower()
    else:
        p_dir = p
        p_ext = None

    sch_files = list(p_dir.glob("*.kicad_sch"))
    pcb_files = list(p_dir.glob("*.kicad_pcb"))
    pro_files = list(p_dir.glob("*.kicad_pro"))

    if not sch_files and not pcb_files:
        raise ValueError(
            f"No .kicad_sch or .kicad_pcb files found in: {p_dir}"
        )

    raw_sch = ""
    schematic = None
    if sch_files:
        raw_sch = sch_files[0].read_text(encoding="utf-8")
        schematic = parse_kicad_sch(raw_sch)

    raw_pcb = ""
    pcb = None
    if pcb_files:
        raw_pcb = pcb_files[0].read_text(encoding="utf-8")
        pcb = parse_kicad_pcb(raw_pcb)

    project_settings = None
    if pro_files:
        project_settings = parse_kicad_pro(
            pro_files[0].read_text(encoding="utf-8")
        )

    return KiCadProject(
        project_name=p_dir.name,
        schematic=schematic,
        pcb=pcb,
        project_settings=project_settings,
        raw_schematic=raw_sch,
        raw_pcb=raw_pcb,
        source_path=str(p_dir),
    )


def load_from_content(
    schematic_content: str = "",
    pcb_content: str = "",
    project_content: str = "",
    project_name: str = "pasted_project",
) -> KiCadProject:
    """Build a KiCadProject from pasted file content strings."""
    schematic = parse_kicad_sch(schematic_content) if schematic_content else None
    pcb = parse_kicad_pcb(pcb_content) if pcb_content else None
    project_settings = parse_kicad_pro(project_content) if project_content else None

    return KiCadProject(
        project_name=project_name,
        schematic=schematic,
        pcb=pcb,
        project_settings=project_settings,
        raw_schematic=schematic_content,
        raw_pcb=pcb_content,
        source_path=None,
    )

"""
Arduino component pin definitions, electrical properties, and wiring rules.
Used by the rule-based analysis layer to detect common circuit faults.
"""

COMPONENT_PINS = {
    "wokwi-arduino-uno": {
        "pins": {
            "0": {"type": "digital", "pwm": False, "direction": "io"},
            "1": {"type": "digital", "pwm": False, "direction": "io"},
            "2": {"type": "digital", "pwm": False, "direction": "io"},
            "3": {"type": "digital", "pwm": True, "direction": "io"},
            "4": {"type": "digital", "pwm": False, "direction": "io"},
            "5": {"type": "digital", "pwm": True, "direction": "io"},
            "6": {"type": "digital", "pwm": True, "direction": "io"},
            "7": {"type": "digital", "pwm": False, "direction": "io"},
            "8": {"type": "digital", "pwm": False, "direction": "io"},
            "9": {"type": "digital", "pwm": True, "direction": "io"},
            "10": {"type": "digital", "pwm": True, "direction": "io"},
            "11": {"type": "digital", "pwm": True, "direction": "io"},
            "12": {"type": "digital", "pwm": False, "direction": "io"},
            "13": {"type": "digital", "pwm": True, "direction": "io"},
            "A0": {"type": "analog", "direction": "input"},
            "A1": {"type": "analog", "direction": "input"},
            "A2": {"type": "analog", "direction": "input"},
            "A3": {"type": "analog", "direction": "input"},
            "A4": {"type": "analog", "i2c": "SDA", "direction": "io"},
            "A5": {"type": "analog", "i2c": "SCL", "direction": "io"},
            "GND.1": {"type": "ground"},
            "GND.2": {"type": "ground"},
            "GND.3": {"type": "ground"},
            "5V": {"type": "power", "voltage": 5.0},
            "3.3V": {"type": "power", "voltage": 3.3},
            "VIN": {"type": "power"},
            "AREF": {"type": "reference"},
            "RESET": {"type": "control"},
        },
        "max_pin_current_ma": 40,
        "max_total_current_ma": 200,
        "operating_voltage": 5.0,
        "requires_power": False,
    },
    "wokwi-arduino-mega": {
        "pins": {
            **{str(i): {"type": "digital", "pwm": i in (2,3,4,5,6,7,8,9,10,11,12,13), "direction": "io"} for i in range(54)},
            **{f"A{i}": {"type": "analog", "direction": "input"} for i in range(16)},
            "GND.1": {"type": "ground"},
            "GND.2": {"type": "ground"},
            "5V": {"type": "power", "voltage": 5.0},
            "3.3V": {"type": "power", "voltage": 3.3},
            "VIN": {"type": "power"},
        },
        "max_pin_current_ma": 40,
        "max_total_current_ma": 200,
        "operating_voltage": 5.0,
        "requires_power": False,
    },
    "wokwi-arduino-nano": {
        "pins": {
            **{str(i): {"type": "digital", "pwm": i in (3,5,6,9,10,11), "direction": "io"} for i in range(14)},
            **{f"A{i}": {"type": "analog", "direction": "input"} for i in range(8)},
            "GND.1": {"type": "ground"},
            "5V": {"type": "power", "voltage": 5.0},
            "3.3V": {"type": "power", "voltage": 3.3},
            "VIN": {"type": "power"},
        },
        "max_pin_current_ma": 40,
        "max_total_current_ma": 200,
        "operating_voltage": 5.0,
        "requires_power": False,
    },
    "wokwi-led": {
        "pins": {
            "A": {"type": "anode"},
            "C": {"type": "cathode"},
        },
        "requires_power": True,
        "needs_resistor": True,
        "typical_resistor_ohms": 220,
        "forward_voltage": 2.0,
        "max_current_ma": 20,
    },
    "wokwi-rgb-led": {
        "pins": {
            "R": {"type": "anode", "color": "red"},
            "G": {"type": "anode", "color": "green"},
            "B": {"type": "anode", "color": "blue"},
            "COM": {"type": "cathode"},
        },
        "requires_power": True,
        "needs_resistor": True,
        "typical_resistor_ohms": 220,
        "max_current_ma": 20,
    },
    "wokwi-resistor": {
        "pins": {
            "1": {"type": "passive"},
            "2": {"type": "passive"},
        },
        "requires_power": False,
    },
    "wokwi-pushbutton": {
        "pins": {
            "1.l": {"type": "passive"},
            "2.l": {"type": "passive"},
            "1.r": {"type": "passive"},
            "2.r": {"type": "passive"},
        },
        "requires_power": False,
        "internal_connections": [("1.l", "1.r"), ("2.l", "2.r")],
        "notes": "1.l-1.r and 2.l-2.r are internally connected. Button press bridges 1-2.",
    },
    "wokwi-slide-switch": {
        "pins": {
            "1": {"type": "passive"},
            "2": {"type": "common"},
            "3": {"type": "passive"},
        },
        "requires_power": False,
    },
    "wokwi-servo": {
        "pins": {
            "PWM": {"type": "signal", "needs_pwm": True},
            "V+": {"type": "power_in", "voltage": 5.0},
            "GND": {"type": "ground_in"},
        },
        "requires_power": True,
        "current_draw_ma": 200,
        "notes": "Draws up to 500mA under load. External power recommended.",
    },
    "wokwi-potentiometer": {
        "pins": {
            "GND": {"type": "ground_in"},
            "SIG": {"type": "analog_out"},
            "VCC": {"type": "power_in"},
        },
        "requires_power": True,
    },
    "wokwi-lcd1602": {
        "pins": {
            "GND": {"type": "ground_in"},
            "VCC": {"type": "power_in"},
            "SDA": {"type": "i2c_data"},
            "SCL": {"type": "i2c_clock"},
        },
        "requires_power": True,
        "protocol": "i2c",
        "i2c_address": "0x27",
    },
    "wokwi-buzzer": {
        "pins": {
            "1": {"type": "signal"},
            "2": {"type": "ground_in"},
        },
        "requires_power": True,
        "current_draw_ma": 30,
    },
    "wokwi-dht22": {
        "pins": {
            "VCC": {"type": "power_in"},
            "SDA": {"type": "data"},
            "NC": {"type": "no_connect"},
            "GND": {"type": "ground_in"},
        },
        "requires_power": True,
        "operating_voltage": 3.3,
        "protocol": "one_wire",
    },
    "wokwi-hc-sr04": {
        "pins": {
            "VCC": {"type": "power_in"},
            "TRIG": {"type": "digital_in"},
            "ECHO": {"type": "digital_out"},
            "GND": {"type": "ground_in"},
        },
        "requires_power": True,
        "operating_voltage": 5.0,
    },
    "wokwi-neopixel": {
        "pins": {
            "VCC": {"type": "power_in"},
            "GND": {"type": "ground_in"},
            "DIN": {"type": "data_in"},
            "DOUT": {"type": "data_out"},
        },
        "requires_power": True,
        "current_draw_ma": 60,
        "notes": "Each pixel draws up to 60mA at full white.",
    },
    "wokwi-pir-motion-sensor": {
        "pins": {
            "VCC": {"type": "power_in"},
            "OUT": {"type": "digital_out"},
            "GND": {"type": "ground_in"},
        },
        "requires_power": True,
    },
    "wokwi-photoresistor-sensor": {
        "pins": {
            "VCC": {"type": "power_in"},
            "GND": {"type": "ground_in"},
            "AO": {"type": "analog_out"},
            "DO": {"type": "digital_out"},
        },
        "requires_power": True,
    },
    "wokwi-stepper-motor": {
        "pins": {
            "A-": {"type": "coil"},
            "A+": {"type": "coil"},
            "B-": {"type": "coil"},
            "B+": {"type": "coil"},
        },
        "requires_power": True,
        "current_draw_ma": 500,
        "notes": "Requires motor driver (e.g., ULN2003). Do NOT connect directly to Arduino pins.",
    },
    "wokwi-membrane-keypad": {
        "pins": {
            "R1": {"type": "row"}, "R2": {"type": "row"},
            "R3": {"type": "row"}, "R4": {"type": "row"},
            "C1": {"type": "column"}, "C2": {"type": "column"},
            "C3": {"type": "column"}, "C4": {"type": "column"},
        },
        "requires_power": False,
    },
}

# Common wiring rules checked by the rule-based analyzer
WIRING_RULES = [
    {
        "id": "led_needs_resistor",
        "description": "LEDs must have a current-limiting resistor (typically 220-1K ohm) to prevent burnout",
        "applies_to": ["wokwi-led", "wokwi-rgb-led"],
        "severity": "error",
    },
    {
        "id": "servo_needs_pwm",
        "description": "Servo signal wire must connect to a PWM-capable Arduino pin",
        "applies_to": ["wokwi-servo"],
        "severity": "error",
    },
    {
        "id": "i2c_needs_correct_pins",
        "description": "I2C devices (SDA/SCL) should connect to A4/A5 on Uno or dedicated SDA/SCL pins",
        "applies_to": ["wokwi-lcd1602"],
        "severity": "error",
    },
    {
        "id": "component_needs_power",
        "description": "Components that require power must have VCC and GND connections",
        "applies_to": "__all_powered__",
        "severity": "error",
    },
    {
        "id": "stepper_needs_driver",
        "description": "Stepper motors should not be connected directly to Arduino pins - use a motor driver",
        "applies_to": ["wokwi-stepper-motor"],
        "severity": "warning",
    },
    {
        "id": "neopixel_power_warning",
        "description": "NeoPixel strips with many LEDs need external power supply (60mA per LED at full white)",
        "applies_to": ["wokwi-neopixel"],
        "severity": "warning",
    },
]

# Arduino boards for identification
ARDUINO_BOARDS = {
    "wokwi-arduino-uno",
    "wokwi-arduino-mega",
    "wokwi-arduino-nano",
}

# Pin types that indicate power connections
POWER_PIN_TYPES = {"power", "power_in", "power_out"}
GROUND_PIN_TYPES = {"ground", "ground_in", "ground_out"}
SIGNAL_PIN_TYPES = {"digital", "analog", "signal", "data", "data_in", "data_out",
                    "digital_in", "digital_out", "analog_out", "i2c_data", "i2c_clock"}


def get_relevant_knowledge(part_types: list[str]) -> str:
    """Build a focused pin reference string for the components in the current diagram."""
    lines = []
    for ptype in sorted(set(part_types)):
        info = COMPONENT_PINS.get(ptype)
        if info:
            pin_names = ", ".join(info["pins"].keys())
            line = f"- **{ptype}**: pins=[{pin_names}]"
            if info.get("requires_power"):
                line += " | requires power"
            if info.get("needs_resistor"):
                line += f" | needs resistor (~{info.get('typical_resistor_ohms', 220)}Ω)"
            if info.get("protocol"):
                line += f" | protocol: {info['protocol']}"
            if info.get("current_draw_ma"):
                line += f" | draws ~{info['current_draw_ma']}mA"
            if info.get("max_current_ma"):
                line += f" | max {info['max_current_ma']}mA"
            if info.get("notes"):
                line += f"\n  Note: {info['notes']}"
            lines.append(line)
        else:
            lines.append(f"- **{ptype}**: (unknown component - not in knowledge base)")
    return "\n".join(lines) if lines else "No component information available."


def get_pwm_pins(board_type: str) -> set[str]:
    """Return the set of PWM-capable pin names for a given board type."""
    info = COMPONENT_PINS.get(board_type, {})
    pins = info.get("pins", {})
    return {name for name, props in pins.items() if props.get("pwm")}


def get_analog_pins(board_type: str) -> set[str]:
    """Return the set of analog input pin names for a given board type."""
    info = COMPONENT_PINS.get(board_type, {})
    pins = info.get("pins", {})
    return {name for name, props in pins.items() if props.get("type") == "analog"}


def get_board_from_parts(parts: list[dict]) -> str | None:
    """Find the Arduino board type from the parts list."""
    for part in parts:
        if part.get("type") in ARDUINO_BOARDS:
            return part["type"]
    return None

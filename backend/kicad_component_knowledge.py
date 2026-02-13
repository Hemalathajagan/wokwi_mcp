"""
KiCad component knowledge base: pin specifications, operating parameters,
common design mistakes, and manufacturing rules for standard KiCad library components.
"""

import fnmatch
from typing import Any


# ---------------------------------------------------------------------------
# Component database keyed on KiCad library symbol IDs
# Supports wildcards (*) for matching component families
# ---------------------------------------------------------------------------

KICAD_COMPONENT_DB: dict[str, dict[str, Any]] = {
    # ---- Passive Components ----
    "Device:R": {
        "category": "passive",
        "description": "Resistor",
        "pins": {"1": "passive", "2": "passive"},
        "checks": ["value_not_empty", "value_is_valid_resistance"],
        "notes": "Verify resistance value matches design intent. Check power rating for current path.",
    },
    "Device:R_Small": {
        "category": "passive",
        "description": "Resistor (small symbol)",
        "pins": {"1": "passive", "2": "passive"},
        "checks": ["value_not_empty", "value_is_valid_resistance"],
        "notes": "Same as Device:R, small schematic symbol.",
    },
    "Device:C": {
        "category": "passive",
        "description": "Capacitor (non-polarized)",
        "pins": {"1": "passive", "2": "passive"},
        "checks": ["value_not_empty", "value_is_valid_capacitance"],
        "notes": "Check voltage rating >= circuit voltage with margin. Use ceramic (MLCC) for decoupling.",
    },
    "Device:C_Small": {
        "category": "passive",
        "description": "Capacitor (small symbol)",
        "pins": {"1": "passive", "2": "passive"},
        "checks": ["value_not_empty", "value_is_valid_capacitance"],
        "notes": "Same as Device:C, small schematic symbol.",
    },
    "Device:C_Polarized": {
        "category": "passive",
        "description": "Polarized capacitor (electrolytic/tantalum)",
        "pins": {"+": "passive", "-": "passive"},
        "checks": ["polarity_correct", "voltage_rating", "value_not_empty"],
        "notes": "POLARITY MATTERS. Positive pin must connect to higher voltage. Reverse polarity can cause explosion. Use for bulk bypass, not high-frequency decoupling.",
    },
    "Device:L": {
        "category": "passive",
        "description": "Inductor",
        "pins": {"1": "passive", "2": "passive"},
        "checks": ["value_not_empty"],
        "notes": "Check current rating and DCR. Critical for switch-mode power supplies.",
    },
    "Device:LED": {
        "category": "indicator",
        "description": "Light Emitting Diode",
        "pins": {"A": "anode", "K": "cathode"},
        "checks": ["needs_current_limiting_resistor", "polarity_correct"],
        "notes": "Requires series current-limiting resistor (typ. 220-1k ohm for 5V, 100-470 for 3.3V). Forward voltage depends on color: Red ~1.8V, Green ~2.2V, Blue/White ~3.0V.",
    },
    "Device:D": {
        "category": "passive",
        "description": "Diode",
        "pins": {"A": "anode", "K": "cathode"},
        "checks": ["polarity_correct"],
        "notes": "Check forward voltage drop and current rating. Polarity: current flows from Anode to Cathode.",
    },
    "Device:D_Zener": {
        "category": "passive",
        "description": "Zener diode",
        "pins": {"A": "anode", "K": "cathode"},
        "checks": ["polarity_correct", "value_not_empty"],
        "notes": "Used for voltage regulation/clamping. Cathode connects to positive side. Value should indicate Zener voltage.",
    },
    "Device:D_Schottky": {
        "category": "passive",
        "description": "Schottky diode",
        "pins": {"A": "anode", "K": "cathode"},
        "checks": ["polarity_correct"],
        "notes": "Low forward voltage drop (~0.2-0.4V). Common for power supply protection and high-speed switching.",
    },
    "Device:Q_NPN_*": {
        "category": "active",
        "description": "NPN BJT transistor",
        "pins": {"B": "base", "C": "collector", "E": "emitter"},
        "checks": ["base_resistor"],
        "notes": "Base needs current-limiting resistor. Check pinout matches footprint (varies by package).",
    },
    "Device:Q_PNP_*": {
        "category": "active",
        "description": "PNP BJT transistor",
        "pins": {"B": "base", "C": "collector", "E": "emitter"},
        "checks": ["base_resistor"],
        "notes": "Base needs current-limiting resistor. Emitter connects to positive rail.",
    },
    "Device:Q_NMOS_*": {
        "category": "active",
        "description": "N-channel MOSFET",
        "pins": {"G": "gate", "D": "drain", "S": "source"},
        "checks": ["gate_resistor"],
        "notes": "Gate needs pull-down resistor to prevent floating. Check Vgs threshold vs drive voltage.",
    },
    "Device:Q_PMOS_*": {
        "category": "active",
        "description": "P-channel MOSFET",
        "pins": {"G": "gate", "D": "drain", "S": "source"},
        "checks": ["gate_resistor"],
        "notes": "Source connects to positive rail. Gate needs pull-up to Vcc when off.",
    },
    "Device:Crystal": {
        "category": "passive",
        "description": "Crystal oscillator",
        "pins": {"1": "passive", "2": "passive"},
        "checks": ["load_capacitors"],
        "notes": "Requires two load capacitors to ground. Capacitor values depend on crystal specs (typically 12-22pF for MCU crystals). Route close to MCU, keep traces short.",
    },
    "Device:Fuse": {
        "category": "passive",
        "description": "Fuse",
        "pins": {"1": "passive", "2": "passive"},
        "checks": ["value_not_empty"],
        "notes": "Place on power input. Value should indicate current rating.",
    },

    # ---- Voltage Regulators ----
    "Regulator_Linear:LM7805*": {
        "category": "power",
        "description": "5V linear voltage regulator (7805 family)",
        "operating_voltage": {"input_min": 7.0, "input_max": 35.0, "output": 5.0},
        "pins": {"1": "input", "2": "ground", "3": "output"},
        "checks": ["input_cap", "output_cap", "input_voltage_sufficient"],
        "notes": "Requires 100nF ceramic cap on input AND output (close to pins). Input must be >= 7V for stable 5V output. Gets hot under load — consider heatsink for >500mA.",
    },
    "Regulator_Linear:LM7812*": {
        "category": "power",
        "description": "12V linear voltage regulator",
        "operating_voltage": {"input_min": 14.5, "input_max": 35.0, "output": 12.0},
        "pins": {"1": "input", "2": "ground", "3": "output"},
        "checks": ["input_cap", "output_cap", "input_voltage_sufficient"],
        "notes": "Requires 100nF ceramic cap on input and output.",
    },
    "Regulator_Linear:LM7833*": {
        "category": "power",
        "description": "3.3V linear voltage regulator",
        "operating_voltage": {"input_min": 5.3, "input_max": 35.0, "output": 3.3},
        "pins": {"1": "input", "2": "ground", "3": "output"},
        "checks": ["input_cap", "output_cap"],
        "notes": "Requires decoupling caps on input and output.",
    },
    "Regulator_Linear:AMS1117*3.3*": {
        "category": "power",
        "description": "3.3V LDO regulator (AMS1117)",
        "operating_voltage": {"input_min": 4.5, "input_max": 15.0, "output": 3.3},
        "pins": {"1": "ground/adjust", "2": "output", "3": "input"},
        "checks": ["input_cap", "output_cap"],
        "notes": "Low dropout (~1.1V). Requires 22uF tantalum or 10uF ceramic on output for stability. Check pinout — varies from 78xx family!",
    },
    "Regulator_Linear:LM1117*": {
        "category": "power",
        "description": "LDO voltage regulator (LM1117)",
        "operating_voltage": {"input_min": 4.75, "input_max": 15.0, "output": 3.3},
        "checks": ["input_cap", "output_cap"],
        "notes": "Requires 10uF tantalum on output for stability.",
    },

    # ---- Microcontrollers ----
    "MCU_Microchip:ATmega328P*": {
        "category": "mcu",
        "description": "ATmega328P (Arduino Uno MCU)",
        "operating_voltage": {"min": 1.8, "max": 5.5, "typical": 5.0},
        "max_pin_current_ma": 40,
        "max_total_current_ma": 200,
        "checks": ["decoupling_caps", "crystal_load_caps", "avcc_connection", "reset_pullup", "aref_cap"],
        "notes": "Needs 100nF decoupling cap on EACH VCC pin (pins 7, 20). AVCC (pin 18) MUST be connected even if ADC is unused. Reset (pin 1) needs 10k pull-up to VCC. AREF needs 100nF to GND if using ADC.",
        "common_mistakes": [
            "AVCC pin left floating — causes unpredictable behavior even without ADC use",
            "Missing 100nF decoupling cap on VCC pins — causes random resets",
            "Missing reset pull-up resistor — causes spurious resets from noise",
            "Crystal load caps wrong value — causes clock instability or failure to start",
        ],
    },
    "MCU_Microchip:ATmega2560*": {
        "category": "mcu",
        "description": "ATmega2560 (Arduino Mega MCU)",
        "operating_voltage": {"min": 1.8, "max": 5.5, "typical": 5.0},
        "max_pin_current_ma": 40,
        "max_total_current_ma": 200,
        "checks": ["decoupling_caps", "crystal_load_caps", "avcc_connection", "reset_pullup"],
        "notes": "Multiple VCC/GND pins — ALL must be connected with individual decoupling caps.",
    },
    "MCU_ST:STM32F103C*": {
        "category": "mcu",
        "description": "STM32F103 (Blue Pill MCU)",
        "operating_voltage": {"min": 2.0, "max": 3.6, "typical": 3.3},
        "logic_level": 3.3,
        "five_v_tolerant": True,
        "checks": ["decoupling_caps", "boot_pins", "crystal_load_caps", "reset_cap"],
        "notes": "3.3V MCU but most GPIO pins are 5V tolerant. Needs 100nF on each VDD pin + 4.7uF bulk cap. BOOT0 must be pulled low for normal operation. NRST needs 100nF to GND.",
        "common_mistakes": [
            "BOOT0 left floating — MCU may boot into bootloader instead of flash",
            "Missing decoupling on VDDA — causes ADC noise and instability",
            "Connecting 5V to non-5V-tolerant pins (VDDA, NRST, BOOT0)",
        ],
    },
    "MCU_ST:STM32F4*": {
        "category": "mcu",
        "description": "STM32F4 series MCU",
        "operating_voltage": {"min": 1.7, "max": 3.6, "typical": 3.3},
        "logic_level": 3.3,
        "five_v_tolerant": True,
        "checks": ["decoupling_caps", "boot_pins", "crystal_load_caps", "vcap_caps"],
        "notes": "Requires VCAP capacitors (2.2uF) on VCAP pins. Needs decoupling on all VDD pins.",
    },
    "MCU_RaspberryPi:RP2040": {
        "category": "mcu",
        "description": "RP2040 (Raspberry Pi Pico MCU)",
        "operating_voltage": {"min": 1.62, "max": 3.63, "typical": 3.3},
        "logic_level": 3.3,
        "five_v_tolerant": False,
        "checks": ["decoupling_caps", "flash_chip", "crystal_load_caps", "usb_resistors"],
        "notes": "NOT 5V tolerant on any pin. Needs external flash chip (QSPI). Requires 1uF on each power pin + 27ohm series resistors on USB D+/D-.",
        "common_mistakes": [
            "Connecting 5V signals directly — will damage the chip",
            "Missing external QSPI flash — RP2040 has no internal flash",
            "Missing 27ohm USB series resistors",
        ],
    },
    "RF_Module:ESP32-WROOM*": {
        "category": "mcu_module",
        "description": "ESP32-WROOM WiFi/BT module",
        "operating_voltage": {"min": 3.0, "max": 3.6, "typical": 3.3},
        "logic_level": 3.3,
        "five_v_tolerant": False,
        "checks": ["decoupling_caps", "strapping_pins", "flash_pins"],
        "notes": "3.3V only — NOT 5V tolerant. GPIO6-11 are connected to internal flash (DO NOT USE). Strapping pins (GPIO0, GPIO2, GPIO12, GPIO15) affect boot mode. Needs 10uF + 100nF decoupling.",
        "common_mistakes": [
            "Using GPIO6-11 for I/O — these are internal flash pins",
            "GPIO34-39 are input-only — cannot be used as outputs",
            "Missing pull-up on EN pin — module won't start",
            "GPIO12 pulled high at boot — causes flash voltage error",
        ],
    },
    "MCU_Module:Arduino_Nano*": {
        "category": "mcu_module",
        "description": "Arduino Nano module",
        "operating_voltage": {"typical": 5.0},
        "logic_level": 5.0,
        "checks": [],
        "notes": "Pre-built module with onboard regulator. Power via VIN (7-12V) or USB. I/O pins are 5V logic.",
    },
    "MCU_Module:Arduino_UNO*": {
        "category": "mcu_module",
        "description": "Arduino UNO module",
        "operating_voltage": {"typical": 5.0},
        "logic_level": 5.0,
        "checks": [],
        "notes": "Pre-built module. Power via VIN (7-12V), USB, or 5V pin.",
    },

    # ---- Communication ICs ----
    "Interface_UART:MAX232*": {
        "category": "communication",
        "description": "RS-232 level converter",
        "operating_voltage": {"typical": 5.0},
        "checks": ["charge_pump_caps"],
        "notes": "Requires 4-5 external capacitors (typically 1uF) for charge pump. Converts TTL to RS-232 voltage levels.",
    },
    "Interface_USB:CH340G": {
        "category": "communication",
        "description": "USB to UART bridge",
        "operating_voltage": {"min": 3.3, "max": 5.0},
        "checks": ["crystal", "decoupling_caps", "usb_resistors"],
        "notes": "Needs 12MHz crystal. Supports 3.3V and 5V operation (VCC pin selects). USB D+/D- need ESD protection.",
    },
    "Interface_USB:CP2102*": {
        "category": "communication",
        "description": "USB to UART bridge (Silicon Labs)",
        "operating_voltage": {"min": 3.0, "max": 3.6},
        "checks": ["decoupling_caps"],
        "notes": "3.3V device. Internal oscillator (no crystal needed). Needs decoupling caps.",
    },
    "Interface_CAN_LIN:MCP2551*": {
        "category": "communication",
        "description": "CAN bus transceiver",
        "operating_voltage": {"typical": 5.0},
        "checks": ["decoupling_caps", "termination_resistor"],
        "notes": "Needs 120 ohm termination resistor at each end of the CAN bus. Requires 100nF decoupling.",
    },

    # ---- Op-Amps ----
    "Amplifier_Operational:LM358*": {
        "category": "analog",
        "description": "Dual op-amp",
        "operating_voltage": {"min": 3.0, "max": 32.0},
        "checks": ["decoupling_caps", "power_pins"],
        "notes": "Dual op-amp. Output cannot swing to rails. Needs decoupling cap on supply pins.",
    },
    "Amplifier_Operational:LM324*": {
        "category": "analog",
        "description": "Quad op-amp",
        "operating_voltage": {"min": 3.0, "max": 32.0},
        "checks": ["decoupling_caps", "power_pins"],
        "notes": "Quad op-amp. Same characteristics as LM358.",
    },

    # ---- Timers ----
    "Timer:NE555*": {
        "category": "timer",
        "description": "555 Timer IC",
        "operating_voltage": {"min": 4.5, "max": 16.0, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "Needs 100nF decoupling cap between VCC and GND close to IC. Control pin (pin 5) needs 10nF to GND if unused.",
    },

    # ---- Memory ----
    "Memory_EEPROM:AT24C*": {
        "category": "memory",
        "description": "I2C EEPROM",
        "operating_voltage": {"min": 1.7, "max": 5.5},
        "checks": ["i2c_pullups", "address_pins", "decoupling_caps"],
        "notes": "I2C interface — needs pull-up resistors on SDA/SCL (typ. 4.7k for 100kHz, 2.2k for 400kHz). Address pins (A0-A2) must be tied to VCC or GND.",
    },
    "Memory_Flash:W25Q*": {
        "category": "memory",
        "description": "SPI NOR Flash",
        "checks": ["decoupling_caps", "spi_pullups"],
        "notes": "SPI interface. CS needs pull-up, HOLD and WP need pull-ups if unused. Needs 100nF decoupling.",
    },

    # ---- Sensors ----
    "Sensor_Temperature:DS18B20*": {
        "category": "sensor",
        "description": "1-Wire temperature sensor",
        "operating_voltage": {"min": 3.0, "max": 5.5},
        "checks": ["onewire_pullup"],
        "notes": "Needs 4.7k pull-up on data line. Parasite power mode needs strong pull-up (MOSFET).",
    },
    "Sensor_Humidity:DHT11": {
        "category": "sensor",
        "description": "Temperature and humidity sensor",
        "operating_voltage": {"min": 3.3, "max": 5.5},
        "checks": ["data_pullup", "decoupling_caps"],
        "notes": "Needs 4.7k-10k pull-up on data pin. Some modules have built-in pull-up.",
    },

    # ---- Connectors ----
    "Connector_Generic:Conn_01x*": {
        "category": "connector",
        "description": "Generic pin header",
        "checks": [],
        "notes": "Verify pin count matches design. Check footprint pitch (2.54mm standard).",
    },
    "Connector:USB_B_Micro": {
        "category": "connector",
        "description": "Micro USB B connector",
        "checks": ["usb_esd_protection", "usb_resistors"],
        "notes": "Add ESD protection on D+/D- lines. VBUS should have decoupling cap and optional fuse.",
    },
    "Connector:USB_C_Receptacle*": {
        "category": "connector",
        "description": "USB Type-C connector",
        "checks": ["usb_cc_resistors", "usb_esd_protection"],
        "notes": "Needs 5.1k resistors on CC1/CC2 pins to GND for proper USB-C detection. Add ESD protection.",
    },
}


# ---------------------------------------------------------------------------
# Power symbols and expected voltages
# ---------------------------------------------------------------------------

POWER_SYMBOLS: dict[str, float] = {
    "+5V": 5.0,
    "+3V3": 3.3,
    "+3.3V": 3.3,
    "+12V": 12.0,
    "+24V": 24.0,
    "+1V8": 1.8,
    "+2V5": 2.5,
    "+9V": 9.0,
    "VCC": 5.0,
    "VDD": 3.3,
    "VBUS": 5.0,
    "VBAT": 3.7,
    "GND": 0.0,
    "GNDREF": 0.0,
    "GNDD": 0.0,
    "GNDA": 0.0,
    "Earth": 0.0,
    "GNDPWR": 0.0,
    "VSS": 0.0,
}


# ---------------------------------------------------------------------------
# Trace width recommendations (1 oz copper, ambient temperature)
# ---------------------------------------------------------------------------

TRACE_WIDTH_CURRENT: dict[float, float] = {
    # current_amps: min_recommended_width_mm
    0.3: 0.15,
    0.5: 0.25,
    1.0: 0.50,
    1.5: 0.75,
    2.0: 1.00,
    3.0: 1.50,
    5.0: 2.50,
    7.0: 3.50,
    10.0: 5.00,
}


# ---------------------------------------------------------------------------
# Default manufacturing constraints
# ---------------------------------------------------------------------------

DEFAULT_MFG_CONSTRAINTS: dict[str, float] = {
    "min_trace_width_mm": 0.15,
    "min_clearance_mm": 0.15,
    "min_via_drill_mm": 0.3,
    "min_via_annular_ring_mm": 0.13,
    "min_hole_to_hole_mm": 0.25,
    "min_edge_clearance_mm": 0.3,
    "min_silk_width_mm": 0.15,
    "min_silk_clearance_mm": 0.15,
}


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

def match_component(lib_id: str) -> dict | None:
    """Match a KiCad library ID against the knowledge base.

    Supports exact matches and wildcard patterns.
    Example: 'MCU_Microchip:ATmega328P-AU' matches 'MCU_Microchip:ATmega328P*'
    """
    # Exact match first
    if lib_id in KICAD_COMPONENT_DB:
        return KICAD_COMPONENT_DB[lib_id]

    # Wildcard match
    for pattern, data in KICAD_COMPONENT_DB.items():
        if '*' in pattern and fnmatch.fnmatch(lib_id, pattern):
            return data

    return None


def get_power_voltage(symbol_name: str) -> float | None:
    """Get the expected voltage for a power symbol name."""
    return POWER_SYMBOLS.get(symbol_name)


def get_component_knowledge_text(symbols: list[dict]) -> str:
    """Build a component reference text for AI prompts from schematic symbols.

    Returns a formatted string describing known components and their requirements.
    """
    seen_libs: set[str] = set()
    lines: list[str] = []

    for sym in symbols:
        lib_id = sym.get("lib_id", "")
        if lib_id in seen_libs:
            continue
        seen_libs.add(lib_id)

        info = match_component(lib_id)
        if not info:
            continue

        ref = sym.get("reference", "?")
        desc = info.get("description", lib_id)
        notes = info.get("notes", "")
        mistakes = info.get("common_mistakes", [])

        lines.append(f"- **{ref}** ({desc} — {lib_id}):")
        if notes:
            lines.append(f"  Notes: {notes}")
        for m in mistakes:
            lines.append(f"  Common mistake: {m}")

    return "\n".join(lines) if lines else "No specific component knowledge available."

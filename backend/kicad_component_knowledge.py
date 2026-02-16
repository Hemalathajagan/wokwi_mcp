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
        "peripheral_pins": {
            "i2c": {"sda": ["PC4", "27"], "scl": ["PC5", "28"]},
            "spi": {"mosi": ["PB3", "17"], "miso": ["PB4", "18"], "sck": ["PB5", "19"], "ss": ["PB2", "16"]},
            "uart": {"tx": ["PD1", "3"], "rx": ["PD0", "2"]},
        },
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
        "peripheral_pins": {
            "i2c": {"sda": ["PB7", "59", "PB11", "48"], "scl": ["PB6", "58", "PB10", "47"]},
            "spi": {"mosi": ["PA7", "17", "PB15", "36"], "miso": ["PA6", "16", "PB14", "35"], "sck": ["PA5", "15", "PB13", "34"]},
            "uart": {"tx": ["PA9", "30", "PA2", "12"], "rx": ["PA10", "31", "PA3", "13"]},
        },
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
        "peripheral_pins": {
            "i2c": {
                "sda": ["GP0", "2", "GP4", "6", "GP8", "12", "GP12", "16", "GP16", "21", "GP20", "26"],
                "scl": ["GP1", "3", "GP5", "7", "GP9", "13", "GP13", "17", "GP17", "22", "GP21", "27"],
            },
            "spi": {
                "mosi": ["GP3", "5", "GP7", "10", "GP11", "15", "GP15", "20", "GP19", "25"],
                "miso": ["GP0", "2", "GP4", "6", "GP8", "12", "GP12", "16", "GP16", "21"],
                "sck": ["GP2", "4", "GP6", "9", "GP10", "14", "GP14", "19", "GP18", "24"],
            },
            "uart": {
                "tx": ["GP0", "2", "GP4", "6", "GP8", "12", "GP12", "16", "GP16", "21"],
                "rx": ["GP1", "3", "GP5", "7", "GP9", "13", "GP13", "17", "GP17", "22"],
            },
        },
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
        "peripheral_pins": {
            "i2c": {"sda": ["GPIO21", "33"], "scl": ["GPIO22", "36"]},
            "spi": {"mosi": ["GPIO23", "37"], "miso": ["GPIO19", "31"], "sck": ["GPIO18", "30"], "ss": ["GPIO5", "29"]},
            "uart": {"tx": ["GPIO1", "35", "GPIO17", "28"], "rx": ["GPIO3", "34", "GPIO16", "27"]},
            "pwm": {"any_gpio": True},
        },
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

    # ---- Sensors: IMU / Motion ----
    "Sensor_Motion:MPU6050*": {
        "category": "sensor",
        "description": "6-axis IMU (accelerometer + gyroscope, I2C/SPI)",
        "operating_voltage": {"min": 2.375, "max": 3.46, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. Needs 100nF on VDD and VLOGIC. I2C address 0x68 (AD0 low) or 0x69 (AD0 high). Keep decoupling caps within 4mm.",
        "common_mistakes": [
            "Connecting to 5V bus without level shifter — damages the sensor",
            "AD0 pin left floating — I2C address undefined",
            "Missing VLOGIC decoupling cap — causes noisy readings",
        ],
    },
    "Sensor_Motion:MPU9250*": {
        "category": "sensor",
        "description": "9-axis IMU (accel + gyro + magnetometer, I2C/SPI)",
        "operating_voltage": {"min": 2.4, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. Same pinout as MPU6050. Internal magnetometer (AK8963). Needs 100nF on VDD and VDDIO.",
        "common_mistakes": [
            "Connecting to 5V I2C bus without level shifter",
            "Not configuring magnetometer separately (AK8963 on auxiliary I2C)",
        ],
    },
    "Sensor_Motion:ADXL345*": {
        "category": "sensor",
        "description": "3-axis digital accelerometer (I2C/SPI)",
        "operating_voltage": {"min": 2.0, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. VS and VDD_IO both need 100nF. I2C address set by ALT ADDRESS pin (0x1D or 0x53).",
        "common_mistakes": [
            "Forgetting decoupling on VDD_IO — erratic communication",
            "ALT ADDRESS pin floating — address undefined",
        ],
    },
    "Sensor_Motion:LSM6DS3*": {
        "category": "sensor",
        "description": "6-axis IMU — accelerometer + gyroscope (I2C/SPI)",
        "operating_voltage": {"min": 1.71, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. I2C address set by SDO/SA0 pin. Needs 100nF on VDD and VDD_IO.",
        "common_mistakes": [
            "SDO/SA0 pin floating — I2C address undefined",
        ],
    },

    # ---- Sensors: Pressure / Temperature ----
    "Sensor_Pressure:BMP280*": {
        "category": "sensor",
        "description": "Barometric pressure + temperature sensor (I2C/SPI)",
        "operating_voltage": {"min": 1.71, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only — NOT 5V tolerant. I2C address 0x76 or 0x77 (set by SDO pin). Needs 100nF decoupling.",
        "common_mistakes": [
            "Connecting to 5V I2C bus without level shifter — damages the sensor",
            "SDO pin left floating — I2C address undefined",
        ],
    },
    "Sensor:BME280*": {
        "category": "sensor",
        "description": "Temperature, humidity, pressure sensor (I2C/SPI)",
        "operating_voltage": {"min": 1.71, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only — NOT 5V tolerant. I2C address 0x76 or 0x77 (set by SDO pin). Needs 100nF decoupling.",
        "common_mistakes": [
            "Connecting to 5V I2C bus without level shifter — damages the sensor",
            "SDO pin left floating — I2C address undefined",
        ],
    },
    "Sensor_Pressure:BMP180*": {
        "category": "sensor",
        "description": "Barometric pressure + temperature sensor (I2C)",
        "operating_voltage": {"min": 1.8, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. Fixed I2C address 0x77. Needs 100nF on VDD. EOC and XCLR pins can be left unconnected.",
        "common_mistakes": [
            "Powering from 5V rail — maximum is 3.6V",
        ],
    },

    # ---- Sensors: Light ----
    "Sensor_Optical:BH1750*": {
        "category": "sensor",
        "description": "Ambient light sensor (I2C)",
        "operating_voltage": {"min": 2.4, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. I2C address set by ADDR pin (0x23 low, 0x5C high). Needs 100nF decoupling.",
        "common_mistakes": [
            "ADDR pin floating — I2C address undefined",
        ],
    },
    "Sensor_Optical:TSL2561*": {
        "category": "sensor",
        "description": "Light-to-digital converter (I2C)",
        "operating_voltage": {"min": 2.7, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. I2C address set by ADDR SEL pin (0x29, 0x39, or 0x49). Needs 100nF decoupling.",
        "common_mistakes": [
            "ADDR SEL pin floating — I2C address undefined",
        ],
    },
    "Sensor_Optical:APDS-9960*": {
        "category": "sensor",
        "description": "RGB + ambient light + proximity + gesture sensor (I2C)",
        "operating_voltage": {"min": 2.4, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. Fixed I2C address 0x39. Needs 100nF decoupling. INT pin is open-drain (needs pull-up).",
        "common_mistakes": [
            "INT pin left without pull-up — interrupt output won't work",
            "Powering from 5V — maximum is 3.6V",
        ],
    },

    # ---- Sensors: Current / Voltage ----
    "Sensor_Current:INA219*": {
        "category": "sensor",
        "description": "Bidirectional current/power monitor (I2C)",
        "operating_voltage": {"min": 3.0, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "Measures bus voltage up to 26V. I2C address set by A0/A1 pins (16 possible addresses). Needs shunt resistor on high-side.",
        "common_mistakes": [
            "A0/A1 address pins floating — I2C address undefined",
            "Shunt resistor too large — excessive power dissipation",
        ],
    },
    "Sensor_Current:INA226*": {
        "category": "sensor",
        "description": "Bidirectional current/power monitor (I2C)",
        "operating_voltage": {"min": 2.7, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "Measures bus voltage up to 36V. I2C address set by A0/A1 pins. Alert pin is open-drain (needs pull-up).",
        "common_mistakes": [
            "A0/A1 address pins floating — I2C address undefined",
        ],
    },
    "Sensor_Current:ACS712*": {
        "category": "sensor",
        "description": "Hall-effect linear current sensor (analog output)",
        "operating_voltage": {"min": 4.5, "max": 5.5, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "5V only. Analog output — connect to ADC. Needs 100nF decoupling close to VCC pin. Available in 5A, 20A, 30A variants.",
        "common_mistakes": [
            "Connecting analog output directly to 3.3V MCU ADC without voltage divider",
            "Missing decoupling cap — causes noisy readings",
        ],
    },

    # ---- Sensors: Distance ----
    "Sensor:HC-SR04*": {
        "category": "sensor",
        "description": "Ultrasonic distance sensor module",
        "operating_voltage": {"min": 4.5, "max": 5.5, "typical": 5.0},
        "checks": [],
        "notes": "5V module. Echo pin outputs 5V — needs level shifter or voltage divider for 3.3V MCUs. Trig needs 10us pulse.",
        "common_mistakes": [
            "Echo pin connected directly to 3.3V MCU GPIO — may damage MCU",
            "Trig pulse too short — no reading returned",
        ],
    },
    "Sensor:VL53L0X*": {
        "category": "sensor",
        "description": "Time-of-Flight distance sensor (I2C)",
        "operating_voltage": {"min": 2.6, "max": 3.5, "typical": 2.8},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "2.8V typical. Default I2C address 0x29 (changeable via software). XSHUT pin allows multiple sensors on one bus. Needs 100nF + 4.7uF decoupling.",
        "common_mistakes": [
            "Powering from 3.3V without checking module regulator — bare chip is 2.8V",
            "XSHUT pin floating when using multiple sensors — address conflicts",
        ],
    },

    # ---- Motor / Driver ICs ----
    "Driver_Motor:L293D*": {
        "category": "motor_driver",
        "description": "Quadruple half-H driver (dual full-bridge)",
        "operating_voltage": {"min": 4.5, "max": 36.0, "typical": 12.0},
        "checks": ["decoupling_caps"],
        "notes": "Separate logic (VSS=5V) and motor (VS up to 36V) supply pins. Built-in flyback diodes. High dropout (~1.4V per side). Needs 100nF on VSS and 100uF on VS.",
        "common_mistakes": [
            "VSS (logic supply) left unconnected — IC won't function",
            "Exceeding 600mA per channel — overheats quickly",
        ],
    },
    "Driver_Motor:L298N*": {
        "category": "motor_driver",
        "description": "Dual full-bridge motor driver",
        "operating_voltage": {"min": 5.0, "max": 46.0, "typical": 12.0},
        "checks": ["decoupling_caps"],
        "notes": "NO built-in flyback diodes — external fast diodes required. Separate logic supply (5V). High dropout (~2V per side). Needs 100nF + 100uF decoupling.",
        "common_mistakes": [
            "Missing flyback diodes — voltage spikes will damage the IC",
            "Using without heatsink at high current — thermal shutdown",
        ],
    },
    "Driver_Motor:DRV8833*": {
        "category": "motor_driver",
        "description": "Dual H-bridge motor driver (low voltage)",
        "operating_voltage": {"min": 2.7, "max": 10.8, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "Built-in protection. nSLEEP pin needs pull-up to enable. FAULT pin is open-drain. Needs 10uF + 100nF on VM.",
        "common_mistakes": [
            "nSLEEP pin floating — driver stays in sleep mode",
            "Missing decoupling on VM — motor noise causes erratic behavior",
        ],
    },
    "Driver_Motor:DRV8825*": {
        "category": "motor_driver",
        "description": "Stepper motor driver (microstepping)",
        "operating_voltage": {"min": 8.2, "max": 45.0, "typical": 24.0},
        "checks": ["decoupling_caps"],
        "notes": "Requires 100uF bulk cap on VMOT close to pin. FAULT and nENBL are active low. Set current limit via VREF potentiometer. Needs proper heatsink.",
        "common_mistakes": [
            "Missing 100uF cap on VMOT — voltage spikes destroy the chip",
            "Connecting/disconnecting motor while powered — destroys driver",
        ],
    },
    "Driver_Motor:A4988*": {
        "category": "motor_driver",
        "description": "Stepper motor driver (microstepping)",
        "operating_voltage": {"min": 8.0, "max": 35.0, "typical": 24.0},
        "checks": ["decoupling_caps"],
        "notes": "Requires 100uF electrolytic cap on VMOT. ENABLE is active low. Current limit set by VREF and sense resistors. Needs heatsink.",
        "common_mistakes": [
            "Missing 100uF cap on VMOT — voltage spikes destroy the chip",
            "Connecting/disconnecting motor while powered — destroys driver",
        ],
    },
    "Driver_Motor:TB6612FNG*": {
        "category": "motor_driver",
        "description": "Dual DC motor driver (low dropout)",
        "operating_voltage": {"min": 2.5, "max": 13.5, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "Very low on-resistance. STBY pin must be pulled high to enable. Separate VM (motor) and VCC (logic) supplies. Needs 100nF + 10uF on VM.",
        "common_mistakes": [
            "STBY pin left floating or low — motors won't run",
        ],
    },
    "Driver_Motor:ULN2003*": {
        "category": "motor_driver",
        "description": "7-channel Darlington transistor array",
        "operating_voltage": {"min": 5.0, "max": 50.0, "typical": 12.0},
        "checks": [],
        "notes": "Built-in flyback diodes (COM pin must be connected to motor supply). Open-collector outputs — needs external pull-up or load to V+. Max 500mA per channel.",
        "common_mistakes": [
            "COM pin left unconnected — flyback diodes don't function, motor spikes damage IC",
        ],
    },
    "Driver_Motor:PCA9685*": {
        "category": "motor_driver",
        "description": "16-channel 12-bit PWM/servo driver (I2C)",
        "operating_voltage": {"min": 2.3, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "I2C address set by A0-A5 pins (up to 62 devices). Separate V+ for servos. OE pin active low (tie to GND to enable). Needs 10uF + 100nF on VDD.",
        "common_mistakes": [
            "OE pin floating — outputs may be disabled",
            "Address pins floating — I2C address undefined",
        ],
    },
    "Driver_Motor:DRV8302*": {
        "category": "motor_driver",
        "description": "3-phase brushless motor pre-driver",
        "operating_voltage": {"min": 6.0, "max": 60.0, "typical": 24.0},
        "checks": ["decoupling_caps"],
        "notes": "Pre-driver — needs external MOSFETs. Requires bootstrap capacitors on high-side gates. Includes buck regulator and current sense amps. Complex layout required.",
        "common_mistakes": [
            "Missing bootstrap capacitors — high-side MOSFETs won't turn on",
            "Poor layout — long gate drive traces cause ringing and shoot-through",
        ],
    },
    "Transistor_Array:ULN2803*": {
        "category": "motor_driver",
        "description": "8-channel Darlington transistor array",
        "operating_voltage": {"min": 5.0, "max": 50.0, "typical": 12.0},
        "checks": [],
        "notes": "8-channel version of ULN2003. COM pin must connect to inductive load supply for flyback protection. Max 500mA per channel.",
        "common_mistakes": [
            "COM pin left unconnected — flyback diodes non-functional",
        ],
    },

    # ---- Display / LED Drivers ----
    "LED:WS2812B*": {
        "category": "led_driver",
        "description": "Addressable RGB LED (NeoPixel)",
        "operating_voltage": {"min": 3.5, "max": 5.3, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "5V LED. Needs 100nF decoupling cap per LED (or per 3-5 LEDs minimum). Data line needs 300-500 ohm series resistor at MCU output. 3.3V logic may not be reliable — use level shifter.",
        "common_mistakes": [
            "No series resistor on data line — first LED may be damaged by ringing",
            "3.3V MCU driving data without level shifter — unreliable at 5V VDD",
            "Missing decoupling caps — causes flickering and color errors",
        ],
    },
    "LED:TLC5940*": {
        "category": "led_driver",
        "description": "16-channel LED driver with PWM (SPI-like)",
        "operating_voltage": {"min": 3.0, "max": 5.5, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "Constant-current LED driver. IREF pin sets maximum current via resistor to GND. Needs GSCLK, BLANK, and XLAT signals. Daisy-chainable.",
        "common_mistakes": [
            "IREF resistor wrong value — LEDs too bright or too dim",
            "BLANK pin floating — outputs may be unpredictable",
        ],
    },
    "Display:MAX7219*": {
        "category": "led_driver",
        "description": "8-digit 7-segment LED driver (SPI)",
        "operating_voltage": {"min": 4.0, "max": 5.5, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "SPI interface. ISET resistor sets segment current. Daisy-chainable via DOUT. Needs 100nF + 10uF decoupling on VCC.",
        "common_mistakes": [
            "ISET resistor wrong value — LEDs too dim or exceeding max current",
            "Missing decoupling — display flickers under load",
        ],
    },
    "Display:HT16K33*": {
        "category": "led_driver",
        "description": "LED matrix driver with keyscan (I2C)",
        "operating_voltage": {"min": 4.5, "max": 5.5, "typical": 5.0},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "I2C address set by A0-A2 pins (0x70-0x77). Drives up to 16x8 LED matrix. Needs 100nF + 10uF on VDD.",
        "common_mistakes": [
            "Address pins floating — I2C address undefined",
        ],
    },
    "Display:HD44780*": {
        "category": "display",
        "description": "Character LCD module controller",
        "operating_voltage": {"min": 4.5, "max": 5.5, "typical": 5.0},
        "checks": [],
        "notes": "5V module. Contrast adjusted via V0 pin (use 10k potentiometer to GND). Backlight needs current-limiting resistor. Can use 4-bit or 8-bit data mode.",
        "common_mistakes": [
            "V0 (contrast) pin floating — display appears blank",
            "Missing current-limiting resistor on backlight — burns out LED",
            "R/W pin not tied to GND when only writing — bus contention",
        ],
    },
    "Display:SSD1306*": {
        "category": "display",
        "description": "128x64 OLED display controller (I2C/SPI)",
        "operating_voltage": {"min": 1.65, "max": 3.3, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V logic. Most modules include regulator. I2C address 0x3C or 0x3D. Needs decoupling on VDD and VCC (charge pump output).",
        "common_mistakes": [
            "Driving I2C with 5V — damages controller on bare modules",
        ],
    },
    "Display:SH1106*": {
        "category": "display",
        "description": "132x64 OLED display controller (I2C/SPI)",
        "operating_voltage": {"min": 2.4, "max": 3.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "Similar to SSD1306 but 132-column instead of 128. Requires column offset in software. I2C address 0x3C or 0x3D.",
        "common_mistakes": [
            "Using SSD1306 driver without column offset — display shifted",
        ],
    },
    "Display:ILI9341*": {
        "category": "display",
        "description": "240x320 TFT LCD controller (SPI)",
        "operating_voltage": {"min": 2.7, "max": 3.3, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "3.3V logic — needs level shifter from 5V MCU. SPI up to 10MHz for reads, 32MHz for writes. Needs DC (data/command) pin. LED backlight needs current limiting.",
        "common_mistakes": [
            "5V logic connected without level shifter — damages controller",
            "Missing DC pin connection — display shows garbage",
            "Backlight without current limiting — burns out LEDs",
        ],
    },

    # ---- ADC / DAC ----
    "Analog_ADC:ADS1115*": {
        "category": "adc",
        "description": "16-bit 4-channel ADC (I2C)",
        "operating_voltage": {"min": 2.0, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "I2C address set by ADDR pin (0x48-0x4B). Internal PGA. ALERT/RDY pin is open-drain. Needs 100nF on VDD. Reference is internal.",
        "common_mistakes": [
            "ADDR pin floating — I2C address undefined",
            "Input voltage exceeding VDD + 0.3V — damages ADC",
        ],
    },
    "Analog_ADC:ADS1015*": {
        "category": "adc",
        "description": "12-bit 4-channel ADC (I2C)",
        "operating_voltage": {"min": 2.0, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "Same as ADS1115 but 12-bit resolution. I2C address set by ADDR pin. Faster sampling rate.",
        "common_mistakes": [
            "ADDR pin floating — I2C address undefined",
        ],
    },
    "Analog_ADC:MCP3008*": {
        "category": "adc",
        "description": "10-bit 8-channel ADC (SPI)",
        "operating_voltage": {"min": 2.7, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "SPI interface. VREF pin sets full-scale range. Needs 100nF on VDD and VREF. AGND and DGND should be connected at one point.",
        "common_mistakes": [
            "VREF left floating or noisy — ADC readings are inaccurate",
            "AGND and DGND not connected — offset errors",
        ],
    },
    "Analog_ADC:MCP3208*": {
        "category": "adc",
        "description": "12-bit 8-channel ADC (SPI)",
        "operating_voltage": {"min": 2.7, "max": 5.5, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "SPI interface. VREF pin sets full-scale range. Same pinout family as MCP3008 but 12-bit. Needs 100nF on VDD and VREF.",
        "common_mistakes": [
            "VREF noisy or unfiltered — limits effective resolution",
        ],
    },
    "Analog_DAC:MCP4725*": {
        "category": "dac",
        "description": "12-bit single-channel DAC (I2C)",
        "operating_voltage": {"min": 2.7, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "I2C address set by A0 pin and factory-programmed bits. Output range is 0 to VDD. Needs 100nF + 10uF on VDD. Has internal EEPROM for power-on value.",
        "common_mistakes": [
            "Output loaded with too low impedance — cannot source much current (25mA max)",
        ],
    },
    "Analog_DAC:DAC8562*": {
        "category": "dac",
        "description": "16-bit dual-channel DAC (SPI)",
        "operating_voltage": {"min": 2.7, "max": 5.5, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "SPI interface. Internal 2.5V reference (can use external). Needs 100nF on AVDD and DVDD. LDAC pin controls output update timing.",
        "common_mistakes": [
            "LDAC pin floating — outputs may not update correctly",
            "Mixing AVDD and DVDD without proper decoupling — noise on output",
        ],
    },

    # ---- GPIO Expanders / Shift Registers ----
    "Interface_Expansion:PCF8574*": {
        "category": "gpio_expander",
        "description": "8-bit I/O expander (I2C)",
        "operating_voltage": {"min": 2.5, "max": 6.0, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "I2C address set by A0-A2 pins (0x20-0x27). Quasi-bidirectional I/O — weak internal pull-ups. INT pin is open-drain (needs external pull-up).",
        "common_mistakes": [
            "A0-A2 address pins floating — I2C address undefined",
            "INT pin without pull-up — interrupt signaling won't work",
        ],
    },
    "Interface_Expansion:MCP23017*": {
        "category": "gpio_expander",
        "description": "16-bit I/O expander (I2C)",
        "operating_voltage": {"min": 1.8, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "I2C address set by A0-A2 (0x20-0x27). Two 8-bit ports (A and B). RESET pin active low — tie to VDD if unused. Needs 100nF on VDD.",
        "common_mistakes": [
            "RESET pin floating — random resets",
            "A0-A2 address pins floating — address conflicts",
        ],
    },
    "Interface_Expansion:MCP23008*": {
        "category": "gpio_expander",
        "description": "8-bit I/O expander (I2C)",
        "operating_voltage": {"min": 1.8, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "I2C address set by A0-A2 (0x20-0x27). Single 8-bit port. RESET pin active low — tie to VDD if unused. Needs 100nF on VDD.",
        "common_mistakes": [
            "RESET pin floating — random resets",
        ],
    },
    "74xx:74HC595*": {
        "category": "shift_register",
        "description": "8-bit serial-in parallel-out shift register",
        "operating_voltage": {"min": 2.0, "max": 6.0, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "SPI-compatible interface. OE pin active low — tie to GND to always enable outputs. SRCLR active low — tie to VCC if clear not needed. Daisy-chainable via QH'.",
        "common_mistakes": [
            "OE pin floating — outputs may be disabled",
            "SRCLR pin floating — register clears randomly",
        ],
    },
    "74xx:74HC165*": {
        "category": "shift_register",
        "description": "8-bit parallel-in serial-out shift register",
        "operating_voltage": {"min": 2.0, "max": 6.0, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "Reads 8 parallel inputs and shifts out serially. SH/LD pin controls parallel load vs shift. CLK INH should be tied low during shifting. Daisy-chainable.",
        "common_mistakes": [
            "SH/LD and CLK INH timing incorrect — wrong data read",
        ],
    },

    # ---- Power Management: Buck Regulators ----
    "Regulator_Switching:LM2596*": {
        "category": "power",
        "description": "SIMPLE SWITCHER 3A step-down (buck) regulator",
        "operating_voltage": {"input_min": 4.5, "input_max": 40.0, "output": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "Requires inductor (33uH-68uH), Schottky diode, input cap (680uF electrolytic), output cap (220uF electrolytic). Fixed and adjustable versions available.",
        "common_mistakes": [
            "Wrong inductor value — causes instability or poor regulation",
            "Missing Schottky diode — circuit won't regulate",
            "Input capacitor too small — input voltage spikes",
        ],
    },
    "Regulator_Switching:MP1584*": {
        "category": "power",
        "description": "3A step-down (buck) converter",
        "operating_voltage": {"input_min": 4.5, "input_max": 28.0, "output": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "High efficiency. Requires inductor, bootstrap cap, feedback resistors (adjustable version). Needs 22uF input + 22uF output ceramic caps minimum.",
        "common_mistakes": [
            "Feedback resistor divider wrong ratio — incorrect output voltage",
            "Bootstrap cap missing — high-side MOSFET won't turn on",
        ],
    },
    "Regulator_Switching:TPS5430*": {
        "category": "power",
        "description": "3A step-down (buck) converter (TI)",
        "operating_voltage": {"input_min": 5.5, "input_max": 36.0, "output": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "Requires inductor (10uH-33uH), bootstrap cap, Schottky diode, compensation network. ENA pin needs voltage divider for UVLO. Needs 10uF ceramic input/output caps.",
        "common_mistakes": [
            "Missing compensation network — output oscillates",
            "ENA pin floating — may not start up",
        ],
    },

    # ---- Power Management: Boost Regulators ----
    "Regulator_Switching:MT3608*": {
        "category": "power",
        "description": "2A step-up (boost) converter",
        "operating_voltage": {"input_min": 2.0, "input_max": 24.0},
        "checks": ["decoupling_caps"],
        "notes": "Requires inductor (4.7uH-22uH), Schottky diode, feedback resistors, input/output caps (22uF ceramic). EN pin has internal pull-up.",
        "common_mistakes": [
            "Feedback resistors wrong ratio — incorrect or dangerous output voltage",
            "Inductor saturation at high load — efficiency drops sharply",
        ],
    },
    "Regulator_Switching:TPS61040*": {
        "category": "power",
        "description": "Step-up (boost) DC-DC converter (TI)",
        "operating_voltage": {"input_min": 1.8, "input_max": 6.0},
        "checks": ["decoupling_caps"],
        "notes": "Output up to 28V. Requires inductor (10uH-22uH), Schottky diode, feedback resistors. Soft-start via SS pin capacitor. Needs 4.7uF input + 4.7uF output caps.",
        "common_mistakes": [
            "Output exceeding 28V due to wrong feedback resistors — damages IC",
        ],
    },

    # ---- Power Management: Buck-Boost ----
    "Regulator_Switching:TPS63020*": {
        "category": "power",
        "description": "Buck-boost converter (TI)",
        "operating_voltage": {"input_min": 1.8, "input_max": 5.5},
        "checks": ["decoupling_caps"],
        "notes": "Maintains output when input crosses output voltage (battery applications). Requires 2.2uH inductor, 10uF input/output caps. PS/SYNC pin selects power-save mode.",
        "common_mistakes": [
            "Wrong inductor value — poor efficiency or instability",
            "VINA and VINB not shorted — required for proper operation",
        ],
    },

    # ---- Power Management: LDOs ----
    "Regulator_Linear:AP2112*": {
        "category": "power",
        "description": "600mA LDO voltage regulator",
        "operating_voltage": {"input_min": 2.5, "input_max": 6.0, "output": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "Low dropout (~250mV at full load). EN pin has internal pull-up. Needs 1uF output cap (ceramic OK). Available in 1.2V, 1.8V, 2.5V, 3.3V.",
        "common_mistakes": [
            "Output cap too small — causes oscillation",
        ],
    },
    "Regulator_Linear:XC6206*": {
        "category": "power",
        "description": "200mA LDO voltage regulator (low quiescent)",
        "operating_voltage": {"input_min": 1.8, "input_max": 6.0, "output": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "Very low quiescent current (~1uA). Needs 1uF output cap. Great for battery-powered designs. Available in many output voltages.",
        "common_mistakes": [
            "Exceeding 200mA output — thermal shutdown or damage",
        ],
    },
    "Regulator_Linear:MIC5219*": {
        "category": "power",
        "description": "500mA LDO voltage regulator",
        "operating_voltage": {"input_min": 2.5, "input_max": 12.0, "output": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "Low dropout (~500mV). EN pin for shutdown. Bypass pin needs 470pF cap for low noise. Needs 100nF input + 2.2uF output caps.",
        "common_mistakes": [
            "Bypass cap missing — higher output noise",
        ],
    },

    # ---- Power Management: Battery ----
    "Battery_Management:TP4056*": {
        "category": "power",
        "description": "Linear Li-Ion battery charger",
        "operating_voltage": {"input_min": 4.0, "input_max": 8.0, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "PROG resistor sets charge current (2k=500mA, 1.2k=1A). CHRG and STDBY are open-drain status outputs (need pull-ups or LEDs to VCC). Input needs 4.7uF cap.",
        "common_mistakes": [
            "PROG resistor wrong value — charges too fast (overheats) or too slow",
            "No protection circuit on battery output — risk of over-discharge or short",
        ],
    },

    # ---- Communication Modules ----
    "RF_Module:ESP-01*": {
        "category": "communication",
        "description": "ESP8266 WiFi module (ESP-01)",
        "operating_voltage": {"min": 3.0, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "3.3V only — NOT 5V tolerant. Draws up to 300mA peaks. CH_PD/EN must be pulled high to enable. GPIO0 must be high for normal boot. Needs 10uF + 100nF decoupling.",
        "common_mistakes": [
            "Powering from 3.3V pin of Arduino — insufficient current (peaks to 300mA)",
            "GPIO0 floating — may enter flash mode instead of run mode",
            "Connecting to 5V UART without level shifter — damages module",
        ],
    },
    "RF_Module:HC-05*": {
        "category": "communication",
        "description": "Bluetooth SPP module (classic Bluetooth)",
        "operating_voltage": {"min": 3.6, "max": 6.0, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "Module has onboard regulator (3.3V internally). UART TX output is 3.3V. KEY/EN pin for AT command mode. Default UART: 9600 baud.",
        "common_mistakes": [
            "Connecting RX directly to 5V TX — module RX is 3.3V input",
        ],
    },
    "RF_Module:HC-06*": {
        "category": "communication",
        "description": "Bluetooth SPP module (slave only)",
        "operating_voltage": {"min": 3.6, "max": 6.0, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "Slave-only version of HC-05. Module has onboard regulator. Default UART: 9600 baud. Configuration via AT commands (before pairing).",
        "common_mistakes": [
            "Trying to use as master — HC-06 is slave-only (use HC-05 for master)",
        ],
    },
    "RF_Module:HM-10*": {
        "category": "communication",
        "description": "Bluetooth Low Energy (BLE) module",
        "operating_voltage": {"min": 3.1, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "BLE 4.0 module. 3.3V only. UART interface. Some clones have different firmware and AT commands. Needs 100nF + 10uF decoupling.",
        "common_mistakes": [
            "Expecting classic Bluetooth SPP — BLE is different protocol, needs BLE-compatible app",
            "Connecting to 5V — damages the module",
        ],
    },
    "RF_Module:nRF24L01*": {
        "category": "communication",
        "description": "2.4GHz RF transceiver module (SPI)",
        "operating_voltage": {"min": 1.9, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "3.3V power but 5V tolerant on SPI pins. Needs 10uF + 100nF decoupling on VCC (critical — draws 11mA peaks). IRQ pin is active low, open-drain.",
        "common_mistakes": [
            "Insufficient decoupling on VCC — causes communication failures and random resets",
            "Powering from Arduino 3.3V pin — insufficient current for peaks",
        ],
    },
    "RF_Module:RFM69*": {
        "category": "communication",
        "description": "ISM band RF transceiver module (SPI)",
        "operating_voltage": {"min": 1.8, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "3.3V only. SPI interface. Needs proper antenna (wire or PCB trace matched to frequency). Needs 100nF + 10uF decoupling. DIO pins for interrupt signaling.",
        "common_mistakes": [
            "Missing or wrong-length antenna — no communication",
            "Powering from 5V — damages module",
        ],
    },
    "RF_Module:SX1278*": {
        "category": "communication",
        "description": "LoRa RF transceiver (SPI)",
        "operating_voltage": {"min": 1.8, "max": 3.7, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "3.3V only. LoRa modulation for long range. SPI interface. Must have matched antenna. Needs 100nF + 10uF on VCC. DIO0-DIO5 for interrupt signaling.",
        "common_mistakes": [
            "Transmitting without antenna — can damage the RF output stage",
            "Wrong antenna for frequency band — very poor range",
        ],
    },
    "Interface_CAN_LIN:SN65HVD230*": {
        "category": "communication",
        "description": "3.3V CAN bus transceiver",
        "operating_voltage": {"min": 3.0, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "termination_resistor"],
        "notes": "3.3V CAN transceiver. Needs 120 ohm termination at each end of bus. Rs pin controls slope — tie to GND for high-speed mode. Needs 100nF decoupling.",
        "common_mistakes": [
            "Missing 120 ohm termination — bus errors and communication failure",
            "Rs pin floating — undefined slew rate",
        ],
    },

    # ---- Audio ----
    "Amplifier_Audio:LM386*": {
        "category": "audio",
        "description": "Low-voltage audio power amplifier",
        "operating_voltage": {"min": 4.0, "max": 12.0, "typical": 9.0},
        "checks": ["decoupling_caps"],
        "notes": "Default gain 20 (26dB). Gain increased to 200 with cap between pins 1 and 8. Output coupling cap needed (220uF-470uF). Needs 10uF bypass on pin 7, 100nF on VCC.",
        "common_mistakes": [
            "Missing output coupling capacitor — DC offset damages speaker",
            "Bypass cap on pin 7 missing — oscillation and noise",
        ],
    },
    "Amplifier_Audio:PAM8403*": {
        "category": "audio",
        "description": "3W stereo Class-D audio amplifier",
        "operating_voltage": {"min": 2.5, "max": 5.5, "typical": 5.0},
        "checks": ["decoupling_caps"],
        "notes": "Filterless Class-D — no output inductor needed. Bridge-tied load outputs (do NOT ground speaker). Needs 10uF + 100nF on PVDD. MUTE pin active low.",
        "common_mistakes": [
            "Grounding one side of speaker — BTL output must be differential",
            "MUTE pin floating — amplifier may be muted",
        ],
    },
    "Amplifier_Audio:MAX98357*": {
        "category": "audio",
        "description": "I2S Class-D mono audio amplifier",
        "operating_voltage": {"min": 2.5, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "I2S digital input — no DAC needed. GAIN pin selects gain (3dB, 6dB, 9dB, 12dB, 15dB). SD_MODE pin controls shutdown and channel select. Filterless output.",
        "common_mistakes": [
            "SD_MODE pin floating — amplifier in shutdown",
            "GAIN pin in undefined state — wrong output level",
        ],
    },
    "Audio:PCM5102*": {
        "category": "audio",
        "description": "32-bit I2S stereo DAC",
        "operating_voltage": {"min": 3.0, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "3.3V only. I2S input. Needs 100nF on each supply pin (AVDD, DVDD, CPVDD). FMT pin selects I2S format. XSMT (soft mute) active low — pull high for normal operation.",
        "common_mistakes": [
            "XSMT pin floating — output muted",
            "FMT pin wrong level — no audio or distorted output",
            "Missing decoupling on CPVDD — charge pump noise in output",
        ],
    },

    # ---- RTC / Timing ----
    "Timer:DS1307*": {
        "category": "rtc",
        "description": "Real-time clock (I2C)",
        "operating_voltage": {"min": 4.5, "max": 5.5, "typical": 5.0},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "5V only. Fixed I2C address 0x68. Requires 32.768kHz crystal. VBAT pin for backup battery (CR2032). SQW/OUT pin for square wave output.",
        "common_mistakes": [
            "Using with 3.3V MCU without level shifter on I2C lines",
            "Missing 32.768kHz crystal — RTC won't keep time",
            "VBAT pin floating — no backup when power lost",
        ],
    },
    "Timer:DS3231*": {
        "category": "rtc",
        "description": "Extremely accurate RTC with TCXO (I2C)",
        "operating_voltage": {"min": 2.3, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "Built-in TCXO — NO external crystal needed. Fixed I2C address 0x68. VBAT for backup battery. INT/SQW pin is open-drain (needs pull-up). 32KHz output available.",
        "common_mistakes": [
            "Adding external crystal — DS3231 has internal oscillator (unlike DS1307)",
            "INT/SQW pin without pull-up — alarms/interrupts won't signal",
        ],
    },
    "Timer:PCF8523*": {
        "category": "rtc",
        "description": "Real-time clock (I2C, low power)",
        "operating_voltage": {"min": 1.0, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "Ultra-low power. Fixed I2C address 0x68. Requires 32.768kHz crystal with 7pF load caps. INT pin is open-drain. Battery switchover configurable via register.",
        "common_mistakes": [
            "Wrong crystal load capacitors — timekeeping drift",
        ],
    },
    "Clock:Si5351*": {
        "category": "oscillator",
        "description": "Programmable clock generator (I2C)",
        "operating_voltage": {"min": 2.5, "max": 3.6, "typical": 3.3},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "3.3V only. I2C address 0x60 (fixed). Generates up to 3 independent clock outputs (8kHz to 160MHz). Requires 25MHz or 27MHz crystal. Needs 100nF on VDD and VDDO.",
        "common_mistakes": [
            "Missing crystal — needs external 25MHz or 27MHz reference",
            "Output connected to 5V input without level consideration",
        ],
    },

    # ---- Protection / Power ICs ----
    "Diode_TVS:SMBJ*": {
        "category": "protection",
        "description": "TVS (Transient Voltage Suppressor) diode — SMB package",
        "checks": ["polarity_correct"],
        "notes": "Place as close as possible to the connector/line being protected. Select breakdown voltage ~10% above normal operating voltage. Unidirectional or bidirectional versions.",
        "common_mistakes": [
            "TVS too far from protected line — inductance reduces effectiveness",
            "Breakdown voltage too close to operating voltage — TVS conducts during normal operation",
        ],
    },
    "Diode_TVS:TPD2E009*": {
        "category": "protection",
        "description": "2-channel ESD protection for USB/HDMI",
        "operating_voltage": {"max": 6.0},
        "checks": [],
        "notes": "Place as close to connector as possible. Low capacitance (~0.5pF) for high-speed data lines. No power supply needed.",
        "common_mistakes": [
            "Placed far from connector — reduced ESD protection",
        ],
    },
    "Power_Management:TPS65217*": {
        "category": "power",
        "description": "PMIC — integrated power management IC (I2C)",
        "operating_voltage": {"input_min": 4.3, "input_max": 5.8, "typical": 5.0},
        "checks": ["decoupling_caps", "i2c_pullups"],
        "notes": "Complex PMIC with 3 buck converters, 2 LDOs, and battery charger. Used in BeagleBone. Requires careful layout per datasheet. I2C address 0x24.",
        "common_mistakes": [
            "Not following reference layout — power management ICs are layout-sensitive",
            "Missing sequencing configuration — regulators may not start in correct order",
        ],
    },
    "Power_Switch:TPS22918*": {
        "category": "power",
        "description": "5.5V, 2A load switch",
        "operating_voltage": {"min": 1.62, "max": 5.5, "typical": 3.3},
        "checks": ["decoupling_caps"],
        "notes": "ON/OFF pin controls output. Quick output discharge (QOD) when off. CT pin sets rise time (cap to GND). Needs 1uF input + 1uF output caps.",
        "common_mistakes": [
            "CT pin floating — uncontrolled rise time, inrush current",
            "Output cap too large without CT cap — inrush triggers overcurrent",
        ],
    },
    "Power_Protection:TPS2596*": {
        "category": "protection",
        "description": "eFuse — electronic fuse with current limiting",
        "operating_voltage": {"min": 2.7, "max": 19.0, "typical": 12.0},
        "checks": ["decoupling_caps"],
        "notes": "Programmable current limit via ILIM resistor. dVdT pin controls inrush. FLT pin is open-drain fault output. OVP pin for overvoltage threshold. Needs 100nF on VIN.",
        "common_mistakes": [
            "ILIM resistor wrong value — current limit too high or too low",
            "dVdT cap missing — output slew rate too fast, causes inrush",
        ],
    },
    "Reference_Voltage:REF3033*": {
        "category": "reference",
        "description": "3.3V precision voltage reference",
        "operating_voltage": {"min": 3.6, "max": 12.0},
        "checks": ["decoupling_caps"],
        "notes": "Low-drift 3.3V reference. Needs 100nF on input and output (ceramic). Output can source 25mA max. Place decoupling caps close to pins.",
        "common_mistakes": [
            "Loading output beyond 25mA — output drops out of regulation",
            "Using as a power supply — voltage references are for precision, not power",
        ],
    },
    "Reference_Voltage:REF5050*": {
        "category": "reference",
        "description": "5.0V precision voltage reference",
        "operating_voltage": {"min": 5.25, "max": 36.0},
        "checks": ["decoupling_caps"],
        "notes": "Low-noise 5.0V reference. Needs 1uF on input and 1uF on output. Has noise-reduction NR pin (add 100nF cap). Place decoupling close to device.",
        "common_mistakes": [
            "NR pin floating — higher output noise than spec",
            "Input voltage too close to output — insufficient headroom",
        ],
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

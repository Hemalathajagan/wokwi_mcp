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
            "13": {"type": "digital", "pwm": False, "direction": "io"},
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
    # -----------------------------------------------------------------------
    # ESP32
    # -----------------------------------------------------------------------
    "wokwi-esp32-devkit-v1": {
        "pins": {
            **{str(i): {
                "type": "digital",
                "pwm": i not in (6, 7, 8, 9, 10, 11),  # flash pins have no PWM
                "direction": "input" if i in (34, 35, 36, 39) else "io",
                "input_only": i in (34, 35, 36, 39),
                "flash_pin": i in (6, 7, 8, 9, 10, 11),
                "strapping_pin": i in (0, 2, 12),
                "adc": (
                    "ADC1" if i in (32, 33, 34, 35, 36, 39) else
                    "ADC2" if i in (0, 2, 4, 12, 13, 14, 15, 25, 26, 27) else
                    None
                ),
                "dac": i in (25, 26),
            } for i in range(40)},
            "GND.1": {"type": "ground"},
            "GND.2": {"type": "ground"},
            "3V3": {"type": "power", "voltage": 3.3},
            "VIN": {"type": "power"},
            "5V": {"type": "power", "voltage": 5.0},
        },
        "max_pin_current_ma": 40,
        "max_total_current_ma": 1200,
        "operating_voltage": 3.3,
        "requires_power": False,
        "i2c_sda": "21",
        "i2c_scl": "22",
        "spi_mosi": "23",
        "spi_miso": "19",
        "spi_sck": "18",
        "flash_pins": [6, 7, 8, 9, 10, 11],
        "input_only_pins": [34, 35, 36, 39],
        "strapping_pins": [0, 2, 12],
        "has_wifi": True,
        "has_bluetooth": True,
        "notes": "3.3V logic, NOT 5V tolerant. GPIO6-11 are flash pins (do not use). GPIO34-39 are input-only. Built-in WiFi and Bluetooth.",
    },
    # -----------------------------------------------------------------------
    # Raspberry Pi Pico
    # -----------------------------------------------------------------------
    "wokwi-pi-pico": {
        "pins": {
            **{f"GP{i}": {
                "type": "digital",
                "pwm": True,
                "direction": "io",
                "adc": f"ADC{i - 26}" if i in (26, 27, 28) else None,
            } for i in range(26)},
            "GND.1": {"type": "ground"},
            "GND.2": {"type": "ground"},
            "3V3": {"type": "power", "voltage": 3.3},
            "VSYS": {"type": "power", "voltage": 5.0},
            "VBUS": {"type": "power", "voltage": 5.0},
        },
        "max_pin_current_ma": 16,
        "max_total_current_ma": 300,
        "operating_voltage": 3.3,
        "requires_power": False,
        "i2c_sda": "GP0",
        "i2c_scl": "GP1",
        "notes": "3.3V logic, NOT 5V tolerant. All GPIO pins support PWM. ADC on GP26-GP28. Programmed with MicroPython or C/C++ SDK.",
    },
    # -----------------------------------------------------------------------
    # ATtiny85
    # -----------------------------------------------------------------------
    "wokwi-attiny85": {
        "pins": {
            "PB0": {"type": "digital", "pwm": True, "direction": "io"},
            "PB1": {"type": "digital", "pwm": True, "direction": "io"},
            "PB2": {"type": "digital", "pwm": False, "direction": "io", "adc": "ADC1"},
            "PB3": {"type": "digital", "pwm": False, "direction": "io", "adc": "ADC3"},
            "PB4": {"type": "digital", "pwm": False, "direction": "io", "adc": "ADC2"},
            "PB5": {"type": "digital", "pwm": False, "direction": "io", "is_reset": True},
            "VCC": {"type": "power", "voltage": 5.0},
            "GND": {"type": "ground"},
        },
        "max_pin_current_ma": 40,
        "max_total_current_ma": 200,
        "operating_voltage": 5.0,
        "requires_power": False,
        "notes": "Only 5 usable GPIO pins (PB5 is RESET). No hardware UART — use SoftwareSerial. Very limited resources (8KB flash, 512B RAM).",
    },
    # -----------------------------------------------------------------------
    # STM32 Bluepill
    # -----------------------------------------------------------------------
    "board-stm32-bluepill": {
        "pins": {
            **{f"PA{i}": {
                "type": "digital",
                "pwm": i in (0, 1, 2, 3, 6, 7, 8, 9, 10),
                "direction": "io",
                "adc": True if i <= 7 else None,
            } for i in range(16)},
            **{f"PB{i}": {
                "type": "digital",
                "pwm": i in (0, 1, 6, 7, 8, 9),
                "direction": "io",
                "adc": True if i <= 1 else None,
            } for i in range(16)},
            "PC13": {"type": "digital", "pwm": False, "direction": "io", "notes": "Built-in LED"},
            "PC14": {"type": "digital", "pwm": False, "direction": "io"},
            "PC15": {"type": "digital", "pwm": False, "direction": "io"},
            "GND.1": {"type": "ground"},
            "GND.2": {"type": "ground"},
            "3.3V": {"type": "power", "voltage": 3.3},
            "5V": {"type": "power", "voltage": 5.0},
        },
        "max_pin_current_ma": 25,
        "max_total_current_ma": 150,
        "operating_voltage": 3.3,
        "five_v_tolerant": True,
        "requires_power": False,
        "i2c_sda": "PB7",
        "i2c_scl": "PB6",
        "spi_mosi": "PA7",
        "spi_miso": "PA6",
        "spi_sck": "PA5",
        "notes": "3.3V logic but most GPIO pins are 5V tolerant. USART1: TX=PA9/RX=PA10, USART2: TX=PA2/RX=PA3.",
    },
    # -----------------------------------------------------------------------
    # Components
    # -----------------------------------------------------------------------
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
    # -----------------------------------------------------------------------
    # Wireless modules
    # -----------------------------------------------------------------------
    "wokwi-hc-05": {
        "pins": {
            "VCC": {"type": "power_in"},
            "GND": {"type": "ground_in"},
            "TXD": {"type": "data_out"},
            "RXD": {"type": "data_in"},
            "EN": {"type": "digital"},
            "STATE": {"type": "digital_out"},
        },
        "requires_power": True,
        "operating_voltage": 3.3,
        "power_voltage": 5.0,
        "current_draw_ma": 50,
        "protocol": "uart",
        "default_baud": 38400,
        "wireless_type": "bluetooth_classic",
        "notes": "RXD is 3.3V logic — needs voltage divider from 5V Arduino TX. TX→RX crossover required. Default baud 38400 (AT mode: 38400).",
    },
    "wokwi-hc-06": {
        "pins": {
            "VCC": {"type": "power_in"},
            "GND": {"type": "ground_in"},
            "TXD": {"type": "data_out"},
            "RXD": {"type": "data_in"},
        },
        "requires_power": True,
        "operating_voltage": 3.3,
        "power_voltage": 5.0,
        "current_draw_ma": 40,
        "protocol": "uart",
        "default_baud": 9600,
        "wireless_type": "bluetooth_classic",
        "notes": "RXD is 3.3V logic — needs voltage divider from 5V Arduino TX. TX→RX crossover required. Default baud 9600.",
    },
    "wokwi-hm-10": {
        "pins": {
            "VCC": {"type": "power_in"},
            "GND": {"type": "ground_in"},
            "TXD": {"type": "data_out"},
            "RXD": {"type": "data_in"},
        },
        "requires_power": True,
        "operating_voltage": 3.3,
        "current_draw_ma": 50,
        "protocol": "uart",
        "default_baud": 9600,
        "wireless_type": "bluetooth_ble",
        "notes": "BLE 4.0 module. 3.3V only — do NOT power from 5V. RXD needs 3.3V logic. Default baud 9600.",
    },
    "wokwi-esp01": {
        "pins": {
            "VCC": {"type": "power_in"},
            "GND": {"type": "ground_in"},
            "TX": {"type": "data_out"},
            "RX": {"type": "data_in"},
            "CH_PD": {"type": "digital", "notes": "Must be pulled HIGH to enable"},
            "RST": {"type": "digital"},
            "GPIO0": {"type": "digital"},
            "GPIO2": {"type": "digital"},
        },
        "requires_power": True,
        "operating_voltage": 3.3,
        "current_draw_ma": 300,
        "protocol": "uart",
        "default_baud": 115200,
        "wireless_type": "wifi",
        "notes": "3.3V ONLY — NOT 5V tolerant. Draws up to 300mA peak (Arduino 3.3V pin can only supply 50mA). CH_PD must be pulled HIGH. TX→RX crossover required.",
    },
    "wokwi-nrf24l01": {
        "pins": {
            "VCC": {"type": "power_in"},
            "GND": {"type": "ground_in"},
            "CE": {"type": "digital"},
            "CSN": {"type": "digital"},
            "SCK": {"type": "spi_clock"},
            "MOSI": {"type": "spi_data_in"},
            "MISO": {"type": "spi_data_out"},
            "IRQ": {"type": "digital_out"},
        },
        "requires_power": True,
        "operating_voltage": 3.3,
        "current_draw_ma": 115,
        "protocol": "spi",
        "wireless_type": "rf_2_4ghz",
        "notes": "3.3V ONLY — connecting to 5V will damage the module. Add 10µF capacitor across VCC-GND for stability. SPI pins: SCK=13, MOSI=11, MISO=12 on Uno.",
    },
    "wokwi-ir-receiver": {
        "pins": {
            "VCC": {"type": "power_in"},
            "GND": {"type": "ground_in"},
            "OUT": {"type": "data_out"},
        },
        "requires_power": True,
        "operating_voltage": 5.0,
        "current_draw_ma": 5,
        "wireless_type": "ir",
        "notes": "Data pin should connect to an interrupt-capable pin (2 or 3 on Uno) for reliable IR decoding.",
    },
    "wokwi-ir-led": {
        "pins": {
            "A": {"type": "anode"},
            "C": {"type": "cathode"},
        },
        "requires_power": True,
        "needs_resistor": True,
        "typical_resistor_ohms": 100,
        "max_current_ma": 50,
        "wireless_type": "ir",
        "notes": "IR transmitter LED. Needs current-limiting resistor. Signal pin should be PWM-capable for 38kHz carrier generation.",
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
    # Wireless module rules
    {
        "id": "bluetooth_tx_rx_crossover",
        "description": "Bluetooth module TX must connect to Arduino RX and vice versa (TX→RX crossover)",
        "applies_to": ["wokwi-hc-05", "wokwi-hc-06", "wokwi-hm-10"],
        "severity": "error",
    },
    {
        "id": "bluetooth_rx_voltage_divider",
        "description": "HC-05/HC-06 RXD pin is 3.3V logic — needs voltage divider when connected to 5V Arduino TX",
        "applies_to": ["wokwi-hc-05", "wokwi-hc-06"],
        "severity": "warning",
    },
    {
        "id": "esp01_power_requirements",
        "description": "ESP-01 needs 3.3V and draws up to 300mA — cannot be powered from Arduino 3.3V pin (50mA max)",
        "applies_to": ["wokwi-esp01"],
        "severity": "error",
    },
    {
        "id": "nrf24l01_spi_pins",
        "description": "nRF24L01 SPI pins must connect to correct Arduino SPI pins (SCK=13, MOSI=11, MISO=12 on Uno)",
        "applies_to": ["wokwi-nrf24l01"],
        "severity": "error",
    },
    {
        "id": "nrf24l01_voltage",
        "description": "nRF24L01 is 3.3V only — connecting VCC to 5V will damage the module",
        "applies_to": ["wokwi-nrf24l01"],
        "severity": "error",
    },
    {
        "id": "ir_receiver_interrupt_pin",
        "description": "IR receiver data pin should connect to an interrupt-capable pin (2 or 3 on Uno) for reliable decoding",
        "applies_to": ["wokwi-ir-receiver"],
        "severity": "warning",
    },
    {
        "id": "wireless_serial_conflict",
        "description": "Using hardware Serial pins (0/1) for wireless modules conflicts with USB serial (upload/debug)",
        "applies_to": ["wokwi-hc-05", "wokwi-hc-06", "wokwi-hm-10", "wokwi-esp01"],
        "severity": "warning",
    },
    # Board-specific rules
    {
        "id": "esp32_flash_pins",
        "description": "ESP32 GPIO6-11 are connected to internal flash memory and must not be used for external connections",
        "applies_to": ["wokwi-esp32-devkit-v1"],
        "severity": "error",
    },
    {
        "id": "esp32_input_only_pins",
        "description": "ESP32 GPIO34, 35, 36, 39 are input-only — cannot be used for OUTPUT, PWM, or driving components",
        "applies_to": ["wokwi-esp32-devkit-v1"],
        "severity": "error",
    },
    {
        "id": "esp32_strapping_pins",
        "description": "ESP32 GPIO0, 2, 12 are strapping pins that affect boot mode — avoid pull-ups/downs on these unless intended",
        "applies_to": ["wokwi-esp32-devkit-v1"],
        "severity": "warning",
    },
    {
        "id": "board_3v3_voltage",
        "description": "ESP32, Pi Pico, and STM32 are 3.3V boards — 5V components/signals may damage GPIO pins",
        "applies_to": ["wokwi-esp32-devkit-v1", "wokwi-pi-pico", "board-stm32-bluepill"],
        "severity": "error",
    },
    {
        "id": "attiny_limited_pins",
        "description": "ATtiny85 has only 5 usable GPIO pins (PB5 is RESET) — check for pin conflicts",
        "applies_to": ["wokwi-attiny85"],
        "severity": "info",
    },
]

# Arduino boards for identification
SUPPORTED_BOARDS = {
    "wokwi-arduino-uno",
    "wokwi-arduino-mega",
    "wokwi-arduino-nano",
    "wokwi-esp32-devkit-v1",
    "wokwi-pi-pico",
    "wokwi-attiny85",
    "board-stm32-bluepill",
}

# Boards that operate at 3.3V logic (NOT 5V tolerant unless specified)
THREE_V3_BOARDS = {
    "wokwi-esp32-devkit-v1",
    "wokwi-pi-pico",
    "board-stm32-bluepill",
}

# Pin types that indicate power connections
POWER_PIN_TYPES = {"power", "power_in", "power_out"}
GROUND_PIN_TYPES = {"ground", "ground_in", "ground_out"}
SIGNAL_PIN_TYPES = {"digital", "analog", "signal", "data", "data_in", "data_out",
                    "digital_in", "digital_out", "analog_out", "i2c_data", "i2c_clock",
                    "spi_clock", "spi_data_in", "spi_data_out"}

# Components that use UART serial (TX/RX) communication
UART_MODULES = {"wokwi-hc-05", "wokwi-hc-06", "wokwi-hm-10", "wokwi-esp01"}

# Components that are 3.3V logic and NOT 5V tolerant
THREE_V3_ONLY_MODULES = {"wokwi-hm-10", "wokwi-esp01", "wokwi-nrf24l01"}

# Wireless module types
WIRELESS_MODULES = {"wokwi-hc-05", "wokwi-hc-06", "wokwi-hm-10", "wokwi-esp01",
                    "wokwi-nrf24l01", "wokwi-ir-receiver", "wokwi-ir-led"}


# ---------------------------------------------------------------------------
# Popular Arduino library knowledge base
# ---------------------------------------------------------------------------

LIBRARY_KNOWLEDGE = {
    "Servo": {
        "header": "Servo.h",
        "related_components": ["wokwi-servo"],
        "required_init": "servo.attach(pin)",
        "common_functions": ["attach", "write", "writeMicroseconds", "read", "attached", "detach"],
        "common_mistakes": [
            "Calling write() before attach() — servo won't move",
            "Using angle > 180 with write() — valid range is 0-180",
            "Not connecting servo to PWM pin (required for Servo library)",
            "Powering servo from Arduino 5V pin — draws too much current, use external supply",
        ],
        "notes": "Each servo uses one timer. On Uno, using Servo disables PWM on pins 9 and 10.",
    },
    "LiquidCrystal": {
        "header": "LiquidCrystal.h",
        "related_components": ["wokwi-lcd1602"],
        "required_init": "lcd.begin(cols, rows)",
        "common_functions": ["begin", "clear", "setCursor", "print", "display", "noDisplay", "scrollDisplayLeft", "createChar"],
        "common_mistakes": [
            "Missing lcd.begin(16, 2) in setup() — display won't initialize",
            "Wrong pin order in constructor: LiquidCrystal(rs, en, d4, d5, d6, d7)",
            "Using setCursor(col, row) with wrong order — it's (column, row), not (row, column)",
            "Calling print() without setCursor() — text appears at last cursor position",
        ],
        "notes": "For I2C LCD (most common on Wokwi), use LiquidCrystal_I2C library instead.",
    },
    "LiquidCrystal_I2C": {
        "header": "LiquidCrystal_I2C.h",
        "related_components": ["wokwi-lcd1602"],
        "required_init": "lcd.begin() or lcd.init()",
        "common_functions": ["init", "begin", "backlight", "noBacklight", "clear", "setCursor", "print", "createChar"],
        "common_mistakes": [
            "Wrong I2C address — default is 0x27, some modules use 0x3F",
            "Missing lcd.backlight() — display is on but not visible without backlight",
            "Not connecting SDA to A4 and SCL to A5 on Uno (or GPIO21/22 on ESP32)",
            "Missing Wire.h include — LiquidCrystal_I2C depends on Wire library",
        ],
        "notes": "Default I2C address for Wokwi LCD1602 is 0x27. Use I2C scanner sketch if unsure.",
    },
    "Wire": {
        "header": "Wire.h",
        "related_components": ["wokwi-lcd1602"],
        "required_init": "Wire.begin()",
        "common_functions": ["begin", "beginTransmission", "endTransmission", "write", "read", "requestFrom", "available"],
        "common_mistakes": [
            "Missing Wire.begin() in setup()",
            "Not calling endTransmission() after beginTransmission() — data never sent",
            "Wrong I2C pins — Uno: A4(SDA)/A5(SCL), Mega: 20(SDA)/21(SCL), ESP32: 21(SDA)/22(SCL)",
            "Missing pull-up resistors on SDA/SCL (Arduino has internal pull-ups, but external 4.7kΩ recommended for long wires)",
        ],
        "notes": "I2C bus: SDA and SCL must connect to correct board-specific pins.",
    },
    "SPI": {
        "header": "SPI.h",
        "related_components": ["wokwi-nrf24l01"],
        "required_init": "SPI.begin()",
        "common_functions": ["begin", "end", "transfer", "beginTransaction", "endTransaction", "setBitOrder", "setClockDivider"],
        "common_mistakes": [
            "Using wrong SPI pins — Uno: MOSI=11, MISO=12, SCK=13; Mega: MOSI=51, MISO=50, SCK=52",
            "Forgetting to set CS/SS pin as OUTPUT and drive it LOW before transfer",
            "Not calling SPI.beginTransaction() with correct speed/mode for the device",
        ],
        "notes": "SPI pins are fixed by hardware. CS/SS pin can be any digital pin.",
    },
    "Adafruit_NeoPixel": {
        "header": "Adafruit_NeoPixel.h",
        "related_components": ["wokwi-neopixel"],
        "required_init": "strip.begin()",
        "common_functions": ["begin", "show", "setPixelColor", "clear", "setBrightness", "Color", "numPixels", "fill"],
        "common_mistakes": [
            "Missing strip.begin() in setup()",
            "Calling setPixelColor() without strip.show() — LEDs won't update until show() is called",
            "Wrong pixel count in constructor — must match actual number of LEDs",
            "Using Color(R,G,B) with values > 255",
            "Not calling strip.clear() before setting new colors — old colors persist",
        ],
        "notes": "NeoPixels need 5V power and a 300-500Ω resistor on the data line. Add 1000µF capacitor across power for large strips.",
    },
    "DHT": {
        "header": "DHT.h",
        "related_components": ["wokwi-dht22"],
        "required_init": "dht.begin()",
        "common_functions": ["begin", "readTemperature", "readHumidity", "computeHeatIndex"],
        "common_mistakes": [
            "Missing dht.begin() in setup()",
            "Wrong DHT type in constructor — use DHT22 for DHT22, DHT11 for DHT11",
            "Reading too frequently — DHT22 needs 2 seconds between reads",
            "Not checking for NaN returns — readTemperature() returns NaN on read failure",
            "Missing 10kΩ pull-up resistor on data pin (some modules have built-in pull-up)",
        ],
        "notes": "DHT22 is more accurate than DHT11. Use isnan() to check for read failures.",
    },
    "SoftwareSerial": {
        "header": "SoftwareSerial.h",
        "related_components": ["wokwi-hc-05", "wokwi-hc-06", "wokwi-hm-10", "wokwi-esp01"],
        "required_init": "mySerial.begin(baud)",
        "common_functions": ["begin", "available", "read", "write", "print", "println", "listen"],
        "common_mistakes": [
            "Wrong baud rate — must match the connected module (HC-06: 9600, HC-05: 38400, ESP-01: 115200)",
            "Using pins that don't support pin change interrupts for RX",
            "Using SoftwareSerial on ESP32 — ESP32 has 3 hardware UARTs, use HardwareSerial instead",
            "Not calling listen() when using multiple SoftwareSerial instances — only one can receive at a time",
            "TX/RX pin order in constructor: SoftwareSerial(RX, TX) — RX first, TX second",
        ],
        "notes": "SoftwareSerial is unreliable above 57600 baud. ESP32 doesn't need it — use Serial1 or Serial2.",
    },
    "RF24": {
        "header": "RF24.h",
        "related_components": ["wokwi-nrf24l01"],
        "required_init": "radio.begin()",
        "common_functions": ["begin", "openWritingPipe", "openReadingPipe", "startListening", "stopListening", "write", "read", "available", "setPALevel", "setDataRate"],
        "common_mistakes": [
            "Wrong CE/CSN pins in constructor — RF24(CE_PIN, CSN_PIN)",
            "Missing radio.begin() — returns false if module not connected properly",
            "Not calling stopListening() before write() — transmitter must stop listening first",
            "Pipe addresses must match between transmitter and receiver",
            "Not setting same data rate and PA level on both ends",
            "Powering from 5V — nRF24L01 is 3.3V only",
        ],
        "notes": "Add 10µF capacitor between VCC and GND of nRF24L01 for stability. Use setPALevel(RF24_PA_LOW) for testing.",
    },
    "IRremote": {
        "header": "IRremote.h",
        "related_components": ["wokwi-ir-receiver", "wokwi-ir-led"],
        "required_init": "IrReceiver.begin(pin) or irrecv.enableIRIn()",
        "common_functions": ["begin", "enableIRIn", "decode", "resume", "send", "sendNEC", "sendSony", "available"],
        "common_mistakes": [
            "Using old API (IRrecv/decode_results) with new IRremote v4 — use IrReceiver.begin() instead",
            "Not calling resume() or IrReceiver.resume() after processing — stops receiving next signal",
            "IR receiver on non-interrupt pin — use pin 2 or 3 on Uno for reliability",
            "IR LED not on PWM pin — needs PWM for 38kHz carrier frequency",
        ],
        "notes": "IRremote v3+ changed API significantly. Wokwi typically uses newer versions.",
    },
    "Stepper": {
        "header": "Stepper.h",
        "related_components": ["wokwi-stepper-motor"],
        "required_init": "Stepper(steps, pin1, pin2, pin3, pin4)",
        "common_functions": ["setSpeed", "step"],
        "common_mistakes": [
            "Wrong step count — 28BYJ-48 has 2048 steps per revolution (with gear ratio), not 200",
            "Connecting stepper directly to Arduino pins — use ULN2003 driver",
            "Wrong pin order in constructor — must match driver wiring (IN1, IN3, IN2, IN4 for ULN2003)",
            "Setting speed too high — stepper will skip steps. Start with setSpeed(10)",
        ],
        "notes": "For 28BYJ-48 with ULN2003: use Stepper(2048, IN1, IN3, IN2, IN4). Pin order matters!",
    },
    "ESP32_WiFi": {
        "header": "WiFi.h",
        "related_components": ["wokwi-esp32-devkit-v1"],
        "required_init": "WiFi.begin(ssid, password)",
        "common_functions": ["begin", "status", "localIP", "disconnect", "reconnect", "RSSI", "scanNetworks"],
        "common_mistakes": [
            "Not waiting for connection — check WiFi.status() == WL_CONNECTED in a loop",
            "Using String for SSID/password — use const char* to avoid memory issues",
            "Not handling disconnection — WiFi can drop, add reconnection logic",
            "Using ADC2 pins while WiFi is active — ADC2 is shared with WiFi, use ADC1 (GPIO32-39) instead",
        ],
        "notes": "ESP32-specific. WiFi.begin() is non-blocking — must wait for WL_CONNECTED status.",
    },
    "AccelStepper": {
        "header": "AccelStepper.h",
        "related_components": ["wokwi-stepper-motor"],
        "required_init": "stepper.setMaxSpeed(speed); stepper.setAcceleration(accel)",
        "common_functions": ["setMaxSpeed", "setAcceleration", "moveTo", "move", "run", "runToPosition", "currentPosition", "setCurrentPosition"],
        "common_mistakes": [
            "Not calling run() in loop() — motor won't move without continuous run() calls",
            "Missing setMaxSpeed() — default is very slow",
            "Using runToPosition() in loop — this blocks until position reached",
            "Wrong interface type in constructor (FULL4WIRE vs DRIVER for different setups)",
        ],
        "notes": "AccelStepper provides acceleration/deceleration. More flexible than built-in Stepper library.",
    },
    "Keypad": {
        "header": "Keypad.h",
        "related_components": ["wokwi-membrane-keypad"],
        "required_init": "Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS)",
        "common_functions": ["getKey", "getKeys", "waitForKey", "addEventListener", "setHoldTime", "setDebounceTime"],
        "common_mistakes": [
            "Wrong row/column pin mapping — verify which pins connect to rows vs columns",
            "Key map array doesn't match physical layout — rows and columns swapped",
            "Only checking getKey() once per loop — returns NO_KEY if not pressed at that exact moment",
            "Using pins with pull-ups/pull-downs that interfere with keypad matrix scanning",
        ],
        "notes": "4x4 keypad needs 8 pins. For fewer pins, consider I2C keypad expander.",
    },
}


def get_library_knowledge(sketch_code: str) -> str:
    """Build library reference text based on #include directives found in the sketch."""
    if not sketch_code:
        return ""

    lines = []
    for lib_name, info in LIBRARY_KNOWLEDGE.items():
        header = info["header"]
        # Check if this library is included in the sketch
        if f"#include <{header}>" in sketch_code or f'#include "{header}"' in sketch_code:
            lines.append(f"\n### {lib_name} ({header})")
            lines.append(f"- Required init: `{info['required_init']}`")
            lines.append(f"- Functions: {', '.join(info['common_functions'])}")
            lines.append("- Common mistakes:")
            for mistake in info["common_mistakes"]:
                lines.append(f"  - {mistake}")
            if info.get("notes"):
                lines.append(f"- Note: {info['notes']}")

    return "\n".join(lines) if lines else ""


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
            if info.get("operating_voltage"):
                line += f" | operating voltage: {info['operating_voltage']}V"
            if info.get("default_baud"):
                line += f" | default baud: {info['default_baud']}"
            if info.get("wireless_type"):
                line += f" | wireless: {info['wireless_type']}"
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
        if part.get("type") in SUPPORTED_BOARDS:
            return part["type"]
    return None

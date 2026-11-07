# ESP32 firmware

1. Install PlatformIO in VS Code or install the PlatformIO CLI.
2. Edit `src/main.cpp`: Wi-Fi credentials, API host, sensor pin, and experimentally calibrated pulses/litre.
3. Verify the flow sensor signal voltage before connecting to ESP32 GPIO. Use suitable level shifting/protection if required.
4. Compile with `pio run`, flash with `pio run -t upload`, and monitor with `pio device monitor`.
5. The example sends interval litres every 5 seconds. Test with measured water volumes and record calibration error.

Do not commit real credentials. This prototype has no persistent offline queue; a failed POST can lose that interval's reading.

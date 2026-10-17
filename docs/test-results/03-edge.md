# Stage 3 — ingestion and edge reference

- 4 local gateway unit tests passed: restart/retry, conflict, read-only register, simulation labeling.
- Reading schema tests validate finite values, units, future timestamps, interval semantics.
- PostgreSQL ingestion integration still pending CI.
- Actual Modbus RTU/TCP hardware and ESP32 firmware are not validated. This is an industrial-PC
  reference adapter with a configurable single unsigned register, not a universal meter driver.

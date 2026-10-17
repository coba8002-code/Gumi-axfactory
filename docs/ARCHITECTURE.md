# Architecture v0.1

Factory equipment / electrical meters -> industrial gateway (Modbus RTU/TCP; Ethernet) -> authenticated ingestion API -> PostgreSQL/time-series tables -> reports and anomaly analytics.

Tablet PWA -> authenticated business API -> incident/maintenance/inspection records -> approval -> knowledge retrieval -> AI assistant with source evidence.

Admin web -> company-specific dashboards -> daily/monthly exports. Municipality gets only consented aggregates.

## Hardware
Base per factory: main 3-phase power meter + selected 2-3 sub-meters + one gateway. Reuse existing FEMS/PLC/CNC data where authorized. Waveshare ESP32-S3-ETH-8DI-8RO is a candidate acquisition node, NOT an electricity meter. CT installation must be handled by qualified personnel.

## Domain entities
Tenant, User, Equipment, Meter, Reading, EquipmentEvent, DowntimeReason, Incident, CorrectiveAction, KnowledgeArticle, Approval, Report, AuditEvent.

## Critical safeguards
Tenant isolation, authentication, audit trail, offline synchronization, event deduplication, timestamp normalization, data provenance, verified knowledge approval, no automatic PLC actuation.

## DeepSeek Harness
External agent orchestration candidate, not a dependency for initial operational path. Sandbox, pin, and test before deployment.


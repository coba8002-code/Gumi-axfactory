"""Authenticated meter streams with interval semantics and provenance."""
from alembic import op
revision = "002"
down_revision = "001"


def upgrade():
    op.execute("""
    CREATE TABLE sensors (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, factory_id uuid NOT NULL,
      equipment_id uuid NOT NULL, device_id uuid NOT NULL, name text NOT NULL,
      UNIQUE(tenant_id,factory_id,id),
      FOREIGN KEY(tenant_id,factory_id,equipment_id) REFERENCES equipment(tenant_id,factory_id,id),
      FOREIGN KEY(tenant_id,factory_id,device_id) REFERENCES identities(tenant_id,factory_id,id)
    );
    CREATE TABLE readings (
      id bigserial PRIMARY KEY, tenant_id uuid NOT NULL, factory_id uuid NOT NULL,
      sensor_id uuid NOT NULL, event_id uuid NOT NULL, observed_at timestamptz NOT NULL,
      received_at timestamptz NOT NULL DEFAULT now(),
      metric text NOT NULL CHECK(metric IN ('power_kw','energy_kwh_interval','temperature_c')),
      value double precision NOT NULL, unit text NOT NULL,
      interval_seconds integer, quality text NOT NULL CHECK(quality IN ('good','estimated','bad')),
      source text NOT NULL CHECK(source IN ('simulator','modbus_tcp','modbus_rtu')),
      firmware_version text NOT NULL, payload_hash char(64) NOT NULL,
      UNIQUE(tenant_id,factory_id,sensor_id,event_id),
      FOREIGN KEY(tenant_id,factory_id,sensor_id) REFERENCES sensors(tenant_id,factory_id,id),
      CHECK(metric <> 'energy_kwh_interval' OR (value >= 0 AND interval_seconds > 0))
    );
    CREATE INDEX reading_scope_time ON readings(tenant_id,factory_id,sensor_id,observed_at);
    """)


def downgrade():
    raise RuntimeError("Restore a verified backup instead.")

"""Immutable period snapshots and explicit estimate inputs."""
from alembic import op
revision="003"
down_revision="002"


def upgrade():
    op.execute("""
    CREATE TABLE reports (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,factory_id uuid NOT NULL,
      period text NOT NULL,day date NOT NULL,sensor_id uuid,
      document jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE NULLS NOT DISTINCT(tenant_id,factory_id,period,day,sensor_id),
      FOREIGN KEY(tenant_id,factory_id,sensor_id) REFERENCES sensors(tenant_id,factory_id,id)
    );
    CREATE TABLE energy_assessments (
      id uuid PRIMARY KEY,tenant_id uuid NOT NULL,factory_id uuid NOT NULL,
      actor_id uuid NOT NULL,inputs jsonb NOT NULL,result jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now()
    );
    """)


def downgrade():
    raise RuntimeError("Restore a verified backup instead.")

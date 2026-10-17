"""Factory-scoped durable AutoLog."""
from alembic import op
revision = "001"
down_revision = None


def upgrade():
    op.execute("""
    CREATE TABLE identities (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, factory_id uuid NOT NULL,
      role text NOT NULL CHECK(role IN ('worker','supervisor','admin','device')),
      token_hash char(64) NOT NULL UNIQUE, active boolean NOT NULL DEFAULT true,
      UNIQUE(tenant_id,factory_id,id)
    );
    CREATE TABLE equipment (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, factory_id uuid NOT NULL, name text NOT NULL,
      UNIQUE(tenant_id,factory_id,id)
    );
    CREATE TABLE incidents (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, factory_id uuid NOT NULL,
      equipment_id uuid NOT NULL, created_by uuid NOT NULL,
      reason text NOT NULL CHECK(reason IN ('fault','tool','material','setup','other')),
      notes text NOT NULL, started_at timestamptz NOT NULL, ended_at timestamptz, original_ended_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(),
      approved boolean NOT NULL DEFAULT false, approved_by uuid, approved_at timestamptz, evidence text,
      CHECK(ended_at IS NULL OR ended_at >= started_at),
      CHECK(NOT approved OR (approved_by IS NOT NULL AND approved_at IS NOT NULL AND evidence IS NOT NULL AND ended_at IS NOT NULL)),
      UNIQUE(tenant_id,factory_id,id),
      FOREIGN KEY(tenant_id,factory_id,equipment_id) REFERENCES equipment(tenant_id,factory_id,id),
      FOREIGN KEY(tenant_id,factory_id,created_by) REFERENCES identities(tenant_id,factory_id,id),
      FOREIGN KEY(tenant_id,factory_id,approved_by) REFERENCES identities(tenant_id,factory_id,id)
    );
    CREATE TABLE corrective_actions (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL, factory_id uuid NOT NULL, incident_id uuid NOT NULL,
      actor_id uuid NOT NULL, action text NOT NULL, outcome text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(),
      FOREIGN KEY(tenant_id,factory_id,incident_id) REFERENCES incidents(tenant_id,factory_id,id),
      FOREIGN KEY(tenant_id,factory_id,actor_id) REFERENCES identities(tenant_id,factory_id,id)
    );
    CREATE TABLE audit_events (
      id bigserial PRIMARY KEY, tenant_id uuid NOT NULL, factory_id uuid NOT NULL, actor_id uuid NOT NULL,
      action text NOT NULL, entity_id text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX incident_scope_time ON incidents(tenant_id,factory_id,started_at);
    CREATE INDEX action_scope ON corrective_actions(tenant_id,factory_id,incident_id);
    CREATE INDEX audit_scope ON audit_events(tenant_id,factory_id,id);
    CREATE FUNCTION reject_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Audit events are append-only'; END $$;
    CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON audit_events
      FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
    """)


def downgrade():
    raise RuntimeError("Destructive downgrade disabled; restore a verified backup.")

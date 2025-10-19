-- PostgreSQL DDL for Crossborder EC Automation (v1)
CREATE TABLE products (
  product_id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  process TEXT[],
  origin_country CHAR(2),
  label_media_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE hs_classifications (
  id BIGSERIAL PRIMARY KEY,
  product_id UUID NOT NULL REFERENCES products(product_id),
  hs_candidates JSONB NOT NULL,
  required_uom TEXT,
  final_hs_code TEXT,
  review_required BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_hs_product ON hs_classifications(product_id);

CREATE TABLE document_packages (
  job_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  artifacts JSONB,
  uom_check JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE pn_submissions (
  job_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  payload JSONB NOT NULL,
  receipt_media_id TEXT,
  errors JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tag_def (
  tag_id BIGSERIAL PRIMARY KEY,
  namespace TEXT NOT NULL,
  key TEXT NOT NULL,
  value_type TEXT NOT NULL,
  enum_values TEXT[],
  description TEXT,
  UNIQUE(namespace, key)
);

CREATE TABLE tag_assignment (
  assign_id BIGSERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  tag_id BIGINT NOT NULL REFERENCES tag_def(tag_id),
  value_json JSONB,
  scope JSONB,
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  source TEXT NOT NULL,
  confidence NUMERIC(3,2) DEFAULT 1.0,
  created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_by TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tag_assign_entity ON tag_assignment(entity_type, entity_id);
CREATE INDEX idx_tag_assign_tag ON tag_assignment(tag_id);
CREATE INDEX idx_tag_assign_window ON tag_assignment(effective_from, expires_at);
CREATE INDEX idx_tag_assign_scope ON tag_assignment USING GIN (scope);
CREATE INDEX idx_tag_assign_value ON tag_assignment USING GIN (value_json);

CREATE TABLE audit_event (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT,
  event TEXT NOT NULL,
  actor JSONB NOT NULL,
  at TIMESTAMPTZ NOT NULL DEFAULT now(),
  target JSONB,
  diff JSONB,
  reason TEXT
);
CREATE INDEX idx_audit_trace ON audit_event(trace_id, at);

CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  payload_json JSONB NOT NULL,
  status TEXT NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  next_run_at TIMESTAMPTZ,
  result_json JSONB,
  error_json JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_jobs_status_next ON jobs(status, next_run_at);

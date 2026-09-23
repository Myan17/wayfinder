-- Schema v1, part 2 of 4 (DESIGN §9.2): principals, authorization facts, serving artifacts.
-- Immutable once merged (DESIGN §18.3): fixes are new migrations.

-- migrate:up

-- ─── Principals and authorization ───────────────────────────────────────────
CREATE TABLE principal (
  id             bigserial PRIMARY KEY,
  kind           text NOT NULL CHECK (kind IN ('user','anonymous')),
  github_user_id bigint UNIQUE,
  login          text,
  token_ciphertext   bytea,
  token_expires_at   timestamptz,
  refresh_ciphertext bytea,
  refresh_expires_at timestamptz,
  platform_role  text NOT NULL DEFAULT 'user' CHECK (platform_role IN ('user','operator'))
);
CREATE TABLE session (
  id_hash    bytea PRIMARY KEY,
  principal_id bigint NOT NULL REFERENCES principal(id),
  revoked_at timestamptz,
  expires_at timestamptz NOT NULL
);
CREATE TABLE user_repo_access (
  principal_id bigint NOT NULL REFERENCES principal(id),
  repo_id      bigint NOT NULL REFERENCES repository(id),
  PRIMARY KEY (principal_id, repo_id)
);
CREATE TABLE user_access_state (
  principal_id bigint PRIMARY KEY REFERENCES principal(id),
  authorization_revision bigint NOT NULL DEFAULT 1,
  refreshed_at timestamptz NOT NULL,
  valid_until  timestamptz NOT NULL
);
CREATE TABLE connection_admin (
  connection_id bigint NOT NULL REFERENCES connection(id),
  principal_id  bigint NOT NULL REFERENCES principal(id),
  PRIMARY KEY (connection_id, principal_id)
);

-- ─── Serving artifacts ──────────────────────────────────────────────────────
CREATE TABLE answer (
  id               uuid PRIMARY KEY,
  principal_id     bigint NOT NULL REFERENCES principal(id),
  status           text NOT NULL CHECK (status IN
                     ('pending','streaming','completed','refused','extractive','failed','cancelled')),
  mode             text NOT NULL CHECK (mode IN ('locate','generated','refused','extractive')),
  query            text NOT NULL,
  canonical_text   text,
  citations        jsonb,
  evidence_manifest jsonb NOT NULL,
  classification   text NOT NULL,
  pipeline_config  text NOT NULL,
  degraded         text[] NOT NULL DEFAULT '{}',
  provider         text,
  model            text,
  usage            jsonb,
  terminal_reason  text,
  cached_from      uuid REFERENCES answer(id) ON DELETE SET NULL,
  idempotency_key  bytea,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (principal_id, idempotency_key)
);
CREATE TABLE answer_trace (
  answer_id uuid PRIMARY KEY REFERENCES answer(id) ON DELETE CASCADE,
  trace     jsonb NOT NULL
);
CREATE TABLE answer_cache (
  cache_key  bytea PRIMARY KEY,
  answer_id  uuid NOT NULL REFERENCES answer(id),
  expires_at timestamptz NOT NULL
);
CREATE TABLE feedback (
  answer_id    uuid REFERENCES answer(id) ON DELETE CASCADE,
  principal_id bigint NOT NULL REFERENCES principal(id),
  rating       smallint,
  reason       text,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE audit_event (
  id         bigserial PRIMARY KEY,
  kind       text NOT NULL,
  subject    text,
  detail     jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE webhook_delivery (
  delivery_id uuid PRIMARY KEY,
  received_at timestamptz NOT NULL DEFAULT now()
);

-- migrate:down

DROP TABLE webhook_delivery, audit_event, feedback, answer_cache, answer_trace, answer,
           connection_admin, user_access_state, user_repo_access, session, principal;

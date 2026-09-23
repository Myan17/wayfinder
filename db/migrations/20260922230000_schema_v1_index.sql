-- Schema v1, part 1 of 4 (DESIGN §9.2): sources, generations, the three identities.
-- Part 2: principals and serving artifacts. Part 3: the interface views. Part 4: deletion support.
-- Immutable once merged (DESIGN §18.3): fixes are new migrations.

-- migrate:up

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_search;

-- ─── Sources and tenancy ────────────────────────────────────────────────────
CREATE TABLE connection (
  id             bigserial PRIMARY KEY,
  mode           text NOT NULL CHECK (mode IN ('installation','public_readonly')),
  github_installation_id bigint UNIQUE,
  account_login  text NOT NULL,
  state          text NOT NULL CHECK (state IN ('active','suspended','deleted')),
  state_observed_at timestamptz NOT NULL,
  state_valid_until timestamptz NOT NULL,
  egress_policy  jsonb NOT NULL,
  policy_revision bigint NOT NULL DEFAULT 1,
  config         jsonb NOT NULL
);

CREATE TABLE repository (
  id                bigserial PRIMARY KEY,
  connection_id     bigint NOT NULL REFERENCES connection(id),
  github_repo_id    bigint UNIQUE NOT NULL,
  full_name         text NOT NULL,
  default_branch    text NOT NULL,
  visibility        text NOT NULL CHECK (visibility IN ('public','private','internal')),
  visibility_observed_at timestamptz NOT NULL,
  visibility_valid_until timestamptz NOT NULL,
  serving_state     text NOT NULL CHECK (serving_state IN ('active','denied','removed')),
  data_class        text NOT NULL CHECK (data_class IN ('public','private')),
  authorization_revision bigint NOT NULL DEFAULT 1,
  desired_generation bigint NOT NULL DEFAULT 0,
  claim_token       uuid,
  claim_expires_at  timestamptz,
  active_generation_id bigint,
  license_spdx      text,
  updated_at        timestamptz NOT NULL DEFAULT now()
);

-- ─── Embedding specifications (before generation, which references them) ────
CREATE TABLE embedding_spec (
  id             bigserial PRIMARY KEY,
  model_ref      text NOT NULL,
  model_digest   text NOT NULL,
  runtime        text NOT NULL,
  doc_template   text NOT NULL,
  query_template text NOT NULL,
  pooling        text NOT NULL,
  normalize      boolean NOT NULL,
  dimension      int NOT NULL,
  truncation     text NOT NULL,
  tokenizer_ref  text NOT NULL,
  UNIQUE (model_digest, runtime, doc_template, query_template, pooling, normalize, dimension, truncation)
);

-- ─── Index generations ──────────────────────────────────────────────────────
CREATE TABLE generation (
  id               bigserial PRIMARY KEY,
  repo_id          bigint NOT NULL REFERENCES repository(id),
  desired_generation bigint NOT NULL,
  commit_sha       text NOT NULL,
  spec_id          bigint NOT NULL REFERENCES embedding_spec(id),
  chunker_version  text NOT NULL,
  status           text NOT NULL CHECK (status IN ('building','ready','active','retired','failed')),
  lease_token      uuid,
  heartbeat_at     timestamptz,
  base_generation_id bigint REFERENCES generation(id) ON DELETE SET NULL,
  chunk_count      int,
  skipped_manifest jsonb,
  created_at       timestamptz NOT NULL DEFAULT now(),
  activated_at     timestamptz,
  UNIQUE (repo_id, commit_sha, chunker_version, spec_id, desired_generation),
  UNIQUE (id, repo_id)
);
CREATE UNIQUE INDEX one_active_per_repo ON generation (repo_id) WHERE status = 'active';
ALTER TABLE repository ADD CONSTRAINT repository_active_generation_fk
  FOREIGN KEY (active_generation_id, id) REFERENCES generation (id, repo_id) DEFERRABLE INITIALLY DEFERRED;

-- ─── Content, representation, occurrence: three different identities ────────
CREATE TABLE content (
  content_hash bytea PRIMARY KEY,
  body         text  NOT NULL,
  language     text,
  token_count  int   NOT NULL
);

CREATE TABLE representation (
  id            bigserial PRIMARY KEY,
  repo_id       bigint NOT NULL REFERENCES repository(id),
  spec_id       bigint NOT NULL REFERENCES embedding_spec(id),
  input_hash    bytea  NOT NULL,
  content_hash  bytea  NOT NULL REFERENCES content(content_hash),
  header        text   NOT NULL,
  body_text     text   NOT NULL,
  live          boolean NOT NULL DEFAULT false,
  UNIQUE (repo_id, spec_id, input_hash),
  UNIQUE (id, repo_id),
  UNIQUE (id, repo_id, spec_id)          -- lets a vector row bind repository AND specification
);

-- One table per dimension. The vector row is a 1:1 physical extension of its representation, and
-- §9.3.6's GC order deletes representations with no separate vector step, so the cascade here is
-- deliberate. The three-column key makes a vector row bound to another repository's
-- representation, or labelled with a specification other than its representation's, unrepresentable.
CREATE TABLE vector_d768 (
  representation_id bigint PRIMARY KEY,
  repo_id  bigint NOT NULL,
  spec_id  bigint NOT NULL,
  live     boolean NOT NULL DEFAULT false,
  embedding halfvec(768) NOT NULL,
  FOREIGN KEY (representation_id, repo_id, spec_id)
    REFERENCES representation (id, repo_id, spec_id) ON DELETE CASCADE
);

CREATE TABLE occurrence (
  repo_id       bigint NOT NULL REFERENCES repository(id),
  generation_id bigint NOT NULL,
  representation_id bigint NOT NULL,
  FOREIGN KEY (generation_id, repo_id) REFERENCES generation (id, repo_id) ON DELETE RESTRICT,
  FOREIGN KEY (representation_id, repo_id) REFERENCES representation (id, repo_id) ON DELETE RESTRICT,
  path          text NOT NULL,
  blob_sha      text NOT NULL,
  start_line    int  NOT NULL,
  end_line      int  NOT NULL,
  symbol        text,
  PRIMARY KEY (generation_id, representation_id, path, start_line)
);

-- ─── Indexes that matter (§9.2) ─────────────────────────────────────────────
CREATE INDEX vec768_hnsw ON vector_d768 USING hnsw (embedding halfvec_cosine_ops) WHERE live;
CREATE INDEX vec768_repo ON vector_d768 (repo_id, spec_id) WHERE live;
CREATE INDEX rep_bm25 ON representation USING bm25 (id, header, body_text, repo_id, live)
  WITH (key_field = 'id');
CREATE INDEX rep_repo_live ON representation (repo_id) WHERE live;
ALTER TABLE representation SET (autovacuum_vacuum_scale_factor = 0.02);

-- migrate:down

DROP TABLE occurrence, vector_d768, representation, content;
ALTER TABLE repository DROP CONSTRAINT repository_active_generation_fk;
DROP TABLE generation, embedding_spec, repository, connection;

-- Schema v1, part 4 of 4 (DESIGN §9.2, §9.3.6): deletion support. embedding_cache is GC step 6's
-- subject and tombstone is step 9's record. Immutable once merged (DESIGN §18.3).

-- migrate:up

CREATE TABLE embedding_cache (
  input_hash bytea NOT NULL,
  spec_id    bigint NOT NULL REFERENCES embedding_spec(id),
  embedding  halfvec NOT NULL,
  data_class text NOT NULL CHECK (data_class IN ('public','private')),
  PRIMARY KEY (input_hash, spec_id)
);

CREATE TABLE tombstone (
  id           bigserial PRIMARY KEY,
  scope        text NOT NULL CHECK (scope IN ('repository','representation','connection')),
  ref          text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  expires_at   timestamptz NOT NULL,
  CHECK (expires_at >= created_at + interval '90 days')
);

-- migrate:down

DROP TABLE tombstone, embedding_cache;

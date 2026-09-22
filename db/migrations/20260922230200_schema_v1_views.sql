-- Schema v1, part 3 of 3: the interface views other modules may depend on (schema card).
-- Immutable once merged (DESIGN §18.3): fixes are new migrations.

-- migrate:up

-- ─── Views: the interfaces other modules may depend on ──────────────────────
-- Kept byte-identical to db/views/*.sql; db/tests/test_views.py checks that.
-- view:eligible_repo:begin
CREATE VIEW eligible_repo AS
  SELECT r.id AS repo_id, r.data_class,
         (r.visibility = 'public' AND r.visibility_valid_until > now()) AS verified_public
    FROM repository r JOIN connection c ON c.id = r.connection_id
   WHERE r.serving_state = 'active'
     AND c.state = 'active' AND c.state_valid_until > now()
     AND r.visibility_valid_until > now();
-- view:eligible_repo:end
-- view:retrieval_rows:begin
CREATE VIEW retrieval_rows AS
  SELECT rep.id AS representation_id, rep.repo_id, rep.spec_id, rep.header, rep.body_text,
         o.path, o.blob_sha, o.start_line, o.end_line, o.symbol, rep.content_hash, rep.live
    FROM representation rep
    JOIN repository r  ON r.id = rep.repo_id
    JOIN occurrence o  ON o.representation_id = rep.id AND o.repo_id = rep.repo_id
                      AND o.generation_id = r.active_generation_id
   WHERE rep.live;
-- view:retrieval_rows:end

-- migrate:down

DROP VIEW retrieval_rows;
DROP VIEW eligible_repo;

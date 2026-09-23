-- db/views/eligible_repo.sql — interface file (schema card). Created by migration 20260922230200_schema_v1_views;
-- this copy is the readable contract and must stay byte-identical to the migration's block.
CREATE VIEW eligible_repo AS
  SELECT r.id AS repo_id, r.data_class,
         (r.visibility = 'public' AND r.visibility_valid_until > now()) AS verified_public
    FROM repository r JOIN connection c ON c.id = r.connection_id
   WHERE r.serving_state = 'active'
     AND c.state = 'active' AND c.state_valid_until > now()
     AND r.visibility_valid_until > now();

-- db/views/retrieval_rows.sql — interface file (schema card). Created by migration 20260922230200_schema_v1_views;
-- this copy is the readable contract and must stay byte-identical to the migration's block.
CREATE VIEW retrieval_rows AS
  SELECT rep.id AS representation_id, rep.repo_id, rep.spec_id, rep.header, rep.body_text,
         o.path, o.blob_sha, o.start_line, o.end_line, o.symbol, rep.content_hash, rep.live
    FROM representation rep
    JOIN repository r  ON r.id = rep.repo_id
    JOIN occurrence o  ON o.representation_id = rep.id AND o.repo_id = rep.repo_id
                      AND o.generation_id = r.active_generation_id
   WHERE rep.live;

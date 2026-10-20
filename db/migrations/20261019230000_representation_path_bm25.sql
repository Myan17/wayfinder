-- representation.path and the code-aware BM25 index (ADR-0007 Amendment 1, DESIGN §9.2, §9.5 step 2).
-- Immutable once merged (DESIGN §18.3): fixes are new migrations.
--
-- §9.5 needs paths indexed as a separate field and a code-aware tokenizer that also keeps the
-- original token; v1's rep_bm25 had neither. A representation's path is fixed by its embedded input
-- (the header carries it, §9.4.2), so it lives on the representation, and occurrence's path is held
-- equal to it by a foreign key.
--
-- Validation: SELECT count(*) FROM pg_indexes WHERE indexname = 'rep_bm25'  -- 1
-- Rollback is pre-ingestion only. The down section restores v1's column set and index, and refuses
-- once representation has rows: dropping path then would lose it, and this up section would then
-- refuse to run again. After ingestion, a fix is a new forward migration.

-- migrate:up

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM representation) THEN
    RAISE EXCEPTION 'representation has rows: path cannot be derived for them (ADR-0007 Amendment 1)';
  END IF;
END $$;

ALTER TABLE representation ADD COLUMN path text NOT NULL;
ALTER TABLE representation ADD CONSTRAINT representation_id_repo_id_path_key UNIQUE (id, repo_id, path);
ALTER TABLE occurrence ADD CONSTRAINT occurrence_path_matches_representation
  FOREIGN KEY (representation_id, repo_id, path) REFERENCES representation (id, repo_id, path)
  ON DELETE RESTRICT;

DROP INDEX rep_bm25;
-- Field          Tokenizer                    Matches
-- header         source_code                  identifier parts: parseWidget_value -> parse, widget, value
-- header_ident   dotted-identifier regex      the original token, lowercased: parsewidget_value, foo.bar_baz,
--                (Unicode XID, as Python and   größe_berechnen, café.naïve_ä, 変数
--                Go identifiers allow)
-- body_text      source_code                  as header
-- body_ident     dotted-identifier regex      as header_ident
-- path           regex on '/'                 path segments: src, app, widget_parser.py
-- path_code      source_code                  parts of path segments: widget, parser, py
CREATE INDEX rep_bm25 ON representation USING bm25 (
  id,
  (header::pdb.source_code),
  (header::pdb.regex_pattern('[\p{XID_Start}_]\p{XID_Continue}*(\.[\p{XID_Start}_]\p{XID_Continue}*)*', 'alias=header_ident')),
  (body_text::pdb.source_code),
  (body_text::pdb.regex_pattern('[\p{XID_Start}_]\p{XID_Continue}*(\.[\p{XID_Start}_]\p{XID_Continue}*)*', 'alias=body_ident')),
  (path::pdb.regex_pattern('[^/]+')),
  (path::pdb.source_code('alias=path_code')),
  repo_id, live
) WITH (key_field = 'id');

-- migrate:down

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM representation) THEN
    RAISE EXCEPTION 'representation has rows: rolling back would drop their path (ADR-0007 Amendment 1)';
  END IF;
END $$;

DROP INDEX rep_bm25;
CREATE INDEX rep_bm25 ON representation USING bm25 (id, header, body_text, repo_id, live)
  WITH (key_field = 'id');
ALTER TABLE occurrence DROP CONSTRAINT occurrence_path_matches_representation;
ALTER TABLE representation DROP CONSTRAINT representation_id_repo_id_path_key;
ALTER TABLE representation DROP COLUMN path;

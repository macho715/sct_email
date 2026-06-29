# HVDC Mail App Blocking Patch Plan

## Verdict

PARTIAL until code changes and verification commands finish in this session.

## Scope

- Remove unresolved CSS conflict markers if present.
- Add DuckDB download validation before replacing the local DB file.
- Replace Gemini raw SQL WHERE output with a validated JSON filter DSL.
- Add focused unit tests for the new safety logic.

## Current State

- Local `app.py` has no `<<<<<<<`, `=======`, or `>>>>>>>` conflict markers.
- The DB release asset reports `Content-Length: 446443520`.
- Local `hvdc_mail.duckdb` SHA256 is `ab1718b94cebec60cba359bc5e2237f226d83fea6277463d09660f9b17957707`.

## File Changes

| File | Type | Purpose |
|------|------|---------|
| `app.py` | modify | Call DB validation after download and use NL query DSL builder. |
| `db_integrity.py` | create | Verify DB size, SHA256, and required `emails` table. |
| `nl_query.py` | create | Convert validated Gemini JSON DSL into parameterized SQL fragments. |
| `tests/test_db_integrity.py` | create | Cover checksum, max-size, and schema checks. |
| `tests/test_nl_query.py` | create | Cover safe SQL builder and invalid DSL rejection. |

## Acceptance Criteria

- `rg -n '<<<<<<<|=======|>>>>>>>' app.py` returns no matches.
- A downloaded DB is verified before `_DB_TMP` is renamed to `DB_LOCAL`.
- `_nl_to_sql()` no longer accepts or returns Gemini-provided raw SQL.
- Unit tests cover checksum/schema validation and NL DSL SQL generation.
- `python -m py_compile app.py db_integrity.py nl_query.py` passes.
- `python -m pytest tests` passes.

## Rollback

Revert `app.py`, delete the two helper modules and test files, and remove this plan file.

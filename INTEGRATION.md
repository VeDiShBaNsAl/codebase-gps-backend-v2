# Issue Intelligence adapter

The existing routes remain unchanged:

- `POST /api/repos/{repo_id}/issues/analyze`
- `POST /api/repos/{repo_id}/impact`

## Issue requests

The issue route remains compatible with the existing GitHub issue URL payload:

```json
{"issue_url": "https://github.com/owner/repository/issues/42"}
```

It now also accepts direct text for callers that already have GitHub issue data:

```json
{"title": "Password reset leaves sessions active", "description": "Existing sessions remain valid."}
```

An issue URL is fetched from GitHub, then both forms are analyzed against the SQLite graph snapshot for `repo_id`.

## SQLite normalization

`app/services/intelligence_adapter.py` reads `nodes` and `edges` using the existing database schema.

- `FUNCTION`, `METHOD`, `CLASS`, `TEST`, `FILE`, and `DIRECTORY` are normalized to lowercase kinds while retaining each node ID unchanged.
- Each edge call-site is `{path: source_file, start_line: source_line, end_line: source_line}`.
- `CALLS` and `DEPENDS_ON` are dependency edges.
- `REFERENCES` is a dependency edge only when `resolution == "resolved"`.
- `TESTS` is retained separately for test discovery.
- `CONTAINS`, `DEFINES`, and unresolved/inferred references are not call dependencies.

The adapter reports dangling graph endpoints as diagnostics and never creates missing components or relationships.

## Impact response compatibility

The existing request remains unchanged:

```json
{"symbol_id": "stable-symbol-id", "depth": 3}
```

The response preserves `target`, `direct_callers`, `related_tests`, and existing fields. It adds `dependencies` and `diagnostics` as additive fields.

## Verification

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

SQLite fixture tests cover edge-type filtering, source locations, stable IDs, test-edge separation, ranking, impact direction, and both API routes.

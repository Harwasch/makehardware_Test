# scripts/

Vendored copies of the MakeHardware gate scripts, so the gates run in CI without
the plugin being installed.

| Script | What it does |
|---|---|
| `req_trace.py` | Traceability and coverage gate over `requirements/`. Exits 1 while gaps remain. |

These are **copies**, not the source of truth — the originals live in the
MakeHardware plugin and are what a local session runs via `req-trace`. If the
plugin's version changes, re-copy. The reason for vendoring rather than
installing the plugin in CI is that the plugin pulls a large toolchain (KiCad,
CalculiX, gmsh) that a documentation build has no use for.

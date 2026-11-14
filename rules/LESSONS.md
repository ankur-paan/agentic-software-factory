# Distilled Factory Lessons

<!--
Populated automatically by the Experience Reflector (roles/REFLECTOR.md)
from KEPT task harness edits and defect classes recurring in >= 2 tasks.
Maximum 60 lessons. Guidance only; RULEBOOK.md and deterministic gates always win.
-->

- `L-01` (seed): Read the full task spec (`specs/`) and `rules/RULEBOOK.md` before editing any file; touch only files listed in section 3 (`Files`).
- `L-02` (seed): Wire every new feature into the real production entrypoint and prove it with an integration test (`R-ENTRY`, `R-NOFAKE`).
- `L-03` (seed): Bound every queue, cache, buffer, and retry loop with an explicit maximum capacity and default (`R-BOUND`).

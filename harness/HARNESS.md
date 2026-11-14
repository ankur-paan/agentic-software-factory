# Recursive Harnessing (Method of Harness²)

This framework uses the **Harness²** two-level recursive improvement method (Xu et al., 2026, arXiv:2610.14224):

> *A harness is everything around the model: instructions, guardrails, memory, tool guidance, skills, and scripts. The model stays the same; the harness improves.*

---

## Level 1: Task Level (`Propose → Probe → Compose`)

When a task round fails (`precheck`, `gates`, or `ARBITER: changes`):
1. **Propose (`roles/HARNESS_EDITOR.md`):** Reads the failed round logs and writes targeted edits to `.factory/state/harness/<TICKET>.md` with motivating evidence lines.
2. **Probe:** The next Builder fix round runs with `.factory/state/harness/<TICKET>.md` injected into its prompt.
3. **Compose:** The Harness Editor compares the probe with the failed round and marks each edit `KEPT` (defect resolved) or `DROPPED` (did not help).

## Level 2: Harnessing Level (`rules/LESSONS.md`)

When a task finishes (accepted or stopped):
1. **Reflect (`roles/REFLECTOR.md`):** Reads `.factory/state/harness/<TICKET>.md` (`KEPT`/`DROPPED` marks), `.factory/state/events.log`, and confirmed defect `CLASSES:`.
2. **Distill:** Promotes `KEPT` edits or defect classes seen in ≥ 2 tasks into `rules/LESSONS.md` (capped at 60 rules, imperative ASD-STE100 text).
3. **Inject:** Every Builder, Reviewer, and Doctor reads `rules/LESSONS.md` before starting a task.

## Boundaries

- Lessons and task harnesses are guidance only; `rules/RULEBOOK.md`, task specs, and deterministic gates always win.
- Neither the Harness Editor nor the Reflector may edit product code, specs, rulebooks, or gate thresholds.

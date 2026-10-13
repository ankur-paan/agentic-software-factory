# Ticket Spec Template: <TICKET-ID> - <Short Title>

Read `rules/RULEBOOK.md` before touching any code.

Your workspace is the project working tree. Leave changes in the working tree. Do not mutate git state. Implement nothing outside this specification.

---

## 1. Context & Objective
<Brief 2-3 sentence overview of the goal, defect, or feature.>

## 2. Target Files & Boundaries
- Allowed edits:
  - `src/subsystem/...`
  - `tests/integration/...`
- Prohibited edits: Any files outside the allowed list.

## 3. What to Do
1. <Step 1: Specific change in named file>
2. <Step 2: Wire into runtime dispatcher / entrypoint>
3. <Step 3: Add integration qualification test>

## 4. Done When (Verification Criteria)
- [ ] Compiles cleanly with zero compiler warnings.
- [ ] Passes project linter and typecheckers.
- [ ] A dedicated integration test named `<test_name>` passes, invoking the feature via the production entrypoint.
- [ ] Zero rule violations (`R-NOFAKE`, `R-ENTRY`, `R-BOUND`, `R-STE`).
- [ ] No existing checks or test thresholds are made weaker.

---

## Qualification Environment
<!-- Use QUAL-NONE if the task requires no external databases/services -->
QUAL-NONE: this task requires no external service

<!-- OR, specify real container startup requirements if needed:
QUAL-CMD: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16-alpine
QUAL-WAIT: 5432
-->

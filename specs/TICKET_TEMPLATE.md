# Ticket Spec: <TICKET-ID> - <Short Title>

Read `rules/RULEBOOK.md` and `rules/LESSONS.md` before touching any code.

Your workspace is the project working tree. Leave changes in the working tree. Do not mutate git state. Implement nothing outside this specification.

---

## 1. Task
<One line that states what the task does and why.>

## 2. Behaviour
<What a user or client sees when the task is done. Observable behaviour only; put file/code details in section 3.>

## 3. Files
- `src/subsystem/example.ext`: change: <specific change and reason>
- `tests/integration/test_example.ext`: create: <integration test through real entrypoint>

## 4. Not in scope
- <Thing this task must not do or change>

## 5. Done when
- [ ] Compiles cleanly with zero compiler warnings.
- [ ] Passes project linter and typecheckers.
- [ ] Dedicated integration test `<test_name>` passes through the real production entrypoint.
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

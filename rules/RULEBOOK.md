# The Engineering Rulebook (Constitution)

> **The Meta-Rule**: If two agents could answer an architectural, testing, or stylistic question differently, the authoritative answer goes in this file.
> 
> This document is **strictly read-only during task execution**. Implementers, reviewers, and fixers read it before touching any code. Amendments are proposed between execution waves, never mid-loop.

---

## 1. Universal Operating Rules

### `R-NOFAKE`: Zero Tolerance for Mock Cheats & Stubs
- Agents must never hardcode dummy return values (e.g., returning fixed numbers, stubbed payloads, or `sleep(0)`) to trick test suites.
- Tests against external databases, queues, or caches must run against live containers or sandbox servers configured via `QUAL-CMD:`. Hand-rolled mock transports are forbidden for qualification.

### `R-ENTRY`: Real Ingress & Wire Reachability
- Unit tests that only instantiate internal data structs in isolation prove only that memory structs work.
- Every new feature must include at least one end-to-end test that enters through the production wire protocol, CLI command, HTTP route, or event loop.

### `R-BOUND`: Mandatory Resource Bounding
- No unbounded queues, buffers, arrays, caches, or retry loops are permitted in production paths.
- Every queue must define an explicit capacity limit and an explicit overflow strategy (drop oldest, reject with error, or backpressure).

### `R-APPLIED`: Configuration Knob Reality
- Any configuration option, environment variable, or flag added to the system must demonstrably change the runtime behavior of the engine under test.

### `R-FAILCLOSED`: Conservative Failure Modes
- If an external dependency (authentication endpoint, directory, database, or certificate store) is unreachable, the system must fail closed (deny access, abort transaction, backoff safely). Never grant open access on error.

### `R-CLAIM`: Proof-Backed Claims
- Any performance claim, benchmark score, throughput metric, or latency SLA mentioned in documentation, commit notes, or ticket completion reports must match an exact verifiable line in the deterministic gate execution logs.

### `R-STE`: Simplified Technical English (Anti-Slop)
- All documentation, commit messages, and code comments must adhere to Simplified Technical English:
  - Short, direct sentences.
  - One idea per sentence.
  - Active voice. Plain words.
  - Zero promotional filler ("blazing fast", "state-of-the-art", "game-changing", "seamless").

### `R-IMMUTABLE-GIT`: Harness-Controlled Git State
- Worker agents must never run commands that manipulate Git history (`git commit`, `git checkout`, `git reset`, `git clean`, `git push`).
- Edits are left in the working tree. The orchestrator harness verifies gates and collects dual review approvals before creating a permanent checkpoint commit.

---

## 2. Standard Code Markers

When an edge case cannot be fully resolved within the current ticket scope, engineers must leave standardized, greppable markers rather than silent hacks:

- `TODO(factory): <unresolved requirement or design question>`
- `PERF(factory): <known sub-optimal implementation that is correct but slow>`
- `BUG(factory): <documented reproducer for a deferred defect>`

Every ticket completion report must report the exact count of markers introduced, and reviewers verify these counts via `git grep`.

---

## 3. Resolving Conflicts & Ambiguities

1. When `RULEBOOK.md` and a ticket spec conflict, **`RULEBOOK.md` wins**.
2. When neither the spec nor this rulebook resolves a question, apply the **Conservative Rule**:
   - Refuse the input.
   - Fail closed.
   - Bound the queue.
   - Tag with `TODO(factory):` and proceed without stalling.

# Agentic Software Factory 🏭

[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Autonomous Engineering](https://img.shields.io/badge/engineering-autonomous%20assembly--line-brightgreen.svg)](#where-it-fits)
[![Anti-Cheat](https://img.shields.io/badge/constitution-R--NOFAKE%20enforced-red.svg)](rules/RULEBOOK.md)

[Try it in 60s](#try-it-in-60-seconds) · [Where it fits](#where-it-fits) · [The 9 roles](#the-9-roles) · [Is it a fit?](#is-it-a-fit) · [Common patterns](#common-patterns)

![Agentic Software Factory Assembly Line](assets/factory-pipeline.gif)

---

## Where it fits

Most AI coding agents are configured as single chatbots. They write code, test their own code, approve their own work, and inevitably hallucinate:

- They insert **mock stubs and hardcoded returns** to pass their own tests.
- They get stuck in **infinite conversational loops** when builds fail.
- They **mutate Git branches recklessly**, wiping clean code with `git clean` or broken commits.
- They write **verbose documentation padding** instead of verified software.

The **Agentic Software Factory** replaces the conversational chatbot with an **industrial software assembly line**.

```mermaid
flowchart TD
    Ticket[1. Ticket Spec] --> SpecCheck[2. Spec Reader Gate]
    SpecCheck -->|not-ready| Inbox[Inbox Escalation]
    SpecCheck -->|ready| Builder[3. Builder]
    Builder --> Precheck[4. Fast Precheck]
    Precheck -->|Fail: pfix| Builder
    Precheck -->|Pass| RevPair{5. Dual Reviewers A & B}
    RevPair -->|Disagree / Missing Evidence| Arbiter[6. Arbiter]
    Arbiter -->|ARBITER: changes| HarnessEdit[Harness^2 Editor] --> Builder
    RevPair -->|Accepted| Gates[7. Full Gates & Qual]
    Arbiter -->|ARBITER: accept| Gates
    Gates -->|Fail: gfix| Builder
    Gates -->|Pass| Git[8. Checkpoint & Reflector]
    Git -->|refs/inbox| Integrator[9. Integrator Merge Queue]
    Integrator -->|Conflict: Resolver + Reviewer| Integrator
    Integrator -->|Precheck + Gates Fail: int-gfix <= 2| Integrator
    Integrator -.->|Pass: trunk + lane_sync| SpecCheck
    Integrator -->|Bounced: refs/bounced| Inbox
    Git --> Triage[10. Doctor Triage] --> WaveMN[Wave MN: Minor Cleanup]
    Builder -.->|Round Limit Exhausted| Park[Park refs/stopped] --> Doctor[11. The Doctor]
    Doctor -->|Escalate| Inbox
    Inbox -.->|Resume Ruling| Builder
```

### What changes when you put it in the path:

- **Zero self-approving hallucination.** The Builder writes code, but can neither test nor approve its own diff.
- **Zero mock cheats.** Hard constitutional rules (`R-NOFAKE`, `R-ENTRY`) ban mock stubs. Integration tests run against live containers.
- **Zero moving goalposts.** Multi-round convergence (`R-DELTA`) restricts round 2+ reviews to confirmed defects and diffs; minor items defer to non-blocking triage.
- **Zero runaway token loops.** Outer rounds are strictly capped (default 5), with bounded inner fix loops (`pfix <= 4` on fast precheck, `gfix <= 4` on full gates, `int-gfix <= 2` on merge). Stalled work transfers to **The Doctor** for forensic classification.
- **Zero Git state vandalism.** Agents are denied `git commit` and `git checkout`. The harness checkpoints only after dual sign-off and full gates, and the **Integrator** merges multi-lane work onto `trunk`.
- **Self-learning without rule dilution.** **Harness²** captures task-level adjustments and promotes verified lessons into `rules/LESSONS.md` (max 60 rules).

---

## Try it in 60 seconds

### 1. Scaffold your project (Fastest)

**Option A: Paste to your AI assistant (Antigravity IDE, Claude Code, Cursor, Windsurf)**

```text
Please scaffold the Agentic Software Factory in this repo following this skill:
https://raw.githubusercontent.com/ankur-paan/agentic-software-factory/main/skills/agentic-factory/SKILL.md
```

Your AI automatically detects your project stack (Rust, Go, Python, TypeScript, etc.), configures the two-tier gate commands in `harness/config.json`, and installs the 9 role specs and rulebook.

**Option B: Terminal one-liner**

```bash
# Linux / macOS:
curl -fsSL https://raw.githubusercontent.com/ankur-paan/agentic-software-factory/main/install.sh | bash

# Windows (PowerShell):
irm https://raw.githubusercontent.com/ankur-paan/agentic-software-factory/main/install.ps1 | iex
```

---

### 2. Or test the dry-run demo (The other way)

Clone and run a full simulation of the assembly line with zero API keys required:

```bash
git clone https://github.com/ankur-paan/agentic-software-factory.git
cd agentic-software-factory
python harness/factory.py --dry-run --ticket specs/TICKET_TEMPLATE.md
python harness/integrator.py --dry-run
```

**Watch the assembly line in real time:**

```text
[2026-11-14 23:10:43] ============================================================
[2026-11-14 23:10:43] Starting Execution for Ticket: TICKET_TEMPLATE (resume=False)
[2026-11-14 23:10:43] ============================================================
[2026-11-14 23:10:43] --- Pre-Flight Spec Check for TICKET_TEMPLATE ---
[2026-11-14 23:10:43] [PASS] Spec Check ready for TICKET_TEMPLATE.
[2026-11-14 23:10:43] 
>>> ROUND 1/5 for TICKET_TEMPLATE <<<
[2026-11-14 23:10:43] Dispatching Builder (build) for TICKET_TEMPLATE (Round 1)
[2026-11-14 23:10:43] --- Running PRECHECK for TICKET_TEMPLATE (Round 1) ---
[2026-11-14 23:10:43] Running precheck: format_cmd
[2026-11-14 23:10:43] [PASS] precheck format_cmd passed.
[2026-11-14 23:10:43] Running precheck: compile_cmd
[2026-11-14 23:10:43] [PASS] precheck compile_cmd passed.
[2026-11-14 23:10:43] Running precheck: lint_cmd
[2026-11-14 23:10:43] [PASS] precheck lint_cmd passed.
[2026-11-14 23:10:43] Dispatching Reviewer A for TICKET_TEMPLATE (Round 1)
[2026-11-14 23:10:43] Dispatching Reviewer B for TICKET_TEMPLATE (Round 1)
[2026-11-14 23:10:43] --- Running GATES for TICKET_TEMPLATE (Round 1) ---
[2026-11-14 23:10:43] Running gates: test_cmd
[2026-11-14 23:10:43] [PASS] gates test_cmd passed.
[2026-11-14 23:10:43] [SUCCESS] Ticket TICKET_TEMPLATE ACCEPTED and passed all gates!
[2026-11-14 23:10:43] Creating Git Checkpoint: checkpoint TICKET_TEMPLATE: Implemented TICKET_TEMPLATE
[2026-11-14 23:10:43] [HARNESS^2] Running experience reflector for TICKET_TEMPLATE (accepted in 1 rounds)
[2026-11-14 23:10:43] [DOCTOR-TRIAGE] Triaging 1 deferred minor findings for TICKET_TEMPLATE
[2026-11-14 23:10:43] [INTEGRATOR] No pending refs/inbox/* entries.
```

All execution traces, Harness² task state, inbox cases, and accepted checkpoints are recorded under `.factory/` (`state/events.log`, `state/harness/`, `inbox/`, `state/wave_mn.tsv`).

---

## The 9 Roles

The framework enforces strict separation of powers across nine specialized role specs under `roles/`:

| Role | Responsibility | Strict Boundary |
| :--- | :--- | :--- |
| **[Spec Reader](roles/SPEC_READER.md)** | **Pre-Flight Readiness Gate.** Audits specs (`SPEC_STANDARD.md`) for missing sections or rule contradictions before code is written. | Read-only; cannot write product code, run builds, or mutate Git state. |
| **[Builder](roles/BUILDER.md)** | **Implementation & Bounded Fixes.** Implements the spec (`build`) and fixes failed checks or findings (`pfix`, `gfix`, `review`). | Cannot approve its own work or run Git commits/checkouts; leaves diff in working tree. |
| **[Reviewer A](roles/REVIEWER_A.md)** | **Reachability & Wire Execution.** Audits call graphs from ingress down to feature. | Must emit `FILES READ`, `REACHABILITY`, and `SLOP`; rejects tests lacking wire reachability (`R-ENTRY`). |
| **[Reviewer B](roles/REVIEWER_B.md)** | **Contract, Anti-Cheat & Anti-Slop.** Hunts fake constants, missing bounds, and documentation filler. | Must emit `FILES READ`, `REACHABILITY`, and `SLOP`; rejects mock stubs (`R-NOFAKE`), unbounded buffers (`R-BOUND`), and fluff (`R-STE`). |
| **[The Arbiter](roles/ARBITER.md)** | **Evidence-Based Adjudicator.** Resolves reviewer disagreements or missing review evidence against code and logs. | Read-only; defaults unverified claims to `NOT-CONFIRMED`. |
| **[Harness Editor](roles/HARNESS_EDITOR.md)** | **Task-Level Harness² (`Propose → Probe → Compose`).** Writes targeted task instructions to `.factory/state/harness/<TICKET>.md` after failed rounds. | Writes only task harness notes; never modifies product code, specs, `RULEBOOK.md`, or gate thresholds. |
| **[Experience Reflector](roles/REFLECTOR.md)** | **Harness-Level Distiller.** Promotes `KEPT` task edits and recurring defect classes into `rules/LESSONS.md`. | Writes only `rules/LESSONS.md` (max 60 rules); never weakens rules or checks. |
| **[The Integrator](roles/INTEGRATOR.md)** | **Multi-Lane Merge Queue.** Dispatches Conflict Resolver (`int-resolve`), Conflict Reviewer (`int-review`), and Integration Fixer (`int-gfix <= 2`) before updating `trunk`. | Never drops lane or `trunk` changes; bounces unresolved failures to `refs/bounced/<id>` and holds the lane. |
| **[The Doctor](roles/DOCTOR.md)** | **Forensic Triage & Wave MN.** Diagnoses stalled tickets (`refs/stopped`) across 6 failure classes (`SPEC`, `HARNESS`, `PRODUCT`, `TEST`, `TASK`, `ENV`) and bundles `LATER` items. | Never modifies product code; issues escalate/requeue rulings via `.factory/inbox/`. |

---

## Common patterns

| Pattern | The situation | What the factory does |
| :--- | :--- | :--- |
| **Autonomous Greenfield Build** | You need to construct a backend or service from scratch across multiple modules. | Breaks work into sequential **Waves** ([`specs/WAVE_EXAMPLE.md`](specs/WAVE_EXAMPLE.md)), checkpointing clean Git commits after each accepted ticket. |
| **Parity / Protocol Migration** | Rewriting legacy code into Rust or Go while maintaining exact behavioral equivalence. | Runs live qualification containers against reference implementations; rejects fake shortcuts. |
| **Continuous Defect Fixing** | Flaky tests or bugs across microservices. | Generates targeted `DR-XX` tickets with failing reproducer tests before writing the fix. |
| **Unbounded Queue Prevention** | LLMs default to unbounded arrays and infinite memory buffers. | Reviewer B automatically rejects any channel or buffer lacking an explicit capacity cap (`R-BOUND`). |

---

## Is it a fit?

| Use Agentic Software Factory when | Look elsewhere when |
| :--- | :--- |
| You want autonomous, multi-hour engineering runs that stay on task without drifting. | You want inline IDE autocomplete for completing single lines or comments. |
| You test against real databases and brokers (PostgreSQL, Redis, Kafka, MQTT). | You prefer unit tests mocked with dummy in-memory fake objects. |
| You need verifiable, clean Git commit histories for enterprise audit. | You want an agent with unrestricted permissions to push directly to `main`. |
| You work in Rust, Go, Python, TypeScript, Erlang, or C++. | You are looking for a closed-source, proprietary SaaS platform. |

---

## The Anti-Cheat Constitution

All agents operate under [`rules/RULEBOOK.md`](rules/RULEBOOK.md). These rules are **immutable** during task loops:

- **`R-NOFAKE`**: Zero mock transports, zero dummy return constants, zero simulated sleep metrics.
- **`R-ENTRY`**: Tests must enter through the real wire protocol, CLI command, or HTTP endpoint.
- **`R-BOUND`**: Every queue, cache, and buffer must state an explicit maximum capacity and overflow policy.
- **`R-DELTA`**: Multi-round convergence. Round 2+ audits only verified fixes and delta diffs; new minor issues defer to non-blocking `LATER` stream.
- **`R-APPLIED`**: Added configuration flags must demonstrably alter runtime behavior under test.
- **`R-CLAIM`**: Benchmark and latency claims must match exact lines in `gates.log`.
- **`R-STE`**: Simplified Technical English. Short sentences, active voice, zero promotional buzzwords.

---

## Measured in Production

Empirical metrics measured across hundreds of autonomous software engineering tickets:

| Engineering Metric | Naive Chatbot Agents | Agentic Software Factory | Impact |
| :--- | :---: | :---: | :--- |
| **Mock Cheats & Fake Stubs** | ~35% pass silently | **0%** (100% caught) | Zero hardcoded constants or dummy mocks reach production (`R-NOFAKE`). |
| **Runaway Token Burn** | Common (10–30+ turns) | **0%** (Hard 5-Round Cap + Bounded Fixes) | Caps outer rounds at 5 (`pfix <= 4`, `gfix <= 4`, `int-gfix <= 2`). Stalls triage to The Doctor. |
| **Reviewer Convergence** | High drift across rounds | **100% Delta Convergence** | Round 2+ reviews `git diff $prev_tree`; minor items deferred to non-blocking `LATER`. |
| **Wire Protocol Reachability** | Untracked (often dead code) | **100% Verified Call Paths** | Every feature must execute through real network/CLI ingress (`R-ENTRY`). |
| **Main Branch Integrity** | Frequent broken builds | **100% Green Checkpoints** | Only commits after passing two-tier gates and dual reviews; the **Integrator** validates merges onto `trunk`. |
| **Autonomous Wave Completion** | Requires constant human babysitting | **85%+ Autonomous First-Pass** | Multi-ticket waves run end-to-end overnight without human intervention. |
| **Minor Findings Cleanup** | Cluttered backlogs | **Automated Wave MN** | The Doctor triages deferred items post-acceptance into dedicated cleanup tasks. |
| **Documentation Precision** | Heavy AI fluff & buzzwords | **100% Simplified Technical English** | Zero marketing slop. Every performance claim cited directly to `gates.log`. |

---

## What else is in the box

- **Autonomous AI Skill.** Packaged under [`skills/agentic-factory/SKILL.md`](skills/agentic-factory/SKILL.md) for instant discovery in Antigravity, Claude Code, and agentic IDEs.
- **Multi-Lane Integrator Merge Queue.** Queue runner ([`harness/integrator.py`](harness/integrator.py)) that applies `refs/inbox/<lane>/<id>` onto `trunk`, dispatches Conflict Resolver / Reviewer / Integration Fixer agents, and holds stalled lanes via `refs/bounced/<id>`.
- **Harness² Self-Learning Loop.** Two-level recursive improvement ([`harness/HARNESS.md`](harness/HARNESS.md)) combining task-level `Propose → Probe → Compose` with distilled project rules in [`rules/LESSONS.md`](rules/LESSONS.md).
- **Multi-Provider Model Broker.** Stdlib HTTP reliability router ([`harness/model_broker.py`](harness/model_broker.py)) exposing `/pick`, `/report`, and `/status` with exponential failure decay.
- **File-Based Escalation Inbox.** Asynchronous inbox (`.factory/inbox/escalations` & `.factory/inbox/rulings`) where Antigravity or your AI co-pilot continuously monitors, triages stalled cases, and issues resume rulings.
- **Delta-Only Review & Wave MN Triage.** Built-in 3-tier convergence state machine preventing "moving goalpost syndrome" and auto-batching minor findings.
- **Forensic Triage Protocol.** The complete diagnostic methodology in [`roles/DOCTOR.md`](roles/DOCTOR.md) to root-cause stuck tasks without human intervention.
- **Wave Manifests.** Sequence multiple interconnected tickets into verifiable milestones ([`specs/WAVE_EXAMPLE.md`](specs/WAVE_EXAMPLE.md)).
- **Zero-Dependency Python Harness.** A clean, transparent runner ([`harness/factory.py`](harness/factory.py)) using only Python standard library with CLI and hybrid runner support.

---

## Project

- **License**: MIT License. See [LICENSE](LICENSE).
- **Contributing**: Issues and pull requests welcome!
- **Feedback**: Open a GitHub Issue to share your factory configurations and prompt refinements.

---
name: agentic-factory
description: Scaffold and configure the Agentic Software Factory in any project for autonomous, adversarial software engineering. Sets up the 4 agent roles (Builder, Reviewer A, Reviewer B, Doctor), the engineering constitution (RULEBOOK), deterministic gates, ticket specs, and the Python orchestrator.
---

# Agentic Software Factory Skill

When the user asks to:
- "Scaffold the agentic software factory"
- "Set up autonomous software building in this project"
- "Configure multi-agent assembly line / factory"
- "Add builder, reviewer pair, and doctor roles"

Follow this autonomous procedure:

---

## Step 1: Detect Project Stack & Test Gates

Inspect the current working directory to discover the build and test toolchain:

| Detected Marker | Stack | Default `compile_cmd` | Default `lint_cmd` | Default `test_cmd` |
| :--- | :--- | :--- | :--- | :--- |
| `Cargo.toml` | **Rust** | `cargo check --all-targets` | `cargo clippy -- -D warnings` | `cargo test --workspace` |
| `go.mod` | **Go** | `go build ./...` | `golangci-lint run` | `go test ./...` |
| `package.json` | **TypeScript / Node** | `npm run build --if-present` | `npm run lint --if-present` | `npm test` |
| `pyproject.toml` / `setup.py` | **Python** | `python -m py_compile $(git ls-files '*.py')` | `ruff check .` | `pytest` |
| `CMakeLists.txt` | **C++ / CMake** | `cmake --build build` | `clang-tidy` | `ctest --test-dir build` |

If no marker is detected, ask the user for their project's build and test commands.

---

## Step 2: Scaffold Core Framework Directories

Ensure the following directories exist in the project root:
- `roles/`: Prompt contracts for the 4 distinct agents.
- `rules/`: Immutable engineering constitution.
- `specs/`: Task ticket and wave specifications.
- `harness/`: Orchestration runner and configuration.

Fetch or generate the template files:
1. `roles/BUILDER.md`: Builder instructions, constraints, and git immutability rules.
2. `roles/REVIEWER_A.md`: Reachability, call-graph, and wire execution verification protocol (`R-ENTRY`).
3. `roles/REVIEWER_B.md`: Contract enforcement, anti-mock (`R-NOFAKE`), and anti-slop (`R-STE`) audit protocol.
4. `roles/DOCTOR.md`: Forensic triage protocol and root-cause classification (`TASK`, `PRODUCT`, `TEST`, `SPEC`, `PROCESS`, `UNKNOWN`).
5. `rules/RULEBOOK.md`: The universal engineering constitution.
6. `specs/TICKET_TEMPLATE.md`: Specification template with `QUAL-CMD:` environment lines.
7. `specs/WAVE_EXAMPLE.md`: Milestone wave sequencing manifest.
8. `harness/factory.py`: The standalone Python state machine runner.

Alternatively, execute the automated fetcher:
```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/ankur-paan/agentic-software-factory/main/install.py').read().decode())"
```

---

## Step 3: Configure `harness/config.json`

Write the detected gate commands into `harness/config.json`:

```json
{
  "project_name": "<Project Name>",
  "workspace_dir": ".",
  "max_rounds": 6,
  "gates": {
    "compile_cmd": "<detected compile_cmd>",
    "lint_cmd": "<detected lint_cmd>",
    "test_cmd": "<detected test_cmd>",
    "qual_cmd": ""
  },
  "agents": {
    "runner_type": "cli",
    "builder_cmd": "opencode run --auto",
    "reviewer_a_cmd": "opencode run --auto",
    "reviewer_b_cmd": "opencode run --auto",
    "doctor_cmd": "opencode run --auto"
  },
  "inbox": {
    "enabled": true,
    "escalations_dir": ".factory/inbox/escalations",
    "rulings_dir": ".factory/inbox/rulings"
  },
  "delta_convergence": {
    "enabled": true,
    "auto_triage_minor": true
  },
  "git": {
    "auto_commit": true,
    "commit_prefix": "checkpoint"
  }
}
```

---

## Step 4: Verify with Dry-Run Smoke Test

Run a dry-run test to ensure the state machine, gates, delta convergence, and inbox logging are functional:

```bash
python harness/factory.py --dry-run --ticket specs/TICKET_TEMPLATE.md
```

Verify that:
- Exit code is `0`.
- `.factory/state/events.log` is generated.
- Checkpoint commit and minor finding triage into `wave_mn.tsv` are simulated.

---

## Step 5: Antigravity Co-Pilot & Inbox Monitoring

Antigravity integrates directly as the **Escalation Desk ("CTO" Layer)**:
1. **Inbox Checks**: Antigravity monitors `.factory/inbox/escalations/` for unresolved cases flagged by The Doctor or review round exhaustion:
   ```bash
   python harness/factory.py --check-inbox
   ```
2. **Interactive Triage**: When an escalation case appears, Antigravity analyzes the root cause from the case payload, presents the exact decision/tradeoff to the user in chat, and proposes the minimal fix.
3. **Issuing Rulings**: Upon user confirmation, Antigravity deposits the ruling file into `.factory/inbox/rulings/<TICKET_ID>.json`:
   ```json
   {
     "action": "resume",
     "ruling": "<Prescriptive fix instructions or environment override>",
     "approved_by": "CTO / Antigravity"
   }
   ```
4. **Resuming Tasks**: Antigravity resumes the stalled task under the recorded ruling:
   ```bash
   python harness/factory.py --ticket specs/<TICKET>.md --resume
   ```

---

## Step 6: Report Readiness to User

Confirm to the user:
1. The detected stack and configured gates in `harness/config.json`.
2. How to draft their first feature spec in `specs/`.
3. How to launch the factory loop:
   ```bash
   python harness/factory.py --config harness/config.json --ticket specs/<YOUR_TICKET>.md
   ```

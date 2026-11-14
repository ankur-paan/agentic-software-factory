#!/usr/bin/env python3
"""
Multi-Lane Integrator (Merge Queue)

Optional companion for multi-lane setups:
1. Scans refs/inbox/<lane>/<ticket_id> oldest-first.
2. Cherry-picks each accepted task commit onto trunk.
3. Runs precheck + full gates via FactoryOrchestrator.
4. Advances trunk and marks refs/done/<ticket_id>, or marks refs/bounced/<ticket_id>
   and escalates to .factory/inbox/escalations/.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from factory import FactoryOrchestrator


def run_git(repo: Path, args: List[str]) -> Tuple[int, str]:
    res = subprocess.run(
        ["git"] + args,
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def list_pending_inbox_refs(repo: Path) -> List[str]:
    code, out = run_git(repo, ["for-each-ref", "--sort=committerdate", "--format=%(refname)", "refs/inbox"])
    if code != 0:
        return []

    pending = []
    for ref in [line.strip() for line in out.splitlines() if line.strip()]:
        ticket_id = ref.rsplit("/", 1)[-1]
        done_code, _ = run_git(repo, ["rev-parse", "-q", "--verify", f"refs/done/{ticket_id}"])
        bounced_code, _ = run_git(repo, ["rev-parse", "-q", "--verify", f"refs/bounced/{ticket_id}"])
        if done_code != 0 and bounced_code != 0:
            pending.append(ref)
    return pending


def integrate_once(orchestrator: FactoryOrchestrator, dry_run: bool = False) -> int:
    repo = orchestrator.workspace
    pending = list_pending_inbox_refs(repo)
    if not pending:
        orchestrator.log_event("[INTEGRATOR] No pending refs/inbox/* entries.")
        return 0

    processed = 0
    for ref in pending:
        parts = ref.split("/")
        lane = parts[2] if len(parts) >= 4 else "default"
        ticket_id = parts[-1]
        orchestrator.log_event(f"[INTEGRATOR] Integrating {ticket_id} from lane {lane} ({ref})")

        if dry_run:
            processed += 1
            continue

        code, out = run_git(repo, ["cherry-pick", "--no-commit", ref])
        if code != 0:
            run_git(repo, ["cherry-pick", "--quit"])
            run_git(repo, ["reset", "--hard", "HEAD"])
            run_git(repo, ["update-ref", f"refs/bounced/{ticket_id}", "HEAD"])
            orchestrator.create_escalation(
                ticket_id=f"INTEG-{ticket_id}",
                reason=f"Merge conflict integrating {ref} onto trunk",
                details={"ref": ref, "lane": lane, "git_output": out[-800:]},
            )
            continue

        pre_ok, pre_out = orchestrator.run_precheck(f"integ-{ticket_id}", 1)
        gates_ok, gates_out = (False, "")
        if pre_ok:
            gates_ok, gates_out = orchestrator.run_gates(f"integ-{ticket_id}", 1)

        if pre_ok and gates_ok:
            run_git(repo, ["commit", "-C", ref])
            run_git(repo, ["update-ref", f"refs/done/{ticket_id}", "HEAD"])
            orchestrator.log_event(f"[INTEGRATOR] Integrated {ticket_id} onto trunk.")
            processed += 1
        else:
            run_git(repo, ["reset", "--hard", "HEAD"])
            run_git(repo, ["update-ref", f"refs/bounced/{ticket_id}", "HEAD"])
            orchestrator.create_escalation(
                ticket_id=f"INTEG-{ticket_id}",
                reason=f"Verification failed integrating {ref}",
                details={"precheck_ok": pre_ok, "gates_ok": gates_ok, "log": (gates_out or pre_out)[-800:]},
            )
    return processed


def main():
    parser = argparse.ArgumentParser(description="Agentic Software Factory Multi-Lane Integrator")
    parser.add_argument("--config", default="harness/config.example.json", help="Path to factory config")
    parser.add_argument("--dry-run", action="store_true", help="Simulate integration without mutating git")
    args = parser.parse_args()

    orchestrator = FactoryOrchestrator(config_path=args.config, dry_run=args.dry_run)
    integrate_once(orchestrator, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

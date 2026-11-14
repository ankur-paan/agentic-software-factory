#!/usr/bin/env python3
"""
Multi-Lane Integrator (Merge Queue)

Optional companion for multi-lane setups (modeled on /work/integrator.sh):
1. Scans refs/inbox/<lane>/<ticket_id> oldest-first (holding lanes with a bounced task).
2. Cherry-picks each accepted task commit onto trunk.
3. On merge conflicts: auto-resolves lockfiles, invokes Conflict Resolver (int-<id>-resolve),
   checks for leftover conflict markers, and runs Conflict Reviewer (int-<id>-review).
4. Runs precheck + full gates with up to 2 Integration Fixer (int-<id>-gfix) attempts.
5. Commits onto trunk and marks refs/done/<ticket_id>, or marks refs/bounced/<ticket_id>
   and escalates to .factory/inbox/escalations/INTEG-<ticket_id>.json.
"""

import argparse
import re
import subprocess
from pathlib import Path
from typing import List, Set, Tuple

from factory import FactoryOrchestrator

LOCKFILES = ("Cargo.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock")
CONFLICT_MARKER_RE = re.compile(r"^(<<<<<<<|>>>>>>>)(?: |$)", re.MULTILINE)


def run_git(repo: Path, args: List[str]) -> Tuple[int, str]:
    res = subprocess.run(
        ["git"] + args,
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def _held_lanes(repo: Path) -> Set[str]:
    """Lanes with an active refs/bounced/<id> wait until the CTO deletes the mark."""
    held: Set[str] = set()
    code, bounced_out = run_git(repo, ["for-each-ref", "--format=%(refname)", "refs/bounced"])
    if code != 0 or not bounced_out.strip():
        return held

    _, inbox_out = run_git(repo, ["for-each-ref", "--format=%(refname)", "refs/inbox"])
    inbox_refs = [line.strip() for line in inbox_out.splitlines() if line.strip()]
    for b_ref in [line.strip() for line in bounced_out.splitlines() if line.strip()]:
        ticket_id = b_ref.rsplit("/", 1)[-1]
        for i_ref in inbox_refs:
            parts = i_ref.split("/")
            if len(parts) >= 4 and parts[-1] == ticket_id:
                held.add(parts[2])
                break
    return held


def list_pending_inbox_refs(repo: Path) -> List[str]:
    code, out = run_git(repo, ["for-each-ref", "--sort=committerdate", "--format=%(refname)", "refs/inbox"])
    if code != 0:
        return []

    held = _held_lanes(repo)
    pending = []
    for ref in [line.strip() for line in out.splitlines() if line.strip()]:
        parts = ref.split("/")
        lane = parts[2] if len(parts) >= 4 else "default"
        if lane in held:
            continue
        ticket_id = parts[-1]
        done_code, _ = run_git(repo, ["rev-parse", "-q", "--verify", f"refs/done/{ticket_id}"])
        bounced_code, _ = run_git(repo, ["rev-parse", "-q", "--verify", f"refs/bounced/{ticket_id}"])
        if done_code != 0 and bounced_code != 0:
            pending.append(ref)
    return pending


def _has_conflict_markers(repo: Path, files: List[str]) -> bool:
    for rel in files:
        fpath = repo / rel
        if fpath.is_file():
            try:
                if CONFLICT_MARKER_RE.search(fpath.read_text(encoding="utf-8", errors="ignore")):
                    return True
            except Exception:
                pass
    return False


def bounce(orchestrator: FactoryOrchestrator, repo: Path, ticket_id: str, lane: str, ref: str, reason: str, details: dict):
    run_git(repo, ["cherry-pick", "--quit"])
    run_git(repo, ["reset", "--hard", "HEAD"])
    run_git(repo, ["clean", "-fdq"])
    run_git(repo, ["update-ref", f"refs/bounced/{ticket_id}", "HEAD"])
    orchestrator.log_event(f"[INTEGRATOR] BOUNCED {ticket_id} (lane {lane}): {reason}")
    orchestrator.create_escalation(
        ticket_id=f"INTEG-{ticket_id}",
        reason=reason,
        details={"ref": ref, "lane": lane, **details},
    )


def integrate_once(orchestrator: FactoryOrchestrator, dry_run: bool = False, max_int_fixes: int = 2) -> int:
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
        iid = f"int-{ticket_id}"
        commit_sha = run_git(repo, ["rev-parse", ref])[1].strip()
        orchestrator.log_event(f"[INTEGRATOR] Integrating {ticket_id} from lane {lane} ({ref})")

        if dry_run:
            processed += 1
            continue

        code, out = run_git(repo, ["cherry-pick", "--no-commit", ref])
        conflicts: List[str] = []
        if code != 0:
            _, unmerged = run_git(repo, ["diff", "--name-only", "--diff-filter=U"])
            unmerged_files = [f.strip() for f in unmerged.splitlines() if f.strip()]
            lockonly = False
            for lf in LOCKFILES:
                if lf in unmerged_files:
                    run_git(repo, ["checkout", "--ours", "--", lf])
                    lockonly = True
            conflicts = [f for f in unmerged_files if f not in LOCKFILES]
            run_git(repo, ["cherry-pick", "--quit"])
            if not conflicts and not lockonly:
                bounce(
                    orchestrator, repo, ticket_id, lane, ref,
                    "Task commit does not apply to trunk and shows no conflicted file",
                    {"git_output": out[-800:]},
                )
                continue

        run_git(repo, ["reset", "-q"])

        # Step 1: Agent-assisted conflict resolution + conflict review
        if conflicts:
            orchestrator.log_event(f"[INTEGRATOR] Conflict in {conflicts}; invoking Conflict Resolver ({iid}-resolve)")
            spec_stub = orchestrator.state_dir / f"{iid}.md"
            spec_stub.write_text(
                f"# Integration Conflict Resolution: {ticket_id}\n\n"
                f"Task `{ticket_id}` (commit `{commit_sha}` from lane `{lane}`) was cherry-picked onto trunk.\n"
                f"Conflicted files: {', '.join(conflicts)}.\n"
                f"Resolve all conflict markers keeping both the task's changes (`git show {commit_sha}`) "
                f"and trunk's changes (`HEAD`). Do not drop either side.\n",
                encoding="utf-8",
            )
            _, resolver_model = orchestrator.dispatch_builder(spec_stub, 1, mode="int-resolve")
            if _has_conflict_markers(repo, conflicts):
                bounce(
                    orchestrator, repo, ticket_id, lane, ref,
                    "Conflict markers remained after int-resolve",
                    {"conflicts": conflicts},
                )
                continue

            verdict, _, review_out = orchestrator.dispatch_reviewer(
                "INT", spec_stub, 1, author_model=resolver_model
            )
            if verdict != "accepted" or not orchestrator.ok_review(review_out):
                bounce(
                    orchestrator, repo, ticket_id, lane, ref,
                    "Conflict resolution review did not accept",
                    {"conflicts": conflicts, "review": review_out[-800:]},
                )
                continue

        # Step 2: Precheck + Full Gates on merged trunk (up to 2 int-gfix attempts)
        spec_stub = orchestrator.state_dir / f"{iid}.md"
        if not spec_stub.exists():
            spec_stub.write_text(
                f"# Integration Verification: {ticket_id}\n\n"
                f"Task `{ticket_id}` (commit `{commit_sha}` from lane `{lane}`) applied onto trunk.\n",
                encoding="utf-8",
            )

        passed = False
        last_log = ""
        for attempt in range(max_int_fixes + 1):
            pre_ok, pre_out = orchestrator.run_precheck(iid, attempt + 1)
            gates_ok, gates_out = (False, "")
            if pre_ok:
                gates_ok, gates_out = orchestrator.run_gates(iid, attempt + 1)
            if pre_ok and gates_ok:
                passed = True
                break
            last_log = gates_out or pre_out
            if attempt < max_int_fixes:
                orchestrator.log_event(
                    f"[INTEGRATOR] Checks failed on trunk for {ticket_id}; invoking {iid}-gfix{attempt + 1}"
                )
                orchestrator.dispatch_builder(
                    spec_stub,
                    attempt + 1,
                    feedback=(
                        f"Task {ticket_id} passed on lane {lane}, but failed after applying onto trunk.\n"
                        f"Task commit: git show {commit_sha}\n"
                        f"Failure log:\n{last_log[-800:]}"
                    ),
                    mode="int-gfix",
                )

        if passed:
            run_git(repo, ["add", "-A"])
            _, msg_out = run_git(repo, ["log", "-1", "--format=%s", commit_sha])
            title = re.sub(r"^checkpoint\s+", "", msg_out.strip()) or ticket_id
            commit_rc, _ = run_git(repo, ["commit", "-m", f"{title} (lane {lane})", "-m", f"Task commit {commit_sha}."])
            if commit_rc != 0:
                bounce(
                    orchestrator, repo, ticket_id, lane, ref,
                    "Task makes no change on trunk",
                    {"commit": commit_sha},
                )
                continue
            run_git(repo, ["update-ref", f"refs/done/{ticket_id}", "HEAD"])
            orchestrator.log_event(f"[INTEGRATOR] Integrated {ticket_id} onto trunk.")
            processed += 1
        else:
            bounce(
                orchestrator, repo, ticket_id, lane, ref,
                f"Checks failed on trunk after {max_int_fixes} integration fixes",
                {"log": last_log[-800:]},
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

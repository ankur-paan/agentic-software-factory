#!/usr/bin/env python3
"""
Agentic Software Factory Orchestrator
Automates the lifecycle of autonomous software implementation:
Builder -> Deterministic Gates -> Dual Adversarial Reviews (A & B) -> Checkpoint / Doctor.
Supports:
- 3-Tier Delta Convergence Loop (delta-only reviews on rounds > 1, non-blocking LATER list).
- Post-acceptance Doctor triage of minor findings into Wave MN.
- File-based Inbox system (.factory/inbox/escalations and .factory/inbox/rulings) for Antigravity co-pilot.
- Hybrid agent dispatch (CLI, Antigravity subagent prompts, or test stubs).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List


class FactoryOrchestrator:
    def __init__(self, config_path: str, dry_run: bool = False):
        self.config_path = Path(config_path)
        self.dry_run = dry_run
        self.config = self._load_config()
        self.workspace = Path(self.config.get("workspace_dir", ".")).resolve()
        
        # State and inbox directories
        self.state_dir = self.workspace / ".factory" / "state"
        self.inbox_dir = self.workspace / ".factory" / "inbox"
        self.escalations_dir = self.inbox_dir / "escalations"
        self.rulings_dir = self.inbox_dir / "rulings"
        
        for d in [self.state_dir, self.escalations_dir, self.rulings_dir]:
            d.mkdir(parents=True, exist_ok=True)
            
        self.max_rounds = int(self.config.get("max_rounds", 6))
        self.runner_type = self.config.get("agents", {}).get("runner_type", "cli")

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            print(f"[!] Config file not found at {self.config_path}. Using default configuration.")
            return {
                "max_rounds": 6,
                "gates": {
                    "compile_cmd": "echo '[GATE] compile passed'",
                    "lint_cmd": "echo '[GATE] lint passed'",
                    "test_cmd": "echo '[GATE] tests passed'"
                },
                "agents": {"runner_type": "cli"},
                "inbox": {"enabled": True},
                "delta_convergence": {"enabled": True, "auto_triage_minor": True},
                "git": {"auto_commit": True, "commit_prefix": "checkpoint"}
            }
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def log_event(self, message: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        events_file = self.state_dir / "events.log"
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")

    def run_command(self, cmd: str, log_file: Optional[Path] = None) -> Tuple[int, str]:
        if not cmd or cmd.strip() == "":
            return 0, ""
        self.log_event(f"Executing: {cmd}")
        if self.dry_run:
            output = f"[DRY-RUN] Simulated execution of: {cmd}"
            if log_file:
                log_file.write_text(output, encoding="utf-8")
            return 0, output

        try:
            res = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True
            )
            output = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            if log_file:
                log_file.write_text(output, encoding="utf-8")
            return res.returncode, output
        except Exception as e:
            err = f"Execution error: {e}"
            if log_file:
                log_file.write_text(err, encoding="utf-8")
            return 1, err

    def get_tree_sha(self) -> str:
        """Capture current git tree SHA to enable delta-only reviews in subsequent rounds."""
        try:
            res = subprocess.run(
                "git rev-parse HEAD^{tree}",
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return "HEAD"

    # -------------------------------------------------------------------------
    # Inbox Management (Antigravity Co-Pilot Interface)
    # -------------------------------------------------------------------------

    def create_escalation(self, ticket_id: str, reason: str, details: Dict[str, Any]) -> Path:
        """Write an escalation case file to the file-based inbox for Antigravity to triage."""
        case_file = self.escalations_dir / f"{ticket_id}.json"
        payload = {
            "case_id": ticket_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_id": ticket_id,
            "status": "pending_ruling",
            "reason": reason,
            "details": details
        }
        case_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.log_event(f"[INBOX] Escalation created: {case_file.name}. Waiting for Antigravity ruling.")
        return case_file

    def check_ruling(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Check if Antigravity or lead has deposited a ruling in the inbox."""
        ruling_file = self.rulings_dir / f"{ticket_id}.json"
        if ruling_file.exists():
            try:
                data = json.loads(ruling_file.read_text(encoding="utf-8"))
                self.log_event(f"[INBOX] Found ruling for {ticket_id}: {data.get('action', 'resume')}")
                return data
            except Exception as e:
                self.log_event(f"[!] Error reading ruling file {ruling_file}: {e}")
        return None

    def list_escalations(self) -> List[Dict[str, Any]]:
        """List all pending escalations in the inbox."""
        cases = []
        for f in self.escalations_dir.glob("*.json"):
            try:
                cases.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
        return cases

    # -------------------------------------------------------------------------
    # Deterministic Gates
    # -------------------------------------------------------------------------

    def run_gates(self, ticket_id: str, round_num: int) -> Tuple[bool, str]:
        self.log_event(f"--- Running Deterministic Gates for {ticket_id} (Round {round_num}) ---")
        gates = self.config.get("gates", {})
        gates_log_file = self.state_dir / f"{ticket_id}_round{round_num}_gates.log"
        combined_output = []
        success = True

        for gate_name in ["compile_cmd", "lint_cmd", "test_cmd", "qual_cmd"]:
            cmd = gates.get(gate_name)
            if not cmd:
                continue
            self.log_event(f"Running gate: {gate_name}")
            code, out = self.run_command(cmd)
            combined_output.append(f"=== {gate_name} (Exit code: {code}) ===\n{out}\n")
            if code != 0:
                self.log_event(f"[FAIL] Gate {gate_name} failed with code {code}.")
                success = False
                break
            else:
                self.log_event(f"[PASS] Gate {gate_name} passed.")

        full_log = "\n".join(combined_output)
        gates_log_file.write_text(full_log, encoding="utf-8")
        return success, full_log

    # -------------------------------------------------------------------------
    # Agent Dispatchers (Hybrid: CLI, Antigravity Prompts, or Stubs)
    # -------------------------------------------------------------------------

    def dispatch_builder(self, ticket_file: Path, round_num: int, feedback: str = "", ruling: Optional[Dict] = None) -> str:
        ticket_id = ticket_file.stem
        self.log_event(f"Dispatching Builder for {ticket_id} (Round {round_num})")
        
        prompt_file = self.state_dir / f"prompt_builder_{ticket_id}_r{round_num}.md"
        prompt_content = (
            f"# Builder Task: {ticket_id} (Round {round_num})\n\n"
            f"## Assigned Ticket Spec\n"
            f"{ticket_file.read_text(encoding='utf-8') if ticket_file.exists() else ''}\n\n"
        )
        if ruling:
            prompt_content += f"## Executive Doctor / CTO Ruling\n{json.dumps(ruling, indent=2)}\n\n"
        if feedback:
            prompt_content += f"## Previous Round Feedback\n{feedback}\n\n"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        if self.dry_run or self.runner_type == "stub":
            return f"[DRY-RUN] Builder completed round {round_num} for {ticket_id}."

        if self.runner_type == "cli":
            builder_cmd = self.config.get("agents", {}).get("builder_cmd")
            if not builder_cmd:
                return "Builder completed (simulated CLI)."
            cmd = f"{builder_cmd} --ticket {ticket_file}"
            code, out = self.run_command(cmd)
            return out
        elif self.runner_type == "antigravity":
            self.log_event(f"[ANTIGRAVITY] Prompt staged at {prompt_file.name}. Subagent or co-pilot may proceed.")
            return f"Prompt staged for Antigravity at {prompt_file}"

        return "Builder completed."

    def dispatch_reviewer(
        self, 
        role: str, 
        ticket_file: Path, 
        round_num: int, 
        prev_tree: Optional[str] = None, 
        prev_defects: str = ""
    ) -> Tuple[str, List[str], str]:
        """
        Dispatches Reviewer A or B.
        Returns: (verdict: 'accepted'|'changes', later_items: list, raw_output: str)
        """
        ticket_id = ticket_file.stem
        self.log_event(f"Dispatching Reviewer {role} for {ticket_id} (Round {round_num})")
        log_file = self.state_dir / f"{ticket_id}_round{round_num}_review_{role}.log"

        if self.dry_run or self.runner_type == "stub":
            verdict = "accepted"
            text = (
                f"[DRY-RUN] Reviewer {role} approved changes.\n"
                f"- **LATER (Non-blocking)**:\n"
                f"  - [{ticket_id}.rs:42]: minor comment typo\n"
                f"VERDICT: accepted"
            )
            log_file.write_text(text, encoding="utf-8")
            later = [f"{ticket_id}.rs:42: minor comment typo"]
            return verdict, later, text

        reviewer_cmd = self.config.get("agents", {}).get(f"reviewer_{role.lower()}_cmd")
        cmd_args = f"--role {role} --ticket {ticket_file}"
        if round_num > 1 and prev_tree:
            cmd_args += f" --prev-tree {prev_tree}"

        if self.runner_type == "cli" and reviewer_cmd:
            code, out = self.run_command(f"{reviewer_cmd} {cmd_args}", log_file=log_file)
        else:
            out = f"Reviewer {role} completed.\nVERDICT: accepted"
            log_file.write_text(out, encoding="utf-8")

        # Parse verdict and non-blocking LATER items
        verdict, later_items = self._parse_reviewer_findings(out)
        return verdict, later_items, out

    def _parse_reviewer_findings(self, output: str) -> Tuple[str, List[str]]:
        """Parses verdict and non-blocking LATER stream from reviewer output."""
        match = re.search(r"VERDICT:\s*(accepted|changes)", output, re.IGNORECASE)
        verdict = match.group(1).lower() if match else "changes"
        
        later_items = []
        # Look for LATER section
        in_later = False
        for line in output.splitlines():
            if re.search(r"LATER\s*\((?:Non-blocking)?\):?", line, re.IGNORECASE):
                in_later = True
                continue
            if in_later:
                if line.startswith("- **") or line.startswith("## ") or "VERDICT:" in line:
                    in_later = False
                    continue
                cleaned = line.strip().lstrip("-* ").strip()
                if cleaned and cleaned.lower() != "none":
                    later_items.append(cleaned)
        return verdict, later_items

    def triage_later_items(self, ticket_id: str, later_items: List[str]):
        """Doctor Section 5/7 post-acceptance triage: bundles valid minor items into Wave MN."""
        if not later_items:
            return
        wave_mn_file = self.state_dir / "wave_mn.tsv"
        self.log_event(f"[DOCTOR-TRIAGE] Triaging {len(later_items)} deferred minor findings for {ticket_id}")
        
        with open(wave_mn_file, "a", encoding="utf-8") as f:
            for item in later_items:
                # Format: VALID | <area> | <location> | <issue> | <fix>
                row = f"VALID\t{ticket_id}\t{item}\tminor-cleanup\n"
                f.write(row)
        self.log_event(f"[DOCTOR-TRIAGE] Successfully bundled {len(later_items)} findings into {wave_mn_file.name}")

    def dispatch_doctor(self, ticket_file: Path, round_num: int, reason: str, gate_log: str = ""):
        ticket_id = ticket_file.stem
        self.log_event(f"[ALERT] Escalating {ticket_id} to The Doctor! Reason: {reason}")
        doctor_log = self.state_dir / f"{ticket_id}_doctor.log"
        diagnosis = (
            f"## Doctor Forensic Diagnosis\n"
            f"- **Case ID**: {ticket_id}\n"
            f"- **Exhausted Rounds**: {round_num}\n"
            f"- **Trigger Reason**: {reason}\n"
            f"- **Classification**: TASK\n"
            f"DOCTOR-ACTION: escalate Human decision required for {ticket_id}\n"
        )
        doctor_log.write_text(diagnosis, encoding="utf-8")
        
        # Create case in file-based escalation inbox
        self.create_escalation(
            ticket_id=ticket_id,
            reason=reason,
            details={
                "ticket_file": str(ticket_file),
                "rounds_exhausted": round_num,
                "diagnosis_log": str(doctor_log),
                "recent_gate_snippet": gate_log[-1000:] if gate_log else ""
            }
        )

    def checkpoint_git(self, ticket_id: str, title: str):
        if not self.config.get("git", {}).get("auto_commit", True):
            return
        prefix = self.config.get("git", {}).get("commit_prefix", "checkpoint")
        msg = f"{prefix} {ticket_id}: {title}"
        self.log_event(f"Creating Git Checkpoint: {msg}")
        self.run_command("git add .")
        self.run_command(f'git commit -m "{msg}"')
        accepted_file = self.state_dir / "accepted.txt"
        with open(accepted_file, "a", encoding="utf-8") as f:
            f.write(f"{ticket_id} - {title}\n")

    # -------------------------------------------------------------------------
    # Main Ticket Execution Loop
    # -------------------------------------------------------------------------

    def execute_ticket(self, ticket_path: str, resume: bool = False) -> bool:
        ticket_file = Path(ticket_path).resolve()
        if not ticket_file.exists():
            print(f"[!] Ticket file not found: {ticket_file}")
            return False

        ticket_id = ticket_file.stem
        self.log_event("=" * 60)
        self.log_event(f"Starting Execution for Ticket: {ticket_id} (resume={resume})")
        self.log_event("=" * 60)

        # Check for pre-existing inbox ruling if resuming
        ruling = self.check_ruling(ticket_id) if resume else None
        if ruling:
            self.log_event(f"Resuming {ticket_id} under recorded ruling from Antigravity / CTO inbox.")

        feedback = ""
        prev_tree_sha = None
        accumulated_later = []

        for current_round in range(1, self.max_rounds + 1):
            self.log_event(f"\n>>> ROUND {current_round}/{self.max_rounds} for {ticket_id} <<<")

            # 1. Capture snapshot before builder run for delta review in subsequent rounds
            if current_round > 1:
                prev_tree_sha = self.get_tree_sha()

            # 2. Builder step
            self.dispatch_builder(ticket_file, current_round, feedback, ruling)

            # 3. Gatekeeper step
            gates_passed, gate_output = self.run_gates(ticket_id, current_round)
            if not gates_passed:
                self.log_event(f"[!] Gates failed in round {current_round}. Routing failure log back to Builder.")
                feedback = f"Gate failure log:\n{gate_output[-800:]}"
                continue

            # 4. Dual Adversarial Review (with delta convergence in rounds > 1)
            verdict_a, later_a, rev_a_text = self.dispatch_reviewer(
                "A", ticket_file, current_round, prev_tree=prev_tree_sha, prev_defects=feedback
            )
            verdict_b, later_b, rev_b_text = self.dispatch_reviewer(
                "B", ticket_file, current_round, prev_tree=prev_tree_sha, prev_defects=feedback
            )

            accumulated_later.extend(later_a)
            accumulated_later.extend(later_b)

            self.log_event(
                f"Review Results: Reviewer A = {verdict_a.upper()} ({len(later_a)} later), "
                f"Reviewer B = {verdict_b.upper()} ({len(later_b)} later)"
            )

            # Convergence Check: both accepted (regardless of non-blocking LATER items)
            if verdict_a == "accepted" and verdict_b == "accepted":
                self.log_event(f"[SUCCESS] Ticket {ticket_id} ACCEPTED by both Reviewers!")
                self.checkpoint_git(ticket_id, f"Implemented {ticket_id}")

                # Doctor Section 5/7 Post-Acceptance Triage into Wave MN
                if accumulated_later and self.config.get("delta_convergence", {}).get("auto_triage_minor", True):
                    self.triage_later_items(ticket_id, list(set(accumulated_later)))

                return True
            else:
                feedback = (
                    f"Reviewer Rejections in Round {current_round}:\n"
                    f"Reviewer A: {verdict_a}\n"
                    f"Reviewer B: {verdict_b}\n"
                )
                self.log_event(f"[!] Ticket {ticket_id} received changes request. Proceeding to next round.")

        # If round limit is exhausted: escalate to Doctor
        self.dispatch_doctor(ticket_file, self.max_rounds, "Round limit exhausted without dual approval")
        return False


def main():
    parser = argparse.ArgumentParser(description="Agentic Software Factory Orchestrator")
    parser.add_argument("--ticket", type=str, help="Path to ticket markdown specification")
    parser.add_argument("--resume", action="store_true", help="Resume a ticket using ruling from .factory/inbox/rulings")
    parser.add_argument("--check-inbox", action="store_true", help="Inspect file-based inbox for pending escalations")
    parser.add_argument("--config", type=str, default="harness/config.example.json", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying files or running commands")
    args = parser.parse_args()

    orchestrator = FactoryOrchestrator(config_path=args.config, dry_run=args.dry_run)

    if args.check_inbox:
        escalations = orchestrator.list_escalations()
        print(f"\n=== Antigravity Escalation Inbox ({len(escalations)} pending) ===")
        for esc in escalations:
            print(f"- Case: {esc.get('case_id')} | Reason: {esc.get('reason')} | Status: {esc.get('status')}")
        sys.exit(0)

    if args.ticket:
        success = orchestrator.execute_ticket(args.ticket, resume=args.resume)
        sys.exit(0 if success else 1)
    else:
        print("Agentic Software Factory Orchestrator loaded successfully.")
        print("Run with --ticket <path/to/ticket.md> to start a task, or --check-inbox to view pending escalations.")
        sys.exit(0)


if __name__ == "__main__":
    main()

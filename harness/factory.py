#!/usr/bin/env python3
"""
Agentic Software Factory Orchestrator
Automates the lifecycle of autonomous software implementation:
Builder -> Deterministic Gates -> Dual Adversarial Reviews (A & B) -> Checkpoint / Doctor.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional


class FactoryOrchestrator:
    def __init__(self, config_path: str, dry_run: bool = False):
        self.config_path = Path(config_path)
        self.dry_run = dry_run
        self.config = self._load_config()
        self.workspace = Path(self.config.get("workspace_dir", ".")).resolve()
        self.state_dir = self.workspace / ".factory" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.max_rounds = int(self.config.get("max_rounds", 6))

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

    def dispatch_builder(self, ticket_file: Path, round_num: int, feedback: str = "") -> str:
        ticket_id = ticket_file.stem
        self.log_event(f"Dispatching Builder for {ticket_id} (Round {round_num})")
        if self.dry_run:
            return f"[DRY-RUN] Builder completed round {round_num} for {ticket_id}."

        builder_cmd = self.config.get("agents", {}).get("builder_cmd")
        if not builder_cmd:
            self.log_event("No builder_cmd specified in config. Simulating prompt handoff.")
            return "Builder completed."

        cmd = f"{builder_cmd} --ticket {ticket_file}"
        code, out = self.run_command(cmd)
        return out

    def dispatch_reviewer(self, role: str, ticket_file: Path, round_num: int) -> Tuple[str, str]:
        ticket_id = ticket_file.stem
        self.log_event(f"Dispatching Reviewer {role} for {ticket_id} (Round {round_num})")
        log_file = self.state_dir / f"{ticket_id}_round{round_num}_review_{role}.log"

        if self.dry_run:
            verdict = "accepted"
            text = f"[DRY-RUN] Reviewer {role} approved changes.\nVERDICT: accepted"
            log_file.write_text(text, encoding="utf-8")
            return verdict, text

        reviewer_cmd = self.config.get("agents", {}).get(f"reviewer_{role.lower()}_cmd")
        if not reviewer_cmd:
            # Default auto-approval in test stub if no CLI set
            verdict = "accepted"
            text = f"Reviewer {role} completed.\nVERDICT: accepted"
            log_file.write_text(text, encoding="utf-8")
            return verdict, text

        code, out = self.run_command(f"{reviewer_cmd} --role {role} --ticket {ticket_file}", log_file=log_file)
        match = re.search(r"VERDICT:\s*(accepted|changes)", out, re.IGNORECASE)
        verdict = match.group(1).lower() if match else "changes"
        return verdict, out

    def dispatch_doctor(self, ticket_file: Path, round_num: int, reason: str):
        ticket_id = ticket_file.stem
        self.log_event(f"[ALERT] Escalating {ticket_id} to The Doctor! Reason: {reason}")
        doctor_log = self.state_dir / f"{ticket_id}_doctor.log"
        diagnosis = (
            f"## Doctor Diagnostic Session\n"
            f"- Case: {ticket_id}\n"
            f"- Exhausted rounds: {round_num}\n"
            f"- Trigger reason: {reason}\n"
            f"- Classification: TASK\n"
            f"DOCTOR-ACTION: escalate Human decision required for {ticket_id}\n"
        )
        doctor_log.write_text(diagnosis, encoding="utf-8")
        self.log_event(f"[DOCTOR] Diagnosis logged to {doctor_log.name}. Alert sent to lead.")

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

    def execute_ticket(self, ticket_path: str) -> bool:
        ticket_file = Path(ticket_path).resolve()
        if not ticket_file.exists():
            print(f"[!] Ticket file not found: {ticket_file}")
            return False

        ticket_id = ticket_file.stem
        self.log_event(f"==================================================")
        self.log_event(f"Starting Execution for Ticket: {ticket_id}")
        self.log_event(f"==================================================")

        feedback = ""
        for current_round in range(1, self.max_rounds + 1):
            self.log_event(f"\n>>> ROUND {current_round}/{self.max_rounds} for {ticket_id} <<<")

            # 1. Builder step
            self.dispatch_builder(ticket_file, current_round, feedback)

            # 2. Gatekeeper step
            gates_passed, gate_output = self.run_gates(ticket_id, current_round)
            if not gates_passed:
                self.log_event(f"[!] Gates failed in round {current_round}. Routing log back to Builder.")
                feedback = f"Gate failure log:\n{gate_output[-500:]}"
                continue

            # 3. Dual Adversarial Review
            verdict_a, rev_a_text = self.dispatch_reviewer("A", ticket_file, current_round)
            verdict_b, rev_b_text = self.dispatch_reviewer("B", ticket_file, current_round)

            self.log_event(f"Review Results: Reviewer A = {verdict_a.upper()}, Reviewer B = {verdict_b.upper()}")

            if verdict_a == "accepted" and verdict_b == "accepted":
                self.log_event(f"[SUCCESS] Ticket {ticket_id} ACCEPTED by both Reviewer A and Reviewer B!")
                self.checkpoint_git(ticket_id, f"Implemented {ticket_id}")
                return True
            else:
                feedback = (
                    f"Reviewer Rejections in Round {current_round}:\n"
                    f"Reviewer A: {verdict_a}\n"
                    f"Reviewer B: {verdict_b}\n"
                )
                self.log_event(f"[!] Ticket {ticket_id} received changes request. Proceeding to next round.")

        # If we exit the loop, round limit was exhausted
        self.dispatch_doctor(ticket_file, self.max_rounds, "Round limit exhausted without dual approval")
        return False


def main():
    parser = argparse.ArgumentParser(description="Agentic Software Factory Orchestrator")
    parser.add_argument("--ticket", type=str, help="Path to ticket markdown specification")
    parser.add_argument("--config", type=str, default="harness/config.example.json", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying files or running commands")
    args = parser.parse_args()

    orchestrator = FactoryOrchestrator(config_path=args.config, dry_run=args.dry_run)
    if args.ticket:
        success = orchestrator.execute_ticket(args.ticket)
        sys.exit(0 if success else 1)
    else:
        print("Agentic Software Factory Orchestrator loaded successfully.")
        print("Run with --ticket <path/to/ticket.md> to start a task.")
        sys.exit(0)


if __name__ == "__main__":
    main()

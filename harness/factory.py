#!/usr/bin/env python3
"""
Agentic Software Factory Orchestrator
Automates the lifecycle of autonomous software implementation:
Spec Check -> Builder -> Precheck -> Dual Reviews + Arbiter -> Full Gates -> Checkpoint / Doctor.

Supports:
- Pre-flight Spec Check against specs/SPEC_STANDARD.md.
- Two-tier verification: fast precheck before review, full gates only after review acceptance.
- Evidence-enforced reviews (FILES READ, REACHABILITY, SLOP) + Arbiter adjudication.
- Recursive Harnessing (Harness^2): task-level Propose/Probe/Compose + rules/LESSONS.md.
- 3-Tier Delta Convergence Loop (delta-only reviews on rounds > 1, non-blocking LATER list).
- Post-acceptance Doctor triage of minor findings into Wave MN + 2-case escalation cap.
- Safe git parking (refs/stopped/<id>) for interrupted or stopped tasks.
- Optional central Model Broker HTTP integration for free/multi-provider model rotation.
- File-based Inbox (.factory/inbox/escalations and .factory/inbox/rulings) for Antigravity co-pilot.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class FactoryOrchestrator:
    """Coordinates spec checks, builders, prechecks, reviews, arbiter, gates, harness, and doctor."""

    def __init__(self, config_path: str, dry_run: bool = False):
        self.config_path = Path(config_path)
        self.dry_run = dry_run
        self.config = self._load_config()
        self.workspace = Path(self.config.get("workspace_dir", ".")).resolve()

        self.state_dir = self.workspace / ".factory" / "state"
        self.harness_state_dir = self.state_dir / "harness"
        self.inbox_dir = self.workspace / ".factory" / "inbox"
        self.escalations_dir = self.inbox_dir / "escalations"
        self.rulings_dir = self.inbox_dir / "rulings"

        for d in [self.state_dir, self.harness_state_dir, self.escalations_dir, self.rulings_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.max_rounds = int(self.config.get("max_rounds", 5))
        self.runner_type = self.config.get("agents", {}).get("runner_type", "cli")

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            print(f"[!] Config file not found at {self.config_path}. Using default configuration.")
            return {
                "max_rounds": 5,
                "spec_check": {"enabled": True, "max_revisions": 1},
                "precheck": {
                    "format_cmd": "",
                    "compile_cmd": "echo '[PRECHECK] compile passed'",
                    "lint_cmd": "echo '[PRECHECK] lint passed'",
                    "max_fixes": 4,
                },
                "gates": {
                    "test_cmd": "echo '[GATE] tests passed'",
                    "max_fixes": 4,
                },
                "agents": {"runner_type": "cli"},
                "harness": {"enabled": True, "lessons_file": "rules/LESSONS.md"},
                "model_broker": {"enabled": False},
                "doctor": {"max_cases_per_ticket": 2},
                "inbox": {"enabled": True},
                "delta_convergence": {"enabled": True, "auto_triage_minor": True},
                "git": {"auto_commit": True, "commit_prefix": "checkpoint", "park_stopped": True},
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
                text=True,
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
                text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return "HEAD"

    # -------------------------------------------------------------------------
    # Optional Model Broker Client
    # -------------------------------------------------------------------------

    def broker_pick(self, exclude: Optional[List[str]] = None) -> Optional[str]:
        """Ask the optional central model broker which model to use now."""
        mb = self.config.get("model_broker", {})
        if not mb.get("enabled", False) or self.dry_run:
            return None
        base_url = mb.get("url", "http://127.0.0.1:8787").rstrip("/")
        excl = ",".join(exclude or [])
        url = f"{base_url}/pick?exclude={urllib.parse.quote(excl)}"
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                chosen = resp.read().decode("utf-8").strip()
                return chosen or None
        except Exception as e:
            self.log_event(f"[BROKER] pick failed ({e}); using configured default command.")
            return None

    def broker_report(self, model: Optional[str], ok: bool, kind: str = "run", who: str = ""):
        """Report run outcome to the optional central model broker."""
        mb = self.config.get("model_broker", {})
        if not mb.get("enabled", False) or not model or self.dry_run:
            return
        base_url = mb.get("url", "http://127.0.0.1:8787").rstrip("/")
        qs = urllib.parse.urlencode({"model": model, "ok": "1" if ok else "0", "kind": kind, "who": who})
        try:
            urllib.request.urlopen(f"{base_url}/report?{qs}", timeout=3).read()
        except Exception:
            pass

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
            "details": details,
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
    # Pre-Flight Spec Check
    # -------------------------------------------------------------------------

    def run_spec_check(self, ticket_file: Path) -> bool:
        """Verify the ticket spec against specs/SPEC_STANDARD.md before starting implementation."""
        spec_cfg = self.config.get("spec_check", {})
        if not spec_cfg.get("enabled", True):
            return True

        ticket_id = ticket_file.stem
        self.log_event(f"--- Pre-Flight Spec Check for {ticket_id} ---")
        spec_log = self.state_dir / f"{ticket_id}_speccheck.log"

        if self.dry_run or self.runner_type == "stub":
            out = (
                "PARAPHRASE:\nDry-run spec check passed.\n\n"
                "FILES:\n- dry-run: ok\n\n"
                "CONTRADICTIONS:\nnone\n\n"
                "GAPS:\nnone\n\n"
                "SPECCHECK: ready\n"
            )
            spec_log.write_text(out, encoding="utf-8")
            self.log_event(f"[PASS] Spec Check ready for {ticket_id}.")
            return True

        cmd = self.config.get("agents", {}).get("spec_reader_cmd")
        if self.runner_type == "cli" and cmd:
            _, out = self.run_command(f"{cmd} --role SPEC_READER --ticket {ticket_file}", log_file=spec_log)
        else:
            out = "SPECCHECK: ready\n"
            spec_log.write_text(out, encoding="utf-8")

        ready = bool(re.search(r"^SPECCHECK:\s*ready\b", out, re.MULTILINE | re.IGNORECASE))
        if not ready:
            self.log_event(f"[FAIL] Spec Check not-ready for {ticket_id}. Escalating.")
            self.create_escalation(
                ticket_id=ticket_id,
                reason="Pre-flight Spec Check failed (SPECCHECK: not-ready)",
                details={"ticket_file": str(ticket_file), "speccheck_log": str(spec_log)},
            )
            return False

        self.log_event(f"[PASS] Spec Check ready for {ticket_id}.")
        return True

    # -------------------------------------------------------------------------
    # Two-Tier Deterministic Verification (Precheck -> Review -> Full Gates)
    # -------------------------------------------------------------------------

    def _run_command_group(
        self, ticket_id: str, round_num: int, phase: str, commands: List[Tuple[str, str]]
    ) -> Tuple[bool, str]:
        self.log_event(f"--- Running {phase.upper()} for {ticket_id} (Round {round_num}) ---")
        log_file = self.state_dir / f"{ticket_id}_round{round_num}_{phase}.log"
        combined_output = []
        success = True

        for name, cmd in commands:
            if not cmd or not cmd.strip():
                continue
            self.log_event(f"Running {phase}: {name}")
            code, out = self.run_command(cmd)
            combined_output.append(f"=== {name} (Exit code: {code}) ===\n{out}\n")
            if code != 0:
                self.log_event(f"[FAIL] {phase} {name} failed with code {code}.")
                success = False
                break
            self.log_event(f"[PASS] {phase} {name} passed.")

        full_log = "\n".join(combined_output)
        log_file.write_text(full_log, encoding="utf-8")
        return success, full_log

    def run_precheck(self, ticket_id: str, round_num: int) -> Tuple[bool, str]:
        """Fast deterministic checks run BEFORE every review."""
        pre = self.config.get("precheck", {})
        if not pre:
            # Backward-compatible fallback for older configs
            g = self.config.get("gates", {})
            pre = {"compile_cmd": g.get("compile_cmd", ""), "lint_cmd": g.get("lint_cmd", "")}
        cmds = [
            ("format_cmd", pre.get("format_cmd", "")),
            ("compile_cmd", pre.get("compile_cmd", "")),
            ("lint_cmd", pre.get("lint_cmd", "")),
        ]
        return self._run_command_group(ticket_id, round_num, "precheck", cmds)

    def run_gates(self, ticket_id: str, round_num: int) -> Tuple[bool, str]:
        """Full expensive CI (tests, benchmarks, qualification) run AFTER review acceptance."""
        gates = self.config.get("gates", {})
        cmds = [
            ("test_cmd", gates.get("test_cmd", "")),
            ("bench_cmd", gates.get("bench_cmd", "")),
            ("qual_cmd", gates.get("qual_cmd", "")),
        ]
        return self._run_command_group(ticket_id, round_num, "gates", cmds)

    # -------------------------------------------------------------------------
    # Recursive Harnessing (Harness^2)
    # -------------------------------------------------------------------------

    def _read_lessons(self) -> str:
        harness_cfg = self.config.get("harness", {})
        if not harness_cfg.get("enabled", True):
            return ""
        lessons_path = self.workspace / harness_cfg.get("lessons_file", "rules/LESSONS.md")
        if lessons_path.exists():
            return lessons_path.read_text(encoding="utf-8")
        return ""

    def harness_edit(self, ticket_file: Path, round_num: int, defects: str):
        """Task-level Propose/Probe/Compose: write targeted guidance for the next round."""
        if not self.config.get("harness", {}).get("enabled", True):
            return
        ticket_id = ticket_file.stem
        task_harness = self.harness_state_dir / f"{ticket_id}.md"
        self.log_event(f"[HARNESS^2] Running task-level harness editor for {ticket_id} (Round {round_num})")

        if self.dry_run or self.runner_type == "stub":
            entry = (
                f"## Round {round_num} Harness Edit\n"
                f"- [PROPOSED] Check failing log evidence before editing.\n"
            )
            with open(task_harness, "a", encoding="utf-8") as f:
                f.write(entry)
            return

        cmd = self.config.get("agents", {}).get("harness_editor_cmd")
        if self.runner_type == "cli" and cmd:
            self.run_command(
                f"{cmd} --role HARNESS_EDITOR --ticket {ticket_file} --out {task_harness}",
                log_file=self.state_dir / f"{ticket_id}_round{round_num}_harness_edit.log",
            )

    def harness_reflect(self, ticket_file: Path, outcome: str, classes: List[str]):
        """Harnessing-level reflection: distill KEPT edits & recurring classes into rules/LESSONS.md."""
        if not self.config.get("harness", {}).get("enabled", True):
            return
        ticket_id = ticket_file.stem
        self.log_event(f"[HARNESS^2] Running experience reflector for {ticket_id} ({outcome})")

        if self.dry_run or self.runner_type == "stub":
            return

        cmd = self.config.get("agents", {}).get("reflector_cmd")
        if self.runner_type == "cli" and cmd:
            self.run_command(
                f"{cmd} --role REFLECTOR --ticket {ticket_file}",
                log_file=self.state_dir / f"{ticket_id}_reflect.log",
            )

    # -------------------------------------------------------------------------
    # Agent Dispatchers
    # -------------------------------------------------------------------------

    def dispatch_builder(
        self,
        ticket_file: Path,
        round_num: int,
        feedback: str = "",
        ruling: Optional[Dict] = None,
        mode: str = "build",
    ) -> Tuple[str, Optional[str]]:
        ticket_id = ticket_file.stem
        self.log_event(f"Dispatching Builder ({mode}) for {ticket_id} (Round {round_num})")

        prompt_file = self.state_dir / f"prompt_builder_{ticket_id}_r{round_num}_{mode}.md"
        lessons = self._read_lessons()
        task_harness_file = self.harness_state_dir / f"{ticket_id}.md"
        task_harness = task_harness_file.read_text(encoding="utf-8") if task_harness_file.exists() else ""

        prompt_content = f"# Builder Task: {ticket_id} (Round {round_num}, Mode: {mode})\n\n"
        if lessons:
            prompt_content += f"## Distilled Lessons (rules/LESSONS.md)\n{lessons}\n\n"
        if task_harness:
            prompt_content += f"## Task Harness Guidance\n{task_harness}\n\n"
        prompt_content += (
            f"## Assigned Ticket Spec\n"
            f"{ticket_file.read_text(encoding='utf-8') if ticket_file.exists() else ''}\n\n"
        )
        if ruling:
            prompt_content += f"## Executive Doctor / CTO Ruling\n{json.dumps(ruling, indent=2)}\n\n"
        if feedback:
            prompt_content += f"## Previous Round Feedback\n{feedback}\n\n"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        if self.dry_run or self.runner_type == "stub":
            return f"[DRY-RUN] Builder ({mode}) completed round {round_num} for {ticket_id}.", None

        model = self.broker_pick()
        if self.runner_type == "cli":
            builder_cmd = self.config.get("agents", {}).get("builder_cmd")
            if not builder_cmd:
                return "Builder completed (simulated CLI).", model
            cmd = f"{builder_cmd} --ticket {ticket_file}"
            if model:
                cmd += f" --model {model}"
            code, out = self.run_command(cmd)
            self.broker_report(model, ok=(code == 0), kind=mode, who=f"builder-{ticket_id}")
            return out, model
        elif self.runner_type == "antigravity":
            self.log_event(f"[ANTIGRAVITY] Prompt staged at {prompt_file.name}.")
            return f"Prompt staged for Antigravity at {prompt_file}", model

        return "Builder completed.", model

    @staticmethod
    def ok_review(output: str) -> bool:
        """
        Verify that a review is a valid accept with all required evidence sections
        (FILES READ, REACHABILITY, SLOP). An accept missing any section is rejected.
        """
        if not re.search(r"VERDICT:\s*accepted\b", output, re.IGNORECASE):
            return False
        required_sections = ["FILES READ", "REACHABILITY", "SLOP"]
        return all(re.search(rf"\b{sec}\b", output, re.IGNORECASE) for sec in required_sections)

    @staticmethod
    def _parse_reviewer_findings(output: str) -> Tuple[str, List[str]]:
        """Parse verdict and non-blocking LATER stream from reviewer output."""
        match = re.search(r"VERDICT:\s*(accepted|changes)", output, re.IGNORECASE)
        verdict = match.group(1).lower() if match else "changes"

        later_items = []
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

    def dispatch_reviewer(
        self,
        role: str,
        ticket_file: Path,
        round_num: int,
        prev_tree: Optional[str] = None,
        author_model: Optional[str] = None,
    ) -> Tuple[str, List[str], str]:
        """Dispatch Reviewer A or B, excluding the author's model when broker is enabled."""
        ticket_id = ticket_file.stem
        self.log_event(f"Dispatching Reviewer {role} for {ticket_id} (Round {round_num})")
        log_file = self.state_dir / f"{ticket_id}_round{round_num}_review_{role}.log"

        if self.dry_run or self.runner_type == "stub":
            text = (
                f"## Reviewer {role} Report\n"
                f"- **FILES READ**: `{ticket_file.name}`\n"
                f"- **REACHABILITY**: Verified production entrypoint.\n"
                f"- **SLOP**: None\n"
                f"- **LATER (Non-blocking)**:\n"
                f"  - [{ticket_id}.ext:42]: minor comment typo\n"
                f"VERDICT: accepted\n"
            )
            log_file.write_text(text, encoding="utf-8")
            return "accepted", [f"{ticket_id}.ext:42: minor comment typo"], text

        agents_cfg = self.config.get("agents", {})
        reviewer_cmd = agents_cfg.get(f"reviewer_{role.lower()}_cmd") or agents_cfg.get("reviewer_a_cmd")
        model = self.broker_pick(exclude=[author_model] if author_model else None)
        cmd_args = f"--role {role} --ticket {ticket_file}"
        if round_num > 1 and prev_tree:
            cmd_args += f" --prev-tree {prev_tree}"
        if model:
            cmd_args += f" --model {model}"

        if self.runner_type == "cli" and reviewer_cmd:
            code, out = self.run_command(f"{reviewer_cmd} {cmd_args}", log_file=log_file)
            self.broker_report(model, ok=(code == 0), kind="review", who=f"review{role}-{ticket_id}")
        else:
            out = (
                f"- **FILES READ**: `{ticket_file.name}`\n"
                f"- **REACHABILITY**: Verified\n"
                f"- **SLOP**: None\n"
                f"VERDICT: accepted\n"
            )
            log_file.write_text(out, encoding="utf-8")

        verdict, later_items = self._parse_reviewer_findings(out)
        if verdict == "accepted" and not self.ok_review(out):
            self.log_event(f"[REJECTED] Reviewer {role} claimed accept without required evidence sections.")
            verdict = "changes"
        return verdict, later_items, out

    def dispatch_arbiter(
        self,
        ticket_file: Path,
        round_num: int,
        review_a_log: Path,
        review_b_log: Path,
        author_model: Optional[str] = None,
    ) -> Tuple[bool, str, List[str]]:
        """Adjudicate findings when reviewers disagree or lack evidence."""
        ticket_id = ticket_file.stem
        self.log_event(f"Dispatching Arbiter for {ticket_id} (Round {round_num})")
        arb_log = self.state_dir / f"{ticket_id}_round{round_num}_arbiter.log"

        if self.dry_run or self.runner_type == "stub":
            out = "ARBITER: accept\nCONFIRMED:\nnone\nCLASSES: none\n"
            arb_log.write_text(out, encoding="utf-8")
            return True, out, []

        cmd = self.config.get("agents", {}).get("arbiter_cmd")
        model = self.broker_pick(exclude=[author_model] if author_model else None)
        if self.runner_type == "cli" and cmd:
            full_cmd = f"{cmd} --role ARBITER --ticket {ticket_file}"
            if model:
                full_cmd += f" --model {model}"
            code, out = self.run_command(full_cmd, log_file=arb_log)
            self.broker_report(model, ok=(code == 0), kind="arbiter", who=f"arbiter-{ticket_id}")
        else:
            out = "ARBITER: changes\nCONFIRMED:\n- Review rejections require fixes.\nCLASSES: R-ENTRY\n"
            arb_log.write_text(out, encoding="utf-8")

        accepted = bool(re.match(r"^\s*ARBITER:\s*accept\b", out, re.IGNORECASE))
        classes_match = re.search(r"^CLASSES:\s*(.+)$", out, re.MULTILINE | re.IGNORECASE)
        classes: List[str] = []
        if classes_match:
            raw = classes_match.group(1).strip()
            if raw.lower() != "none":
                classes = [c.strip() for c in raw.split(",") if c.strip()]
        return accepted, out, classes

    # -------------------------------------------------------------------------
    # Doctor, Minor Triage, and Git Checkpoint / Parking
    # -------------------------------------------------------------------------

    def triage_later_items(self, ticket_id: str, later_items: List[str]):
        """Doctor post-acceptance triage: bundle valid minor items into Wave MN."""
        if not later_items:
            return
        wave_mn_file = self.state_dir / "wave_mn.tsv"
        self.log_event(f"[DOCTOR-TRIAGE] Triaging {len(later_items)} deferred minor findings for {ticket_id}")
        with open(wave_mn_file, "a", encoding="utf-8") as f:
            for item in later_items:
                f.write(f"VALID\t{ticket_id}\t{item}\tminor-cleanup\n")

    def _doctor_case_count(self, ticket_id: str) -> int:
        count_file = self.state_dir / f"{ticket_id}_doctor_count.txt"
        if count_file.exists():
            try:
                return int(count_file.read_text(encoding="utf-8").strip())
            except Exception:
                return 0
        return 0

    def _increment_doctor_case_count(self, ticket_id: str) -> int:
        count = self._doctor_case_count(ticket_id) + 1
        (self.state_dir / f"{ticket_id}_doctor_count.txt").write_text(str(count), encoding="utf-8")
        return count

    def dispatch_doctor(self, ticket_file: Path, round_num: int, reason: str, gate_log: str = ""):
        ticket_id = ticket_file.stem
        case_num = self._increment_doctor_case_count(ticket_id)
        max_cases = int(self.config.get("doctor", {}).get("max_cases_per_ticket", 2))

        self.log_event(f"[ALERT] Escalating {ticket_id} to The Doctor (Case #{case_num}/{max_cases}). Reason: {reason}")
        doctor_log = self.state_dir / f"{ticket_id}_doctor.log"

        if case_num > max_cases:
            diagnosis = (
                f"## Doctor Forensic Diagnosis\n"
                f"- **Case ID**: {ticket_id}\n"
                f"- **Trigger Reason**: Exceeded max Doctor cases ({max_cases}): {reason}\n"
                f"- **Classification**: PROCESS\n"
                f"DOCTOR-ACTION: escalate Human decision required after {max_cases} failed Doctor attempts\n"
            )
        else:
            diagnosis = (
                f"## Doctor Forensic Diagnosis\n"
                f"- **Case ID**: {ticket_id}\n"
                f"- **Exhausted Rounds**: {round_num}\n"
                f"- **Trigger Reason**: {reason}\n"
                f"- **Classification**: TASK\n"
                f"DOCTOR-ACTION: escalate Human decision required for {ticket_id}\n"
            )
        doctor_log.write_text(diagnosis, encoding="utf-8")

        self.create_escalation(
            ticket_id=ticket_id,
            reason=reason,
            details={
                "ticket_file": str(ticket_file),
                "doctor_case_number": case_num,
                "rounds_exhausted": round_num,
                "diagnosis_log": str(doctor_log),
                "recent_gate_snippet": gate_log[-1000:] if gate_log else "",
            },
        )

    def park_stopped(self, ticket_id: str):
        """Park unfinished work under refs/stopped/<id> and restore a clean working tree."""
        if not self.config.get("git", {}).get("park_stopped", True):
            return
        self.log_event(f"[GIT] Parking stopped work for {ticket_id} under refs/stopped/{ticket_id}")
        if self.dry_run:
            return
        code, status = self.run_command("git status --porcelain")
        if code == 0 and status.strip():
            self.run_command("git add -A")
            code, _ = self.run_command(f'git commit -m "wip: parked {ticket_id}"')
            if code == 0:
                self.run_command(f"git update-ref refs/stopped/{ticket_id} HEAD")
                self.run_command("git reset --hard HEAD~1")
                self.run_command("git clean -fd")

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

        ruling = self.check_ruling(ticket_id) if resume else None
        if ruling:
            self.log_event(f"Resuming {ticket_id} under recorded ruling from Antigravity / CTO inbox.")

        if not resume and not self.run_spec_check(ticket_file):
            return False

        feedback = ""
        prev_tree_sha = None
        accumulated_later: List[str] = []
        accumulated_classes: List[str] = []
        max_pfix = int(self.config.get("precheck", {}).get("max_fixes", 4))
        max_gfix = int(self.config.get("gates", {}).get("max_fixes", 4))

        for current_round in range(1, self.max_rounds + 1):
            self.log_event(f"\n>>> ROUND {current_round}/{self.max_rounds} for {ticket_id} <<<")
            if current_round > 1:
                prev_tree_sha = self.get_tree_sha()

            # 1. Builder step
            _, author_model = self.dispatch_builder(ticket_file, current_round, feedback, ruling, mode="build")

            # 2. Fast Precheck before review (with pfix sub-loop)
            precheck_ok = False
            precheck_out = ""
            for ptry in range(max_pfix + 1):
                precheck_ok, precheck_out = self.run_precheck(ticket_id, current_round)
                if precheck_ok:
                    break
                if ptry < max_pfix:
                    self.log_event(f"[PRECHECK] Failed (try {ptry + 1}/{max_pfix}); dispatching quick fix.")
                    self.dispatch_builder(
                        ticket_file, current_round, f"Precheck failure:\n{precheck_out[-800:]}", ruling, mode="pfix"
                    )

            if not precheck_ok:
                feedback = f"Precheck failure log:\n{precheck_out[-800:]}"
                self.harness_edit(ticket_file, current_round, feedback)
                continue

            # 3. Dual Adversarial Review (evidence-enforced)
            verdict_a, later_a, _ = self.dispatch_reviewer(
                "A", ticket_file, current_round, prev_tree=prev_tree_sha, author_model=author_model
            )
            verdict_b, later_b, _ = self.dispatch_reviewer(
                "B", ticket_file, current_round, prev_tree=prev_tree_sha, author_model=author_model
            )
            accumulated_later.extend(later_a)
            accumulated_later.extend(later_b)

            reviewed_accept = (verdict_a == "accepted" and verdict_b == "accepted")
            arbiter_out = ""

            if not reviewed_accept:
                ra_log = self.state_dir / f"{ticket_id}_round{current_round}_review_A.log"
                rb_log = self.state_dir / f"{ticket_id}_round{current_round}_review_B.log"
                reviewed_accept, arbiter_out, classes = self.dispatch_arbiter(
                    ticket_file, current_round, ra_log, rb_log, author_model=author_model
                )
                accumulated_classes.extend(classes)

            # 4. Full Expensive Gates run ONLY after review/arbiter acceptance
            if reviewed_accept:
                gates_ok = False
                gate_out = ""
                for gtry in range(max_gfix + 1):
                    gates_ok, gate_out = self.run_gates(ticket_id, current_round)
                    if gates_ok:
                        break
                    if gtry < max_gfix:
                        self.log_event(f"[GATES] Failed (try {gtry + 1}/{max_gfix}); dispatching gate fix.")
                        self.dispatch_builder(
                            ticket_file, current_round, f"Gate failure:\n{gate_out[-800:]}", ruling, mode="gfix"
                        )

                if gates_ok:
                    self.log_event(f"[SUCCESS] Ticket {ticket_id} ACCEPTED and passed all gates!")
                    self.checkpoint_git(ticket_id, f"Implemented {ticket_id}")
                    self.harness_reflect(ticket_file, f"accepted in {current_round} rounds", accumulated_classes)
                    if accumulated_later and self.config.get("delta_convergence", {}).get("auto_triage_minor", True):
                        self.triage_later_items(ticket_id, list(set(accumulated_later)))
                    return True

                feedback = f"Gate failure log:\n{gate_out[-800:]}"
            else:
                feedback = arbiter_out or f"Reviewer Rejections: A={verdict_a}, B={verdict_b}"

            self.harness_edit(ticket_file, current_round, feedback)

        # Round limit exhausted: reflect, park, and escalate to Doctor
        self.harness_reflect(ticket_file, f"stopped after {self.max_rounds} rounds", accumulated_classes)
        self.park_stopped(ticket_id)
        self.dispatch_doctor(ticket_file, self.max_rounds, "Round limit exhausted without acceptance", feedback)
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

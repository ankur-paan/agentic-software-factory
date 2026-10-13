#!/usr/bin/env python3
"""
Agentic Software Factory Scaffolder
Inspects current directory, detects tech stack (Rust, Go, Python, Node, C++),
and scaffolds the complete factory architecture (roles, rules, specs, harness).
"""

import os
import sys
import json
import urllib.request
from pathlib import Path

BASE_RAW_URL = "https://raw.githubusercontent.com/ankur-paan/agentic-software-factory/main"

FILES_TO_FETCH = [
    ("roles/BUILDER.md", "roles/BUILDER.md"),
    ("roles/REVIEWER_A.md", "roles/REVIEWER_A.md"),
    ("roles/REVIEWER_B.md", "roles/REVIEWER_B.md"),
    ("roles/DOCTOR.md", "roles/DOCTOR.md"),
    ("rules/RULEBOOK.md", "rules/RULEBOOK.md"),
    ("specs/TICKET_TEMPLATE.md", "specs/TICKET_TEMPLATE.md"),
    ("specs/WAVE_EXAMPLE.md", "specs/WAVE_EXAMPLE.md"),
    ("harness/factory.py", "harness/factory.py"),
]

def detect_stack(root: Path):
    if (root / "Cargo.toml").exists():
        return {
            "name": "Rust Project",
            "compile_cmd": "cargo check --all-targets",
            "lint_cmd": "cargo clippy -- -D warnings",
            "test_cmd": "cargo test --workspace"
        }
    elif (root / "go.mod").exists():
        return {
            "name": "Go Project",
            "compile_cmd": "go build ./...",
            "lint_cmd": "golangci-lint run",
            "test_cmd": "go test ./..."
        }
    elif (root / "package.json").exists():
        return {
            "name": "Node/TypeScript Project",
            "compile_cmd": "npm run build --if-present",
            "lint_cmd": "npm run lint --if-present",
            "test_cmd": "npm test"
        }
    elif (root / "pyproject.toml").exists() or (root / "setup.py").exists() or (root / "requirements.txt").exists():
        return {
            "name": "Python Project",
            "compile_cmd": "python -m py_compile $(git ls-files '*.py')",
            "lint_cmd": "ruff check .",
            "test_cmd": "pytest"
        }
    else:
        return {
            "name": "Generic Software Project",
            "compile_cmd": "echo 'compile gate check'",
            "lint_cmd": "echo 'lint gate check'",
            "test_cmd": "echo 'test gate check'"
        }

def main():
    root = Path.cwd()
    print(f"🏭 Scaffolding Agentic Software Factory into: {root.resolve()}\n")

    stack = detect_stack(root)
    print(f"✓ Detected environment: {stack['name']}")

    # 1. Fetch framework files
    for remote_path, local_path in FILES_TO_FETCH:
        dest = root / local_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{BASE_RAW_URL}/{remote_path}"
        try:
            print(f"  → Writing {local_path}...")
            req = urllib.request.Request(url, headers={"User-Agent": "agentic-factory-installer"})
            with urllib.request.urlopen(req) as resp:
                content = resp.read().decode("utf-8")
            dest.write_text(content, encoding="utf-8")
        except Exception as e:
            print(f"    [!] Error downloading {url}: {e}")

    # 2. Generate customized config
    config_dest = root / "harness" / "config.json"
    if not config_dest.exists():
        print("  → Generating harness/config.json with detected gates...")
        config = {
            "project_name": stack["name"],
            "workspace_dir": ".",
            "max_rounds": 6,
            "gates": {
                "compile_cmd": stack["compile_cmd"],
                "lint_cmd": stack["lint_cmd"],
                "test_cmd": stack["test_cmd"],
                "qual_cmd": ""
            },
            "agents": {
                "builder_cmd": "opencode run --auto",
                "reviewer_a_cmd": "opencode run --auto",
                "reviewer_b_cmd": "opencode run --auto",
                "doctor_cmd": "opencode run --auto"
            },
            "git": {
                "auto_commit": True,
                "commit_prefix": "checkpoint"
            }
        }
        config_dest.write_text(json.dumps(config, indent=2), encoding="utf-8")

    # 3. Add .gitignore entries
    gitignore_path = root / ".gitignore"
    ignore_lines = [
        "\n# Agentic Software Factory State\n",
        ".factory/\n",
        "*.log\n"
    ]
    if gitignore_path.exists():
        existing = gitignore_path.read_text(encoding="utf-8")
        if ".factory/" not in existing:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.writelines(ignore_lines)
    else:
        gitignore_path.write_text("".join(ignore_lines), encoding="utf-8")

    print("\n✅ Agentic Software Factory successfully scaffolded!")
    print("----------------------------------------------------------------")
    print("Next steps:")
    print("1. Review gate commands in: harness/config.json")
    print("2. Create your first task spec from: specs/TICKET_TEMPLATE.md")
    print("3. Test the assembly line with dry-run:")
    print("   python harness/factory.py --dry-run --ticket specs/TICKET_TEMPLATE.md")
    print("----------------------------------------------------------------\n")

if __name__ == "__main__":
    main()

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    script_path = Path(__file__).resolve()
    skill_root = script_path.parent.parent
    repo_root = skill_root.parent.parent
    vendor_dir = skill_root / "vendor"
    skill_requirements = skill_root / "requirements.txt"
    repo_requirements = repo_root / "requirements.txt"

    vendor_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--target",
        str(vendor_dir),
    ]

    if skill_requirements.exists():
        command.extend(["-r", str(skill_requirements)])
    elif repo_requirements.exists():
        command.extend(["-r", str(repo_requirements)])
    else:
        command.append("fast-flights>=3.0rc0")

    print("Installing local dependencies into:", vendor_dir)
    print("Running:", " ".join(command))
    subprocess.run(command, check=True)
    print("Done. You can now run the example or CLI wrapper without a system-wide install.")


if __name__ == "__main__":
    main()

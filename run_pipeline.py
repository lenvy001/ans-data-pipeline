from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_script(script_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=script_path.parent.parent,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    scripts_dir = base_dir / "script_python"

    run_script(scripts_dir / "part_1_integracao.py")
    run_script(scripts_dir / "part_2_validacao.py")

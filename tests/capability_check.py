import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "capability-project"


def main():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["XDG_CACHE_HOME"] = str(FIXTURE / "build" / ".cache")
    command = [sys.executable, "-m", "makelove", *sys.argv[1:]]
    subprocess.run(command, cwd=FIXTURE, env=env, check=True)


if __name__ == "__main__":
    main()

"""Run DRAM latency-throughput sweeps in parallel."""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

folder = Path(__file__).resolve().parent
scripts_folder = folder / "scripts"
csv_folder = folder / "csv"
csv_folder.mkdir(exist_ok=True)
scripts = sorted(scripts_folder.glob("test_*.py"))


def run_script(script):
    print(f"Running {script.name}...", flush=True)
    subprocess.run([sys.executable, str(script)], cwd=csv_folder, check=True)


with ThreadPoolExecutor(max_workers=10) as executor:
    list(executor.map(run_script, scripts))

print("All sweeps completed; each DRAM script wrote its own test_<DRAM>.csv file in csv/.")

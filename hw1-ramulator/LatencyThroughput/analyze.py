"""Summarize and plot the per-DRAM latency-throughput sweeps."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

folder = Path(__file__).resolve().parent
csv_folder = folder / "csv"
plots_folder = folder / "plots"
plots_folder.mkdir(exist_ok=True)
summary = []

for csv_file in sorted(csv_folder.glob("test_*.csv")):
    with csv_file.open(newline="") as source:
        rows = [
            {
                "nop_counter": float(row["nop_counter"]),
                "latency_ns": float(row["latency_ns"]),
                "throughput_GBps": float(row["throughput_GBps"]),
            }
            for row in csv.DictReader(source)
        ]

    if not rows:
        continue

    dram = csv_file.stem[5:]
    unloaded = max(rows, key=lambda row: row["nop_counter"])
    peak = max(rows, key=lambda row: row["throughput_GBps"])

    summary.append({
        "dram": dram,
        "max_nop_counter": unloaded["nop_counter"],
        "unloaded_latency_ns": unloaded["latency_ns"],
        "max_throughput_GBps": peak["throughput_GBps"],
        "nop_counter_at_max_throughput": peak["nop_counter"],
    })

    points = sorted(rows, key=lambda row: row["throughput_GBps"])
    fig, ax = plt.subplots()
    ax.plot([row["throughput_GBps"] for row in points],
            [row["latency_ns"] for row in points], marker="o")
    ax.set(title=f"{dram}: latency vs. throughput",
           xlabel="Throughput (GB/s)", ylabel="Latency (ns)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_folder / f"{csv_file.stem}_latency_vs_throughput.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot([row["nop_counter"] for row in rows],
            [row["latency_ns"] for row in rows], marker="o")
    ax.set_xscale("log")
    ax.set(title=f"{dram}: nop counter vs. latency",
           xlabel="nop_counter (log scale)", ylabel="Latency (ns)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_folder / f"{csv_file.stem}_nop_vs_latency.png", dpi=150)
    plt.close(fig)

with (folder / "combined_summary.csv").open("w", newline="") as output:
    columns = [
        "dram", "max_nop_counter", "unloaded_latency_ns",
        "max_throughput_GBps", "nop_counter_at_max_throughput",
    ]
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(summary)

print(f"Summary saved in {folder}; plots saved in {plots_folder}")

"""Run READ-N for every DRAM configuration and export the results."""

import csv
import os
import time
from pathlib import Path

import readn_ddr3
import readn_ddr4
import readn_ddr5
import readn_gddr6
import readn_gddr7
import readn_hbm1
import readn_hbm2
import readn_hbm3
import readn_hbm4
import readn_lpddr5
import readn_lpddr6

NUM_STREAMS = [1, 4, 16]
DRAM_MODULES = [readn_ddr3, readn_ddr4, readn_ddr5, readn_gddr6, readn_gddr7,
                readn_hbm1, readn_hbm2, readn_hbm3, readn_hbm4, readn_lpddr5, readn_lpddr6]


def main():
    directory = Path(__file__).resolve().parent
    # The existing runners use trace paths relative to the working directory.
    os.chdir(directory)
    filename = directory / "readn_results.csv"
    start = time.time()

    with open(filename, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "dram", "num_streams",
            "controller_cycles", "simulated_time_ms", "avg_read_latency_cycles",
            "avg_read_latency_ns", "throughput_GBps", "read_requests", "write_requests",
            "row_hits", "row_misses", "row_conflicts", "row_hit_rate_pct", "run_time_s",
        ])
        writer.writeheader()

        for dram_module in DRAM_MODULES:
            for n in NUM_STREAMS:
                print(f"===== {dram_module.__name__}: READ-{n} =====")
                run_start = time.time()
                result = dram_module.read_n(n)
                result["run_time_s"] = time.time() - run_start
                writer.writerow(result)
                file.flush()
                print(f"Run time: {result['run_time_s']:.2f} seconds\n")

    print(f"Exported {len(DRAM_MODULES) * len(NUM_STREAMS)} results to {filename}")
    print(f"Total run time: {time.time() - start:.2f} seconds")


if __name__ == "__main__":
    main()

"""HBM4 latency probes under sequential background traffic."""
# NVIDIA Next Generation Vera Rubin Platform

import ramulator
import time
import csv
import os

NUM_CHANNELS = 32 # typical for HBM4
NUM_PSEUDO = 2 # typical, from spec

CACHELINE_SIZE = 32 # may replace later with cachelinesize

script_dir = os.path.dirname(os.path.abspath(__file__))

if CACHELINE_SIZE == 32:
    TRACE = os.path.join(script_dir, "read_1_32.trace")
else:
    TRACE = os.path.join(script_dir, "read_1_64.trace")

    # Configure the frontend: random probes plus sequential background traffic.
frontend = ramulator.frontend.LoadStoreTrace(
        clock_ratio=16, # has 1GHz channels, controller set to be 6.3*8 = 28.8GHz
        path = TRACE,                                                      # num_cols // internal_prefetch_size
    )

    # Configure
hbm4 = ramulator.dram.HBM4(
        org_preset="HBM4_32Gb_8Hi",
        timing_preset="HBM4_8000Mbps",
        #using default configs
    )

    # Configure the memory controller.
ctrl = ramulator.controller.HBM34(
        dram=hbm4,
        scheduler=ramulator.scheduler.FRFCFSRowHit(),
        refresh_manager=ramulator.refresh_manager.AllBank(),
        row_policy=ramulator.row_policy.ClosedCAP(), # closed more typical than open for HBM
        addr_mapper=ramulator.addr_mapper.RoBaRaCoCh(),
    )

    # Configure the memory system.
    # Pass-through mapping preserves the frontend's DRAM address vectors.
mem = ramulator.memory_system.GenericDRAM(
        clock_ratio=1,
        controllers=[ctrl] * NUM_CHANNELS * NUM_PSEUDO,
        channel_mapper=ramulator.channel_mapper.CacheLineInterleave(),
    )

 

    # Run the simulation.
sim = ramulator.Simulation(frontend, mem)
sim.run()

# Read and print stats
stats = sim.stats
if stats:
    print("\n" + "="*20 + " EXPERIMENT 2.2-1 RESULTS HBM1 " + "="*20)

    # total simulated cycles / time
    controllers = stats.get("memory_system", {}).get("controller", {})
    if isinstance(controllers, dict):
        controllers = [controllers]

    # controllers share a global clock, so read the cycle count from the first one
    sim_cycles = controllers[0].get("cycles", 0)
    print(f"Total Simulated Cycles:   {sim_cycles}")

    # average read latency
    frontend_stats = stats.get("frontend", {})
    avg_read_latency_cycles = frontend_stats.get("avg_read_latency", 0)
    # Note: If your build uses "avg_probe_latency", swap it here.
    # To convert to nanoseconds if needed, multiply by your DRAM's tCK clock period.
    print(f"Average Read Latency:     {avg_read_latency_cycles:.2f} cycles")

    # throughput/BW
    total_throughput_mbps = sum(c.get("total_throughput_MBps", 0) for c in controllers)
    total_throughput_gbps = total_throughput_mbps / 1000.0
    print(f"Achieved Throughput:      {total_throughput_gbps:.3f} GB/s")

    # row hit, miss, & conflict
    total_row_hits = sum(c.get("row_hits", 0) for c in controllers)
    total_row_misses = sum(c.get("row_misses", 0) for c in controllers)
    total_row_conflicts = sum(c.get("row_conflicts", 0) for c in controllers)

    total_row_accesses = total_row_hits + total_row_misses + total_row_conflicts
    row_hit_rate = (total_row_hits / total_row_accesses * 100.0) if total_row_accesses > 0 else 0.0

    print(f"\n--- Row-Buffer Statistics ---")
    print(f"Row Hits:                 {total_row_hits}")
    print(f"Row Misses:               {total_row_misses}")
    print(f"Row Conflicts:            {total_row_conflicts}")
    print(f"Calculated Row Hit Rate:  {row_hit_rate:.2f}%")
    print("="*66)
else:
    print("Error: No statistics were returned by the simulation runtime block.")
"""LPDDR5 latency probes under sequential background traffic."""
# use Qualcomm Snapdragon 8 Gen 1 for reference

import ramulator
import time
import csv
import os

NUM_CHANNELS = 2 # typical for LPDDR5
CACHELINE_SIZE = 32 # may replace later with cachelinesize

script_dir = os.path.dirname(os.path.abspath(__file__))

if CACHELINE_SIZE == 32:
    TRACE = os.path.join(script_dir, "copy_32.trace")
else:
    TRACE = os.path.join(script_dir, "copy_64.trace")


    # Configure the frontend: random probes plus sequential background traffic.
frontend = ramulator.frontend.LoadStoreTrace(
        clock_ratio=8, # 28.8 vs. 800M
        path = TRACE,
    )

    # Configure
lpddr5 = ramulator.dram.LPDDR5(
        org_preset="LPDDR5_8Gb_x16",
        timing_preset="LPDDR5_6400",
        #using default configs
    )

    # Configure the memory controller.
ctrl = ramulator.controller.LPDDR5(
        dram=lpddr5,
        scheduler=ramulator.scheduler.FRFCFSRowHit(),
        refresh_manager=ramulator.refresh_manager.AllBank(),
        row_policy=ramulator.row_policy.Open(), # somewhat more typical for LPDDR
        addr_mapper=ramulator.addr_mapper.RoBaRaCoCh(),
    )

    # Configure the memory system.
    # Pass-through mapping preserves the frontend's DRAM address vectors.
mem = ramulator.memory_system.GenericDRAM(
        clock_ratio=1,
        controllers=[ctrl] * NUM_CHANNELS,
        channel_mapper=ramulator.channel_mapper.CacheLineInterleave(),
    )



    # Run the simulation.
sim = ramulator.Simulation(frontend, mem)
sim.run()

# Read and print stats
stats = sim.stats
if stats:
    print("\n" + "="*20 + " EXPERIMENT 2.2-1 RESULTS LPDDR5 " + "="*20)

    # total simulated cycles / time
    controllers = stats.get("memory_system", {}).get("controller", {})
    if isinstance(controllers, dict):
        controllers = [controllers]

    # controllers share a global clock, so read the cycle count from the first one
    sim_cycles = controllers[0].get("cycles", 0)
    print(f"Total Simulated Cycles:   {sim_cycles}")

    # average read latency
    frontend_stats = stats.get("frontend", {})
    avg_read_latency_cycles = controllers[0].get("avg_read_latency", 0)
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
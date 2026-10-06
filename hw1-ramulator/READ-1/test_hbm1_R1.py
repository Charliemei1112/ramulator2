"""DDR5 latency probes under sequential background traffic."""
# based on specs of AMD Radeon R9 Fury series

import ramulator
import os

NUM_CHANNELS = 8 # R9 Fury uses 4 stacks of 8 channels
CACHELINE_SIZE = 32 # may replace later with cachelinesize

script_dir = os.path.dirname(os.path.abspath(__file__))

if CACHELINE_SIZE == 32:
    TRACE = os.path.join(script_dir, "read_1_32.trace")
else:
    TRACE = os.path.join(script_dir, "read_1_64.trace")

# Configure the frontend: random probes plus sequential background traffic.
frontend = ramulator.frontend.LoadStoreTrace(
    clock_ratio=16, # standard from test
    path = TRACE,
)

# Configure
hbm1 = ramulator.dram.HBM1(
    org_preset="HBM1_2Gb",
    timing_preset="HBM1_1Gbps",
    #using default configs
)

# Configure the memory controller.
ctrl = ramulator.controller.HBM12(
    dram=hbm1,
    scheduler=ramulator.scheduler.FRFCFSRowHit(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.Open(), # closed mor typical than open for HBM
    addr_mapper=ramulator.addr_mapper.RoBaRaCoCh(), # avoid seg fault
)

# Configure the memory system.
# Pass-through mapping preserves the frontend's DRAM address vectors.
mem = ramulator.memory_system.GenericDRAM(
    clock_ratio=1,
    controllers=[ctrl] * NUM_CHANNELS,
    channel_mapper=ramulator.channel_mapper.CacheLineInterleave(), #avoid seg fault
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
    # average read latency
    # Ramulator 2 profiles average read latency directly on the controller level
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
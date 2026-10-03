"""DDR3 latency probes under sequential background traffic, with refresh enabled."""

import ramulator
import time
import csv

RANK = 1
# BANK = 8
NUM_CHANNELS = 1  # One 64-bit channel.

# Configure the frontend: random probes plus sequential background traffic.
frontend = ramulator.frontend.LoadStoreTrace(
    clock_ratio=8,
    path="./read_4_64B.trace",
)

# Configure DDR3.
ddr3 = ramulator.dram.DDR3(
    org_preset="DDR3_2Gb_x8",
    timing_preset="DDR3_1600H",
    rank=RANK,
)

# Configure the memory controller.
ctrl = ramulator.controller.GenericDDR(
    dram=ddr3,
    scheduler=ramulator.scheduler.FRFCFSRowHit(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.Open(),
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

# Read statistics.
stats = sim.stats
frontend_stats = stats["frontend"]
# Controller stats are under memory_system → controller
ctrl_stats = stats["memory_system"]["controller"]

_, timing = ddr3.resolve()
clock_period_ns = timing["tCK_ps"] / 1000.0

simulated_time_ms = ctrl_stats["cycles"] * clock_period_ns / 1_000_000
read_latency_ns = ctrl_stats["avg_read_latency"] * clock_period_ns
throughput_gbps = ctrl_stats["total_throughput_MBps"] / 1000.0

print(f"Controller cycles:     {ctrl_stats['cycles']}")
print(f"Simulated time:        {simulated_time_ms:.3f} ms")
print(f"Avg read latency:      {ctrl_stats['avg_read_latency']:.1f} cycles")
print(f"Avg read latency:      {read_latency_ns:.2f} ns")
print(f"Total throughput:      {throughput_gbps:.3f} GB/s")
print(f"Read requests:         {ctrl_stats['num_read_reqs']}")
print(f"Write requests:        {ctrl_stats['num_write_reqs']}")
print(f"Row hits:              {ctrl_stats['row_hits']}")
print(f"Row misses:            {ctrl_stats['row_misses']}")
print(f"Row conflicts:         {ctrl_stats['row_conflicts']}")

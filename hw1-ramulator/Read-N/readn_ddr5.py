"""DDR5 latency probes under sequential background traffic, with refresh enabled."""

import ramulator
import time
import csv
import cache_line_size
import readn_dram as dram

NUM_CHANNELS = 2
bytes = cache_line_size.CACHE_LINE_SIZE["DDR5"]
print(bytes)

def read_n(n=1):

    file_path = f"./read_{n}_{bytes}B.trace"
    print(file_path)

    # Configure the frontend: random probes plus sequential background traffic.
    frontend = ramulator.frontend.LoadStoreTrace(
        clock_ratio=8,
        path=file_path,
    )

    ddr5 = dram.ddr5

    # Configure the memory controller.
    ctrl = ramulator.controller.GenericDDR(
        dram=ddr5,
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
    controllers = stats["memory_system"]["controller"]

    if isinstance(controllers, dict):
        controllers = [controllers]

    _, timing = ddr5.resolve()
    clock_period_ns = timing["tCK_ps"] / 1000.0 

    # Controllers run concurrently, so do not sum their cycles.
    cycles = max(ctrl["cycles"] for ctrl in controllers)
    simulated_time_ms = cycles * clock_period_ns / 1_000_000

    # Weight average latency by each controller's read-request count.
    read_requests = sum(ctrl["num_read_reqs"] for ctrl in controllers)
    write_requests = sum(ctrl["num_write_reqs"] for ctrl in controllers)

    read_latency_cycles = sum(ctrl["avg_read_latency"] * ctrl["num_read_reqs"] for ctrl in controllers) / read_requests
    read_latency_ns = read_latency_cycles * clock_period_ns

    throughput_gbps = sum(
        ctrl["total_throughput_MBps"] for ctrl in controllers) / 1000.0

    row_hits = sum(ctrl["row_hits"] for ctrl in controllers)
    row_misses = sum(ctrl["row_misses"] for ctrl in controllers)
    row_conflicts = sum(ctrl["row_conflicts"] for ctrl in controllers)
    row_access = row_hits + row_misses + row_conflicts
    row_hit_rate = row_hits * 100 / row_access

    print(f"Controller cycles:     {cycles}")
    print(f"Simulated time:        {simulated_time_ms:.3f} ms")
    print(f"Avg read latency:      {read_latency_cycles:.1f} cycles")
    print(f"Avg read latency:      {read_latency_ns:.2f} ns")
    print(f"Total throughput:      {throughput_gbps:.3f} GB/s")
    print(f"Read requests:         {read_requests}")
    print(f"Write requests:        {write_requests}")
    print(f"Row hits:              {row_hits}")
    print(f"Row misses:            {row_misses}")
    print(f"Row conflicts:         {row_conflicts}")
    print(f"Row Hit Rate:          {row_hit_rate:.3f}%")

    return {
        "dram": "DDR5",
        "num_streams": n,
        "controller_cycles": cycles,
        "simulated_time_ms": simulated_time_ms,
        "avg_read_latency_cycles": read_latency_cycles,
        "avg_read_latency_ns": read_latency_ns,
        "throughput_GBps": throughput_gbps,
        "read_requests": read_requests,
        "write_requests": write_requests,
        "row_hits": row_hits,
        "row_misses": row_misses,
        "row_conflicts": row_conflicts,
        "row_hit_rate_pct": row_hit_rate,
    }

if __name__ == "__main__":
    read_n(1)
    read_n(4)
    read_n(16)
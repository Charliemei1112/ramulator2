"""GDDR7 latency probes under sequential background traffic."""
# NVIDIA GeForce RTX 5070 Ti

import ramulator
import time
import csv

NOP_COUNTER_VALUES = [1,2,3,4,5,6,7,8,9,10,12,15,20,50,100,500,1000,10000,100000]

PROBE_REQUESTS = 10_000
WARMUP_CYCLES = 10_000
BANK = 16
NUM_CHANNELS = 32  # 32 × 8-bit channels = 256-bit interface.
MIN_REFRESH_INTERVALS = 100


def sweep(nop_counter=1):
    print(f"===== nop_counter={nop_counter} =====")

    # Configure the frontend: random probes plus sequential background traffic.
    frontend = ramulator.frontend.LatencyThroughputTrace(
        clock_ratio=16,  # Injection headroom for 32 channels; verify saturation.
        nop_counter=nop_counter,  # Sweeping Variable
        latency_sample_count=PROBE_REQUESTS,
        warmup_cycles=WARMUP_CYCLES,
        stream_cls=64,
        stagger_stream_rows=True,

        # Layout for GDDR7_16Gb_x8
        # Hierarchy: Channel, Bank, Row, Column.
        addr_vec_size=4,
        bank_positions=[1, 0],                   # Bank, Channel
        bank_counts=[BANK, NUM_CHANNELS],
        total_bank_units=BANK * NUM_CHANNELS,    # BANK * NUM_CHANNELS
        row_pos=2,
        col_pos=3,
        num_rows=1 << 14,                        # Number of rows: 2^14 = 16384
        num_cols=(1 << 6) << 5,                  # Number of columns: 2048
        internal_prefetch_size=32,               # Defined in class GDDR7
        num_cls=64,                              # num_cols // internal_prefetch_size
    )

    # Configure GDDR7.
    gddr7 = ramulator.dram.GDDR7(
        org_preset="GDDR7_16Gb_x8",        # 16Gb device, four 8-bit channels
        timing_preset="GDDR7_28000_PAM3",  # 28 Gb/s; preset command timings
    )

    # Configure the memory controller.
    ctrl = ramulator.controller.GDDR7(
        dram=gddr7,
        scheduler=ramulator.scheduler.FRFCFSRowHit(),
        refresh_manager=ramulator.refresh_manager.AllBank(),
        row_policy=ramulator.row_policy.Open(),
        addr_mapper=ramulator.addr_mapper.PassThroughAddrMapper(),
    )

    # Configure the memory system.
    # Pass-through mapping preserves the frontend's DRAM address vectors.
    mem = ramulator.memory_system.GenericDRAM(
        clock_ratio=1,
        controllers=[ctrl] * NUM_CHANNELS,
        channel_mapper=ramulator.channel_mapper.PassThroughChannelMapper(),
    )

    # Run the simulation.
    sim = ramulator.Simulation(frontend, mem)
    sim.run()

    # Read and print statistics.
    stats = sim.stats
    frontend_stats = stats["frontend"]
    controllers = stats["memory_system"]["controller"]

    if isinstance(controllers, dict):
        controllers = [controllers]

    _, timing = gddr7.resolve()
    clock_period_ns = timing["tCK_ps"] / 1000.0

    # Average latency of the random read probes.
    latency_cycles = frontend_stats["avg_probe_latency"]
    latency_ns = latency_cycles * clock_period_ns

    # Aggregate achieved throughput across all modeled channels.
    throughput_gbps = sum(controller["total_throughput_MBps"] for controller in controllers) / 1000.0

    # Controllers share the same clock; elapsed cycles are not summed.
    cycles = controllers[0]["cycles"]
    measured_time_ms = cycles * clock_period_ns / 1_000_000

    print(f"Probe latency:            {latency_ns:.2f} ns")
    print(f"Total throughput:         {throughput_gbps:.3f} GB/s")

    # Verify refresh coverage separately for every channel.
    refresh_intervals = []

    for channel, controller in enumerate(controllers):
        intervals = controller["cycles"] / timing["nREFI"]
        refresh_intervals.append(intervals)
        print(f"Channel {channel}: {int(intervals)} refresh intervals")

        if intervals < MIN_REFRESH_INTERVALS:
            raise RuntimeError(f"Channel {channel}: only {intervals:.1f} refresh intervals. Increase PROBE_REQUESTS to cover at least {MIN_REFRESH_INTERVALS}.")

    return {"nop_counter": nop_counter,
            "latency_ns": latency_ns,
            "throughput_GBps": throughput_gbps,
            "measured_time_ms": measured_time_ms,
            "min_refresh_intervals": min(refresh_intervals),
            }


def export_csv(results, filename):
    with open(filename, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["nop_counter", "latency_ns", "throughput_GBps", "measured_time_ms", "min_refresh_intervals"])
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    results = []
    sweep_start = time.time()

    for nop_counter in NOP_COUNTER_VALUES:
        run_start = time.time()
        result = sweep(nop_counter)

        run_end = time.time()
        results.append(result)
        print(f"Run time:                 {run_end - run_start:.2f} seconds\n")

    export_csv(results, "test_gddr7.csv")

    sweep_end = time.time()
    print(f"\nTotal sweep time: {sweep_end - sweep_start:.2f} seconds\n")
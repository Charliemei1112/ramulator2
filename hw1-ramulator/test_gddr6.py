"""GDDR6 latency probes under sequential background traffic."""

import ramulator
import time
import csv

NOP_COUNTER_VALUES = [1,2,3,4,5,6,7,8,9,10,12,15,20,50,100,500,1000,10000,100000]

PROBE_REQUESTS = 10_000
WARMUP_CYCLES = 10_000
NUM_CHANNELS = 8  # 128-bit, Nvidia GTX 4060
MIN_REFRESH_INTERVALS = 100

def sweep(nop_counter=1):
    print(f"===== nop_counter={nop_counter} =====")

    # Configure the frontend: random probes plus sequential background traffic.
    frontend = ramulator.frontend.LatencyThroughputTrace(
        clock_ratio=8,
        nop_counter=nop_counter,  # Sweeping Variable
        latency_sample_count=PROBE_REQUESTS,
        warmup_cycles=WARMUP_CYCLES,
        stream_cls=64,
        stagger_stream_rows=True,

        # Layout for GDDR6_8Gb_x16
        # Hierarchy: Channel, BankGroup, Bank, Row, Column.
        addr_vec_size=5,
        bank_positions=[2, 1, 0],                 # Bank, BankGroup, Channel
        bank_counts=[4, 4, NUM_CHANNELS],         # Bank, BankGroup, Channel in org_preset
        total_bank_units=4 * 4 * NUM_CHANNELS,    # Total banks across channels
        row_pos=3,
        col_pos=4,
        num_rows=1 << 14,                         # Number of rows: 2^14 = 16384
        num_cols=1 << 10,                         # Number of columns: 2^10 = 1024
        internal_prefetch_size=16,               # Defined in class GDDR6
        num_cls=64,                              # num_cols // internal_prefetch_size
    )

    # Configure GDDR6.
    gddr6 = ramulator.dram.GDDR6(
        org_preset="GDDR6_8Gb_x16",                 # 8Gb device, two 16-bit channels
        timing_preset="GDDR6_14000_1350mV_double",  # 14 Gb/s, 1.35 V
    )

    # Configure the memory controller.
    ctrl = ramulator.controller.GenericDDR(
        dram=gddr6,
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

    _, timing = gddr6.resolve()
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

    export_csv(results, "test_gddr6.csv")

    sweep_end = time.time()
    print(f"\nTotal sweep time: {sweep_end - sweep_start:.2f} seconds\n")
"""DDR4 latency probes under sequential background traffic, with refresh enabled."""

import ramulator
import time
import csv

NOP_COUNTER_VALUES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 50, 100, 500, 1000, 10000, 100000]

PROBE_REQUESTS = 20_000
WARMUP_CYCLES = 10_000
MIN_REFRESH_INTERVALS = 100

RANK = 1
NUM_CHANNELS = 1  # One 64-bit channel.


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

        # Layout for DDR4_16Gb_x8, one rank per channel.
        # Level: Channel, Rank, BankGroup, Bank, Row, Column.
        addr_vec_size=6,
        bank_positions=[1, 3, 2, 0],                    # Rank, Bank, BankGroup, Channel
        bank_counts=[RANK, 4, 4, NUM_CHANNELS],         # rank, bank, bankgroup, channel in org_preset
        total_bank_units=RANK * 4 * 4 * NUM_CHANNELS,   # total banks: rank * bank * bankgroup * num_channels
        row_pos=4,
        col_pos=5,
        num_rows=1 << 17,                               # 131072 rows
        num_cols=1 << 10,                               # number of columns: 2^10 = 1024
        internal_prefetch_size=8,                       # Defined in class DDR4
        num_cls=128,                                   # 1024 // 8 = 128
    )

    # Configure DDR4.
    ddr4 = ramulator.dram.DDR4(
        org_preset="DDR4_16Gb_x8",
        timing_preset="DDR4_3200AA",
        rank=RANK,
    )

    # Configure the memory controller.
    ctrl = ramulator.controller.GenericDDR(
        dram=ddr4,
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

    # Read statistics.
    stats = sim.stats
    frontend_stats = stats["frontend"]
    controllers = stats["memory_system"]["controller"]

    if isinstance(controllers, dict):
        controllers = [controllers]

    _, timing = ddr4.resolve()
    clock_period_ns = timing["tCK_ps"] / 1000.0

    latency_cycles = frontend_stats["avg_probe_latency"]
    latency_ns = latency_cycles * clock_period_ns

    throughput_gbps = sum(controller["total_throughput_MBps"] for controller in controllers) / 1000.0

    # Controller cycles already exclude warmup in this implementation.
    cycles = controllers[0]["cycles"]
    measured_time_ms = cycles * clock_period_ns / 1_000_000

    # print(f"Controller cycles:        {cycles}")
    # print(f"Measured simulated time:  {measured_time_ms:.3f} ms")
    # print(f"Completed latency probes: "f"{frontend_stats['probe_requests_completed']}")
    # print(f"Probe latency:            {latency_cycles:.2f} cycles")
    print(f"Probe latency:            {latency_ns:.2f} ns")
    print(f"Total throughput:         {throughput_gbps:.3f} GB/s")
    # print(f"Background requests sent: {frontend_stats['streaming_requests_sent']}")

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

    export_csv(results, "test_ddr4.csv")

    sweep_end = time.time()
    print(f"\nTotal sweep time: {sweep_end - sweep_start:.2f} seconds\n")

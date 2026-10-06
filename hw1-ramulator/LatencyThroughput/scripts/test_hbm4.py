"""HBM4 latency probes under sequential background traffic."""
# NVIDIA Next Generation Vera Rubin Platform

import ramulator
import time
import csv

NOP_COUNTER_VALUES = [1,2,3,4,5,6,7,8,9,10,12,15,20,50,100,500,1000,10000,100000]
PROBE_REQUESTS = 20_000
WARMUP_CYCLES = 10_000
BANK = 8
BANKGROUP = 2
NUM_CHANNELS = 32 # typical for HBM4
NUM_PSEUDO = 2 # typical, from spec
NUM_SIDS = 2 #from spec

MIN_REFRESH_INTERVALS = 100

def sweep(nop_counter=1):
    print(f"===== nop_counter={nop_counter} =====")

    # Configure the frontend: random probes plus sequential background traffic.
    frontend = ramulator.frontend.LatencyThroughputTrace(
        clock_ratio=16, # has 1GHz channels, controller set to be 6.3*8 = 28.8GHz
        nop_counter=nop_counter,  # Sweeping Variable
    
        latency_sample_count=PROBE_REQUESTS,
        warmup_cycles=WARMUP_CYCLES,
        stream_cls=32,
        stagger_stream_rows=True,

        # Layout for HBM4
        # Hierarchy: Channel, PseudoChannel, Sid, BankGroup, Bank, Row, Column.
        addr_vec_size=7,
        bank_positions=[4, 3, 2, 1, 0],                                     # Bank, BankGroup, Sid, PseudoChannel, Channel
        bank_counts=[BANK, BANKGROUP, NUM_SIDS, NUM_PSEUDO, NUM_CHANNELS],             # bank, bankgroup, sid, pseudochannels, channel in org_preset
        total_bank_units=BANK * BANKGROUP * NUM_CHANNELS * NUM_PSEUDO * NUM_SIDS,      # total banks: bank * bankgroup * num_channels * num_pseudo * num_sids
        row_pos=5,
        col_pos=6,
        num_rows=1<<14,                                                     # number of rows 2^14 = 16384
        num_cols=(1<<5) << 3,                                               # number of cols (2^5)*8 = 256
        internal_prefetch_size=8,                                           # internal prefetch size, defined in class
        num_cls=32,                                                         # num_cols // internal_prefetch_size
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
        addr_mapper=ramulator.addr_mapper.PassThroughAddrMapper(),
    )

    # Configure the memory system.
    # Pass-through mapping preserves the frontend's DRAM address vectors.
    mem = ramulator.memory_system.GenericDRAM(
        clock_ratio=1,
        controllers=[ctrl] * NUM_CHANNELS * NUM_PSEUDO,
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

    # Serialized timings use simulator ticks; HBM4 ticks are half a CK cycle.
    timing = dict(zip(hbm4.timing_params, hbm4.to_config()["timing"]))
    clock_period_ns = timing["tCK_ps"] / 1000.0

    # Average latency of the random read probes.
    latency_cycles = frontend_stats["avg_probe_latency"]
    latency_ns = latency_cycles * clock_period_ns

    # Aggregate achieved throughput across all modeled channels.
    throughput_gbps = sum(controller["total_throughput_MBps"] for controller in controllers) / 1000.0

    # Controllers share the same clock; elapsed cycles are not summed.
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

    export_csv(results, "test_hbm4.csv")

    sweep_end = time.time()
    print(f"\nTotal sweep time: {sweep_end - sweep_start:.2f} seconds\n")

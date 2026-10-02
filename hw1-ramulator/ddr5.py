"""DDR5 latency probes under sequential background traffic."""

import ramulator

NOP_COUNTER = 1       # Larger values reduce background traffic pressure.
READ_RATIO = 100      # Background traffic: 100% reads.
PROBE_REQUESTS = 10_000
WARMUP_CYCLES = 10_000

# Configure the frontend: random probes plus sequential background traffic.
frontend = ramulator.frontend.LatencyThroughputTrace(
    clock_ratio=8,
    nop_counter=NOP_COUNTER,
    read_ratio=READ_RATIO,
    latency_measure_mode="random-probe",
    latency_sample_count=PROBE_REQUESTS,
    streaming_only=False,
    warmup_cycles=WARMUP_CYCLES,
    seed=12345,
    stream_cls=64,
    stagger_stream_rows=True,

    # Layout for DDR5_16Gb_x8, rank=1.
    # Hierarchy: Channel, Rank, BankGroup, Bank, Row, Column.
    addr_vec_size=6,
    bank_positions=[1, 3, 2],     # Rank, Bank, BankGroup; BG cycles fastest.
    bank_counts=[1, 4, 8],
    total_bank_units=32,
    row_pos=4,
    col_pos=5,
    num_rows=1 << 16,
    num_cols=1 << 10,
    internal_prefetch_size=16,
    num_cls=64,
)

# Configure DDR5.
ddr5 = ramulator.dram.DDR5(
    org_preset="DDR5_16Gb_x8",
    timing_preset="DDR5_4800AN",
    rank=1,
)

# Configure the memory controller.
ctrl = ramulator.controller.GenericDDR(
    dram=ddr5,
    scheduler=ramulator.scheduler.FRFCFSRowHit(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.Open(),
    addr_mapper=ramulator.addr_mapper.PassThroughAddrMapper(),
)

# Configure the memory system.
# Pass-through mapping preserves the frontend's DRAM address vectors.
mem = ramulator.memory_system.GenericDRAM(
    clock_ratio=1,
    controllers=[ctrl],
    channel_mapper=ramulator.channel_mapper.PassThroughChannelMapper(),
)

# Run the simulation.
sim = ramulator.Simulation(frontend, mem)
sim.run()

# Read and print statistics.
stats = sim.stats
if stats:
    frontend_stats = stats["frontend"]
    controller_stats = stats["memory_system"]["controller"]
    _, timing = ddr5.resolve()

    probe_latency_cycles = frontend_stats["avg_probe_latency"]
    probe_latency_ns = probe_latency_cycles * timing["tCK_ps"] / 1000.0
    throughput_gbps = controller_stats["total_throughput_MBps"] / 1000.0

    print(f"Controller cycles:        {controller_stats['cycles']}")
    print(f"Completed latency probes: {frontend_stats['probe_requests_completed']}")
    print(f"Probe latency:            {probe_latency_cycles:.2f} cycles")
    print(f"Probe latency:            {probe_latency_ns:.2f} ns")
    print(f"Total throughput:         {throughput_gbps:.3f} GB/s")
    print(f"Background requests sent: {frontend_stats['streaming_requests_sent']}")
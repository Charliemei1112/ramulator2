"""DDR4 latency probes under sequential background traffic."""

import ramulator

NOP_COUNTER = 1       # Larger values reduce background traffic pressure.
# READ_RATIO = 100      # Background traffic: 100% reads.
PROBE_REQUESTS = 10_000
WARMUP_CYCLES = 10_000
RANK = 2 # rank=1: single-rank DDR5, rank=2: dual-rank DDR5
NUM_CHANNELS = 2 # dual-channel DDR5

# Configure the frontend: random probes plus sequential background traffic.
frontend = ramulator.frontend.LatencyThroughputTrace(
    clock_ratio=8,
    nop_counter=NOP_COUNTER,  # Sweeping Variable
    latency_sample_count=PROBE_REQUESTS,
    warmup_cycles=WARMUP_CYCLES,
    stream_cls=64,
    stagger_stream_rows=True,

    # Layout for DDR5_16Gb_x8, rank=1.
    # Hierarchy: Channel, Rank, BankGroup, Bank, Row, Column.
    addr_vec_size=6,
    bank_positions=[1, 3, 2, 0],     # Rank, Bank, BankGroup, Channel
    bank_counts=[RANK, 4, 4, NUM_CHANNELS],        # rank, bank, bankgroup, channel in org_preset
    total_bank_units=RANK * 4 * 4 * NUM_CHANNELS,          # total banks: rank * bank * bankgroup * num_channels
    row_pos=4,
    col_pos=5,
    num_rows=1 << 17,             # number of rows： 2^17 = 131072
    num_cols=1 << 10,             # number of columns: 2^10 = 1024
    internal_prefetch_size=8,    # internal prefetch size: 16, defined in class DDR4
    num_cls=128,                   # num_cols // internal_prefetch_size = 1024 // 8 = 128
)

# Configure DDR5.
ddr4 = ramulator.dram.DDR4(
    org_preset="DDR4_16Gb_x8",      # 2GB chip * 8
    timing_preset="DDR4_3200AA",    # 3200MT/s
    rank=RANK,                      # Dual-Rank

    # Product-specific Configuration
    rate=3600,
    tCK_ps=556,
    nCL=16,
    nRAS=42,
    nRC=64,
    # Verbose=True,
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

# Read and print statistics.
stats = sim.stats
if stats:
    frontend_stats = stats["frontend"]
    controllers = stats["memory_system"]["controller"]

    # One controller returns a dictionary; multiple controllers return a list.
    if isinstance(controllers, dict):
        controllers = [controllers]

    _, timing = ddr4.resolve()
    clock_period_ns = timing["tCK_ps"] / 1000.0

    # Average latency of the random read probes.
    latency_cycles = frontend_stats["avg_probe_latency"]
    latency_ns = latency_cycles * clock_period_ns

    # Aggregate achieved throughput across all modeled channels.
    throughput_gbps = sum(
        controller["total_throughput_MBps"]
        for controller in controllers
    ) / 1000.0

    # Controllers share the same clock; elapsed cycles are not summed.
    cycles = controllers[0]["cycles"]

    print(f"Controller cycles:        {cycles}")
    print(f"Completed latency probes: {frontend_stats['probe_requests_completed']}")
    print(f"Probe latency:            {latency_cycles:.2f} cycles")
    print(f"Probe latency:            {latency_ns:.2f} ns")
    print(f"Total throughput:         {throughput_gbps:.3f} GB/s")
    print(f"Background requests sent: {frontend_stats['streaming_requests_sent']}")
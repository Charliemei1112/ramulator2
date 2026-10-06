"""DDR5 latency probes under sequential background traffic."""
# use Qualcomm Snapdragon 8 Elite Gen 6 for reference

import ramulator

NOP_COUNTER = 120       # Larger values reduce background traffic pressure.
# READ_RATIO = 100      # Background traffic: 100% reads.
PROBE_REQUESTS = 10_000
WARMUP_CYCLES = 10_000
NUM_CHANNELS = 2 # typical for LPDDR6
NUM_RANK = 1
NUM_BANK = 4
NUM_BG = 4

# Configure the frontend: random probes plus sequential background traffic.
frontend = ramulator.frontend.LatencyThroughputTrace(
    clock_ratio=11, # 2.7G vs 28.8
    nop_counter=NOP_COUNTER,  # Sweeping Variable
    
    latency_sample_count=PROBE_REQUESTS,
    warmup_cycles=WARMUP_CYCLES,
    stream_cls=64,
    stagger_stream_rows=True,

    # Layout for LPDDR6
    # Hierarchy: Channel, Rank, BankGroup, Bank, Row, Column.
    addr_vec_size=6,
    bank_positions=[3, 2, 1, 0],     # Bank, BankGroup, Rank, Channel
    bank_counts=[NUM_BANK, NUM_BG, NUM_RANK, NUM_CHANNELS],        # bank, bankgroup, rank, channel in org_preset
    total_bank_units=NUM_BG * NUM_BANK * NUM_CHANNELS * NUM_RANK,          # total banks: rank * bank * bankgroup * num_channels
    row_pos=4,
    col_pos=5,
    num_rows=1<<16,             # number of rows 2^14 = 16384
    num_cols=1<<10,             # number of cols (2^5)*8 = 256
    internal_prefetch_size=16,    # internal prefetch size, defined in class
    num_cls=64,                   # num_cols / internal_prefetch_size
)

# Configure
lpddr6 = ramulator.dram.LPDDR6(
    org_preset="LPDDR6_16Gb_x12",
    timing_preset="LPDDR6_10667_BL24",
    #using default configs
)

# Configure the memory controller.
ctrl = ramulator.controller.LPDDR6(
    dram=lpddr6,
    scheduler=ramulator.scheduler.FRFCFSRowHit(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.ClosedCAP(), # somewhat more typical for LPDDR
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

    _, timing = lpddr6.resolve()
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
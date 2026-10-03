"""DDR5 latency probes under sequential background traffic."""
# use NVIDIA H100 GPU for reference

import ramulator

NOP_COUNTER = 1       # Larger values reduce background traffic pressure.
# READ_RATIO = 100      # Background traffic: 100% reads.
PROBE_REQUESTS = 10_000
WARMUP_CYCLES = 10_000
NUM_CHANNELS = 16 # typical for HBM3
NUM_PSEUDO = 2 # typical, from spec
NUM_SIDS = 2 #from spec

# Configure the frontend: random probes plus sequential background traffic.
frontend = ramulator.frontend.LatencyThroughputTrace(
    clock_ratio=15, # has 2GHz channels, controller set to be 6.3*8 = 28.8GHz
    nop_counter=NOP_COUNTER,  # Sweeping Variable
    
    latency_sample_count=PROBE_REQUESTS,
    warmup_cycles=WARMUP_CYCLES,
    stream_cls=64,
    stagger_stream_rows=True,

    # Layout for HBM3
    # Hierarchy: Channel, PseudoChannel, Sid, BankGroup, Bank, Row, Column.
    addr_vec_size=7,
    bank_positions=[4, 3, 2, 1, 0],     # Bank, BankGroup, Sid, PseudoChannel, Channel
    bank_counts=[2, 4, NUM_SIDS, NUM_PSEUDO, NUM_CHANNELS],        # bank, bankgroup, sid, pseudochannels, channel in org_preset
    total_bank_units=4 * 4 * NUM_CHANNELS * NUM_PSEUDO * NUM_SIDS,          # total banks: bank * bankgroup * num_channels * num_pseudo * num_sids
    row_pos=5,
    col_pos=6,
    num_rows=1<<14,             # number of rows 2^14 = 16384
    num_cols=(1<<5) << 3,             # number of cols (2^5)*8 = 256
    internal_prefetch_size=8,    # internal prefetch size, defined in class
    num_cls=32,                   # num_cols / internal_prefetch_size
)

# Configure
hbm3 = ramulator.dram.HBM3(
    org_preset="HBM3_16Gb_8hi",
    timing_preset="HBM3_6400Mbps",
    #using default configs
)

# Configure the memory controller.
ctrl = ramulator.controller.HBM34(
    dram=hbm3,
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
if stats:
    frontend_stats = stats["frontend"]
    controllers = stats["memory_system"]["controller"]

    # One controller returns a dictionary; multiple controllers return a list.
    if isinstance(controllers, dict):
        controllers = [controllers]

    _, timing = hbm3.resolve()
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
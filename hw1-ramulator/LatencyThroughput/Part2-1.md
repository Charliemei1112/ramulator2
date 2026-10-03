### PARAMETERS

Latency_throughouput validatino workload:
    random-access, pointer-chasing-like foreground 
    sequential streaming background accesses

DRAM Models: 
GenericDDR: DDR3, DDR4, DDR5, GDDR6, GDDR7, 
LPDDR5: LPDDR5, LPDDR6, 
HBM12: HBM1, HBM2, 
HBM34: HBM3, HBM4

Traffic Sequence:
LatencyThroughputTrace for frontend

Evaluation:
1) Unloaded pointer-chase latency
2) Maximum sustained background throughput or bandwidth
3) The approximate knee of the latency–throughput curve
4) How latency changes as the memory system approaches saturation

Explain why sequential streaming background accesses are useful when measuring the
throughput capability of a DRAM organization. In particular, discuss why this experiment
is different from generating independent random accesses as the background traffic.
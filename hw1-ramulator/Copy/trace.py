CACHELINE_SIZE_64 = 64  
CACHELINE_SIZE_32 = 32
NUM_REQUESTS = 1000000  # as specified by spec
TRACE_FILE_32 = "copy_32.trace"
TRACE_FILE_64 = "copy_64.trace"

# Each iteration writes 1 LD and 1 ST, so we run for exactly half the total requests
ITERATIONS = NUM_REQUESTS // 2  

# Separate starting addresses to prevent Array A and B from overwriting each other
START_B = 0
START_A = 40000000  # Offset by 1GB in hex to keep arrays in different DRAM rows

with open(TRACE_FILE_32, "w") as f:
    addr_b = START_B
    addr_a = START_A
    for i in range(ITERATIONS):
        f.write(f"LD {addr_b}\n")
        f.write(f"ST {addr_a}\n")
        addr_b += CACHELINE_SIZE_32
        addr_a += CACHELINE_SIZE_32

with open(TRACE_FILE_64, "w") as f:
    addr_b = START_B
    addr_a = START_A
    for i in range(ITERATIONS):
        f.write(f"LD {addr_b}\n")
        f.write(f"ST {addr_a}\n")
        addr_b += CACHELINE_SIZE_64
        addr_a += CACHELINE_SIZE_64

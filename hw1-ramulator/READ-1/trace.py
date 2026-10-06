CACHELINE_SIZE_32 = 32
CACHELINE_SIZE_64 = 64  
NUM_REQUESTS = 1000000  # as specified by spec
TRACE_FILE_32 = "read_1_32.trace"
TRACE_FILE_64 = "read_1_64.trace"

with open(TRACE_FILE_32, "w") as f:
    cur_addr = 0
    for i in range(NUM_REQUESTS):
        f.write(f"LD {cur_addr}\n")
        cur_addr += CACHELINE_SIZE_32

with open(TRACE_FILE_64, "w") as f:
    cur_addr = 0
    for i in range(NUM_REQUESTS):
        f.write(f"LD {cur_addr}\n")
        cur_addr += CACHELINE_SIZE_64
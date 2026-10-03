"""Generate READ-N traces with hexadecimal addresses."""

NUM_REQUESTS = 1_000_000
NUM_STREAMS = [1, 4, 16]
STREAM_SPACING = 16**6


def generate_read_n(num_streams, line_bytes):
    load_seq = []
    for i in range (NUM_REQUESTS):
        stream = i % num_streams
        line = i // num_streams
        addr = stream * STREAM_SPACING + line * line_bytes
        load_seq.append(addr)

    filename = f"read_{num_streams}_{line_bytes}B.trace"

    with open(filename, "w") as trace:
        for addr in load_seq:
            trace.write(f"LD 0x{addr:08X}\n")

    print(f"Generated {filename}: {NUM_REQUESTS:,} requests")


if __name__ == "__main__":
    for line_bytes in (32, 64):
        for num_streams in NUM_STREAMS:
            generate_read_n(num_streams, line_bytes)
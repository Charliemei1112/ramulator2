"""Print bytes per request for each DRAM standard, excluding VRR variants."""

import ramulator

CACHE_LINE_SIZE = {}
import cache_line_size

for name in ramulator.dram.__all__:
    if "VRR" in name:
        continue

    dram_class = getattr(ramulator.dram, name)
    # sizes = set()
    dram = next(iter(dram_class.org_presets.values()))

    size_bytes = dram_class.data_payload_bytes
    if size_bytes is None or size_bytes <= 0:
        size_bytes = (dram_class.internal_prefetch_size * dram["channel_width"] // 8)

    CACHE_LINE_SIZE[name] = size_bytes

print(CACHE_LINE_SIZE)
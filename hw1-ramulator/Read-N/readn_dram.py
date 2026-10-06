# Configure DDR3.


import ramulator

# DDR3 Configuration
ddr3 = ramulator.dram.DDR3(
    org_preset="DDR3_2Gb_x8",
    timing_preset="DDR3_1600H",
)

# DDR4 Configuration
ddr4 = ramulator.dram.DDR4(
    org_preset="DDR4_8Gb_x8",
    timing_preset="DDR4_2400R",
)

# DDR5 Configuration
ddr5 = ramulator.dram.DDR5(
        org_preset="DDR5_16Gb_x8",      
        timing_preset="DDR5_4800AN",                    
    )

# GDDR6 Configuration
gddr6 = ramulator.dram.GDDR6(
    org_preset="GDDR6_8Gb_x16",                 # 8Gb device, two 16-bit channels
    timing_preset="GDDR6_14000_1350mV_double",  # 14 Gb/s, 1.35 V
)

# GDDR7 Configuration.
gddr7 = ramulator.dram.GDDR7(
    org_preset="GDDR7_16Gb_x8",        # 16Gb device, four 8-bit channels
    timing_preset="GDDR7_28000_PAM3",  # 28 Gb/s; preset command timings
)

# LPDDR5 Configuration
lpddr5 = ramulator.dram.LPDDR5(
    org_preset="LPDDR5_8Gb_x16",
    timing_preset="LPDDR5_6400",
    #using default configs
)

lpddr6 = ramulator.dram.LPDDR6(
    org_preset="LPDDR6_16Gb_x12",
    timing_preset="LPDDR6_10667_BL24",
    #using default configs
)

hbm1 = ramulator.dram.HBM1(
    org_preset="HBM1_2Gb",
    timing_preset="HBM1_2Gbps",
)

hbm2 = ramulator.dram.HBM2(
    org_preset="HBM2_2Gb",
    timing_preset="HBM2_2000Mbps",
)

hbm3 = ramulator.dram.HBM3(
    org_preset="HBM3_16Gb_8hi",
    timing_preset="HBM3_6400Mbps",
)

hbm4 = ramulator.dram.HBM4(
    org_preset="HBM4_32Gb_8Hi",
    timing_preset="HBM4_8000Mbps",
    #using default configs
)



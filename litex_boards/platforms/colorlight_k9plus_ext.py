#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2023 Charles-Henri Mousset <ch.mousset@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build.xilinx import Xilinx7SeriesPlatform
from litex.build.openfpgaloader import OpenFPGALoader

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk.
    ("clk25", 0, Pins("W19"), IOStandard("LVCMOS33")),
    # Ext Rst
    ("cpu_reset", 0, Pins("P16"), IOStandard("LVCMOS33")),
    # Leds.
    ("user_led", 0, Pins("V18"), IOStandard("LVCMOS33")),

    # Ext Leds.
    ("user_led", 1, Pins("P17"), IOStandard("LVCMOS33")),
    ("user_led", 2, Pins("V20"), IOStandard("LVCMOS33")),
    # ("user_led", 3, Pins("V22"), IOStandard("LVCMOS33")), # CONFILCT
    # ("user_led", 4, Pins("U21"), IOStandard("LVCMOS33")),
    # Ext Serial
    ("serial", 0,
        Subsignal("tx", Pins("V17")),
        Subsignal("rx", Pins("R16")),
        IOStandard("LVCMOS33")
    ),
    # Ext SDCard.
    ("sdcard", 0,
        Subsignal("data", Pins("P6 P5 T5 T4"), Misc("PULLUP True")),
        Subsignal("cmd",  Pins("R4"),            Misc("PULLUP True")),
        Subsignal("clk",  Pins("N5")),
        # Subsignal("cd",   Pins("Y25")),
        Misc("SLEW=FAST"),
        IOStandard("LVCMOS33"),
    ),

    # RGMII Ethernet (B50612D) PHY 0.
    ("eth_clocks", 0, # U5 is SDIO phy #0
        Subsignal("tx", Pins("W4")),
        Subsignal("rx", Pins("V4")),
        IOStandard("LVCMOS33")
    ),
    ("eth", 0,
        Subsignal("rst_n",   Pins("W22")),
        Subsignal("mdio",    Pins("Y22")),
        Subsignal("mdc",     Pins("W21")),
        Subsignal("rx_ctl",  Pins("AB18")),
        Subsignal("rx_data", Pins("AA18 Y19 AA19 AB20")),
        Subsignal("tx_ctl",  Pins("Y4")),
        Subsignal("tx_data", Pins("AA3 AA4 AB5 AA5")),
        IOStandard("LVCMOS33")
    ),
    # RGMII Ethernet (B50612D) PHY 1.
    ("eth_clocks", 1, # U9 is SDIO phy #1
        Subsignal("tx", Pins("W20")),
        Subsignal("rx", Pins("Y18")),
        IOStandard("LVCMOS33")
    ),
    ("eth", 1,
        Subsignal("rst_n",   Pins("W22")),
        Subsignal("mdio",    Pins("Y22")),
        Subsignal("mdc",     Pins("W21")),
        Subsignal("rx_ctl",  Pins("AA1")),
        Subsignal("rx_data", Pins("AB1 AB2 Y3 AB3")),
        Subsignal("tx_ctl",  Pins("AA20")),
        Subsignal("tx_data", Pins("AB21 AA21 AB22 Y21")),
        IOStandard("LVCMOS33")
    ),

    # SPIFlash
    ("spiflash", 0,
        Subsignal("cs_n", Pins("T19")),
        Subsignal("clk",  Pins("V22")),
        Subsignal("mosi", Pins("P22")),
        Subsignal("miso", Pins("R22")),
        Subsignal("wp",   Pins("P21")),
        Subsignal("hold", Pins("R21")),
        IOStandard("LVCMOS33"),
    ),
    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("T19")),
        Subsignal("clk",  Pins("V22")),
        Subsignal("dq",   Pins("P22 R22 P21 R21")),
        IOStandard("LVCMOS33")
    ),

    # SDRRAM (M12L64322A).
    ("sdram_clock", 0, Pins("C19"), IOStandard("LVCMOS33")),
    ("sdram", 0,
        Subsignal("a", Pins(
            "F14 D14 E14 E17 D19 F18 "
            "D17 F19 E18 E16 F15 ")),  # Address pin A11 routed but NC on M12L64322A
        Subsignal("dq", Pins(
            "A13 A19 B13 A20 C13 C18 B18 A18 "
            "D22 E19 E21 F21 E22 F20 G22 G21 "
            "A14 B17 C17 A15 B16 B15 A16 C15 "
            "A21 C20 B21 C22 B22 D20 B20 D21 "
            )),
        Subsignal("we_n",  Pins("C14")),
        Subsignal("ras_n", Pins("F13")),
        Subsignal("cas_n", Pins("D16")),
        #Subsignal("cs_n", Pins("")), # GND
        #Subsignal("cke",  Pins("")), # 3V3
        Subsignal("ba",    Pins("F16 D15")),
        #Subsignal("dm",   Pins("")), # GND
        IOStandard("LVCMOS33"),
        Misc("SLEWRATE=FAST")
    ),
    
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = []


# Platform -----------------------------------------------------------------------------------------

class Platform(Xilinx7SeriesPlatform):
    default_clk_name   = "clk25"
    default_clk_period = 1e9/25e6

    def __init__(self, toolchain="vivado"):
        Xilinx7SeriesPlatform.__init__(self, "xc7a50tfgg484-1", _io, _connectors, toolchain=toolchain)
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 1 [current_design]\n"
             "set_property CONFIG_MODE SPIx1 [current_design]\n"
             "set_property BITSTREAM.CONFIG.CONFIGRATE 50 [current_design]\n"
             "set_property BITSTREAM.CONFIG.SPI_32BIT_ADDR NO [current_design]"]
        self.toolchain.additional_commands = \
            ["write_cfgmem -force -format bin -interface spix1 -size 16 "
             "-loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]


    def create_programmer(self):
        return OpenFPGALoader(cable="ch347_jtag")

    def do_finalize(self, fragment):
        Xilinx7SeriesPlatform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request(self.default_clk_name, loose=True), self.default_clk_period)

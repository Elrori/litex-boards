#!/usr/bin/env python3

#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2020 Antmicro <www.antmicro.com>
# Copyright (c) 2022 Victor Suarez Rovere <suarezvictor@gmail.com>
# Copyright (c) 2023 Charles-Henri Mousset <ch.mousset@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause


from migen import *

from litex.gen import *

from litex.build.io import DDROutput

from litex_boards.platforms import colorlight_k9plus_ext

from litex.soc.cores.clock import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores.led import LedChaser
from litex.soc.cores.dna  import DNA

from litedram.modules import M12L64322A
from litedram.phy import GENSDRPHY

from liteeth.phy.s7rgmii import LiteEthPHYRGMII

from litex.soc.cores.video import VideoS7HDMIPHY

# CRG ----------------------------------------------------------------------------------------------

class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq, with_dram=True, with_ethernet=True):
        self.rst       = Signal()
        self.cd_sys    = ClockDomain()
        self.cd_idelay = ClockDomain()

        self.cd_hdmi   = ClockDomain()
        self.cd_hdmi5x = ClockDomain()

        if with_dram:
            self.cd_sys_ps = ClockDomain()
        # # #

        # Clk/Rst.
        clk25 = platform.request("clk25")
        rst   = ~platform.request("cpu_reset")

        # PLL.
        self.pll = pll = S7PLL(speedgrade=-1)
        self.comb += pll.reset.eq(self.rst | rst)
        pll.register_clkin(clk25, 25e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)
        pll.create_clkout(self.cd_idelay,    200e6)
        pll.create_clkout(self.cd_hdmi,   25e6,  margin=0)
        pll.create_clkout(self.cd_hdmi5x, 125e6, margin=0)
        platform.add_false_path_constraints(self.cd_sys.clk, pll.clkin) # Ignore sys_clk to pll.clkin path created by SoC's rst.
        self.idelayctrl = S7IDELAYCTRL(self.cd_idelay)

        if with_dram:
            pll.create_clkout(self.cd_sys_ps, sys_clk_freq, phase=90) # untested
            # SDRAM clock
            sdram_clk = ClockSignal("sys_ps")
            self.specials += DDROutput(1, 0, platform.request("sdram_clock"), sdram_clk)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, toolchain="vivado", sys_clk_freq=100e6,
        with_dna        = False,
        with_pmod_uart  = False,
        with_ethernet   = False,
        with_etherbone  = False,
        eth_port        = 0,
        eth_ip          = "192.168.1.50",
        eth_dynamic_ip  = False,
        with_led_chaser = True,
        with_spi_flash  = False,
        with_sdcard     = True,
        **kwargs):
        platform = colorlight_k9plus_ext.Platform(toolchain=toolchain)

        # CRG --------------------------------------------------------------------------------------
        self.crg  = _CRG(platform, sys_clk_freq, True)

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq, ident="LiteX SoC on Arty A7", **kwargs)

        # SDRAM ------------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            sdrphy_cls = GENSDRPHY
            self.sdrphy = sdrphy_cls(platform.request("sdram"))
            self.add_sdram("sdram",
                phy           = self.sdrphy,
                module        = M12L64322A(sys_clk_freq, "1:1"),
                l2_cache_size = kwargs.get("l2_size", 8192)
            )


        # Ethernet / Etherbone ---------------------------------------------------------------------
        # if with_ethernet or with_etherbone:
        #     self.ethphy = LiteEthPHYRGMII(
        #         clock_pads = self.platform.request("eth_clocks", eth_port),
        #         pads       = self.platform.request("eth", eth_port),
        #         tx_delay = 0)
        #     if with_ethernet:
        #         self.add_ethernet(phy=self.ethphy, dynamic_ip=eth_dynamic_ip)
        #     if with_etherbone:
        #         self.add_etherbone(phy=self.ethphy, ip_address=eth_ip)
        # if with_ethernet or with_etherbone:
        #     self.ethphy = LiteEthPHYRGMII(
        #         clock_pads = self.platform.request("eth_clocks", eth_port),
        #         pads       = self.platform.request("eth", eth_port),
        #         tx_delay = 0)
        #     if with_ethernet:
        #         self.add_ethernet(phy=self.ethphy)
        #     if with_etherbone:
        #         self.add_etherbone(phy=self.ethphy)

        if with_ethernet:
            self.ethphy = LiteEthPHYRGMII(
                clock_pads = self.platform.request("eth_clocks", 0),
                pads       = self.platform.request("eth", 0),
                tx_delay = 0e-9,
                rx_delay = 2e-9,
            )
            self.add_ethernet(phy=self.ethphy)

        # HDMI Options -----------------------------------------------------------------------------
        # if with_hdmi and (with_video_colorbars or with_video_framebuffer or with_video_terminal):
        #     self.videophy = VideoS7HDMIPHY(platform.request("hdmi_out"), clock_domain="hdmi")
        #     if with_video_colorbars:
        #         self.add_video_colorbars(phy=self.videophy, timings="640x480@60Hz", clock_domain="hdmi")
        #     if with_video_terminal:
        #         self.add_video_terminal(phy=self.videophy, timings="640x480@60Hz", clock_domain="hdmi")
        #     if with_video_framebuffer:
        #         self.add_video_framebuffer(phy=self.videophy, timings="640x480@60Hz", clock_domain="hdmi")
        self.videophy = VideoS7HDMIPHY(platform.request("hdmi_out"), clock_domain="hdmi")
        self.add_video_colorbars(phy=self.videophy, timings="640x480@60Hz", clock_domain="hdmi")

        # SPI Flash --------------------------------------------------------------------------------
        if with_spi_flash:
            from litespi.modules import MX25L12833F
            from litespi.opcodes import SpiNorFlashOpCodes as Codes
            self.add_spi_flash(mode="4x", module=MX25L12833F(Codes.READ_1_1_4),rate="1:2")

        # Leds -------------------------------------------------------------------------------------
        if with_led_chaser:
            self.leds = LedChaser(
                pads         = platform.request_all("user_led"),
                sys_clk_freq = sys_clk_freq,
            )

        # SD Card ----------------------------------------------------------------------------------
        if with_sdcard:
            self.add_sdcard()

# Build --------------------------------------------------------------------------------------------

def main():
    from litex.build.parser import LiteXArgumentParser
    parser = LiteXArgumentParser(platform=colorlight_k9plus_ext.Platform, description="LiteX SoC on Arty A7.")
    parser.add_target_argument("--flash",          action="store_true",       help="Flash bitstream.")
    parser.add_target_argument("--sys-clk-freq",   default=100e6, type=float, help="System clock frequency.")
    parser.add_target_argument("--with-dna",       action="store_true",       help="Enable 7-Series DNA.")
    parser.add_target_argument("--with-pmod-uart", action="store_true",       help="Enable uart on P2 (top) PMOD")
    ethopts = parser.target_group.add_mutually_exclusive_group()
    ethopts.add_argument("--with-ethernet",        action="store_true",       help="Enable Ethernet support.")
    ethopts.add_argument("--with-etherbone",       action="store_true",       help="Enable Etherbone support.")
    parser.add_target_argument("--eth-port",       default=0, type=int,       help="Ethernet port to use (0/1)")
    parser.add_target_argument("--eth-ip",         default="192.168.1.50",    help="Ethernet/Etherbone IP address.")
    parser.add_target_argument("--eth-dynamic-ip", action="store_true",       help="Enable dynamic Ethernet IP addresses setting.")
    parser.add_target_argument("--with-spi-flash", action="store_true",       help="Enable SPI Flash (MMAPed).")
    args = parser.parse_args()

    assert not (args.with_etherbone and args.eth_dynamic_ip)

    soc = BaseSoC(
        toolchain      = args.toolchain,
        sys_clk_freq   = args.sys_clk_freq,
        with_dna       = args.with_dna,
        with_pmod_uart = args.with_pmod_uart,
        with_ethernet  = args.with_ethernet,
        with_etherbone = args.with_etherbone,
        eth_port       = args.eth_port,
        eth_ip         = args.eth_ip,
        eth_dynamic_ip = args.eth_dynamic_ip,
        with_spi_flash = args.with_spi_flash,
        **parser.soc_argdict
    )

    builder = Builder(soc, **parser.builder_argdict)
    if args.build:
        builder.build(**parser.toolchain_argdict)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))

    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0, builder.get_bitstream_filename(mode="flash"))

if __name__ == "__main__":
    main()

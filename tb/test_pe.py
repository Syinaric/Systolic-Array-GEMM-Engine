""" cocotb tb for rtl/pe.sv """

import os 
import random 
import cocotb 
from cocotb.clock import clock 
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer 
from pe_model import PEModel, expected_dot, signed_range, wrap_signed
from delay_model import expected_out 

#helpers

def read_int(sig, name): 
    raw = str(sig.value)
    if "x" in raw.lower() or "z" in raw.lower(): 
        raise AssertionError(f"{name} is not resolvable: {raw}")
    return int(sig.value)

def read_signed(sig, name, width): 
    raw = read_int(sig, name)
    return raw - (1 << width) if raw >= (1 << (width - 1)) else raw 

def to_unsigned(value, width):
    return value & ((1 << width) - 1)


class PEHarness: 
    """Drives the DUT and the golden model from one input vector.
 
    Everything in this file goes through `step()`. That is deliberate: if the
    testbench ever drives the DUT and the model from separately-constructed
    stimulus, a mismatch stops being evidence about the RTL and starts being
    evidence about the testbench.
    """

    PORTS = ("a_out", "b_out", "first_out", "last_out", "drain_out")
    INTERNAL = ("acc", "active") 

    def __init__(self, dut): 
        self.dut = dut 
        self.dw = int(dut.DATA_WIDTH.value) 
        self.aw = int(dut.ACC_WIDTH.value) 
        self.model = PEModel(self.dw, self.aw) 
        self.cylce = 0 
        self.seed = int(os.environ.get("SEED") or random.randrange )
        self.rng = random.Random(self.seed) 


    async def start(self, reset_cycles = 3): 
        cocotb.start_soon(Clock(self.dut.clk, 10, unit="ns").start())
        self.dut.reset.value = 1 
        self._drive_idle() 
        for _ in range (reset_cycles): 
            await RisingEdge(self.dut.clk) 
            self.model.step(reset=1) 
        await FallingEdge(self.dut.clk)
        self.dut.eset.value = 0 
        self.dut._log.info(f"DUT parameters: DATA_WIDTH={self.dw} ACC_WIDTH={self.aw} "
                           f"SEED= {self.seed} (reproduce with: make MODULE_NAME=pe"
                           f"k=<k> SEED = {self.seed})")


    def _drive_idle(self): 
        d = self.dut 
        d.a_in.value = 0 
        d.b_in.value = 0 
        d.first_in.value = 0 
        d.last_in.value = 0 
        d.drain_shift.value = 0 
        d.drain_in.value = 0 
        d.en.value = 1 

    async def step(self, a_in=0, b_in = 0, first_in = 0, last_in=0, drain_shift=0,
                    drain_in=0, en = 1, reset = 0, check = True): 
        """advance 1 rising edge on both dut and model, then compare 
        returns the expected ReadOnly view of the model state"""

        d = self.dut 
        await FallingEdge(d.clk) 
        d.a_in.value = to_unsigned(a_in, self.dw) 
        d.b_in.value = to_unsigned(b_in, self.dw)
        d.first_in.value = first_in
        d.last_in.value = last_in
        d.drain_shift.value = drain_shift
        d.drain_in.value = to_unsigned(drain_in, self.aw)
        d.en.value = en
        d.reset.value = reset
 
        await RisingEdge(d.clk)
        await ReadOnly()


        expected = self.model.step(  a_in=a_in, b_in=b_in, first_in=first_in, last_in=last_in,
            drain_shift=drain_shift, drain_in=drain_in, en=en, reset=reset,)
        if check: 
            self._compare(expected, a_in, b_in, first_in, last_in, en, reset )
            self.cycle += 1 
            return expected 


    def _compare(self, expected, a_in, b_in, first_in, last_in, en, reset) : 
        d = self.dut 
        widths = { 
            "a_out": self.dw, "b_out": self.dw, "first_out": 1, "last_out" : 1, 
            "drain_out" : self.aw, "acc": self.aw, "active" : 1
        }
        for name in self.PORTS + self.INTERNAL: 
            w = width[name] 
            sig = getattr(d, name) 
            got = read_signed(sig, name, w) if w > 1 else read_int(sig, name) 
            exp = getattr(expected, name )
            assert got == exp, (  
                f"cycle {self.cycle}: {name}={got}, expected {exp}\n"
                f"stimulus: a_in={a_in} b_in={b_in} first_in={first_in} "
                f"last_in={last_in} en={en} reset={reset}\n"
                f"seed={self.seed}"
            )
    async def run_tile(self, a_vec, b_vec, drain_after = True) :
        """drive 1 k length tile. returns drained result"""
        k = len(a_vec) 
        for i, (a, b) in enumerate(zip(a_vec, b_vec)): 
            await self.step (a_in=a, b_in=b, firs_in = int(i == 0), last_in = int(i == k - 1))
        if drain_after : 
            s = await self.step() 
            return s.drain_out 
        return None 
    
    def random_operands(self, n): 
        lo, hi = signed_range
        return [self.rng.randint(lo,hi)for _ in range (n)] 

def get_k(): 
    return int(os.environ.get ("k") or 8)


    #signedness 
@cocotb.test() 
async def test_signed_quadrants(dut): 
    """all 4 sign combinations + asymetrical extreme""" 

    h = PEHarness(dut) 
    await h.start() 
    lo, hi = signed_range(h.dw) 
    vectors = [ (7,6) , (7,-6), (-7, 6), (-7,-6), (lo, lo), (lo, hi) ,
                (hi, hi), (lo, 1), (1, lo), (0, lo),
    ]

    for a, b in vectors: 
        result = await h.run_tile ([a], [b])
        assert result == a*b, f"{a} * {b} = {results}, expected {a * b}"
        dut._log.info(f" sign quadrants passed ({len(vectors)} vectors)")

#acc 
@cocotb.test() 
async def test_k_accumulation_random(dut): 
    """randomized k length accumalation against golden model"""
    h = PEHarness(dut)
    await h.start()
    k = get_k()

    for tile in range(8): 
        a_vec = h.random_operands(k) 
        b_vec = h.random_operands(k) 
        result = await h.run_tile(a_vec, b_vec) 
        expected = expected_dot(a_vec, b_vec, h.aw) 
        assert expected == result (
            f" tile{tile} : K{k} result={result} expected{expected}, " 
            f" seed{h.seed} "
        )
        await h.step() 
    dut._log.info(f"random accumalation passed: 8 tiles at K={k}")


@cocotb.test() 
async def test_k1_coincdent_irst_last(dut): 
    """first_in and last_in are asserted on the same cycle"""
    h = PEHarness(dut) 
    await h.start() 
    await h.step(a_in=-128, b_in=-128, first_in = 1, last_in = 1)
    assert read_int( dut.active, "active") == 0, ( 
        "active must clear when first_in and last_in coincide (k = 1)" 
    )
    s = await h.step() 
    assert s.drain_out == 16384


""" cocotb tb for rtl/systolic_array.sv """
import os 
import random 
import cocotb 
from cocotb.clock import Clock 
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge 
from systolic_array_model import SystolicArrayModel, expected_matmul
from pe_model import signed_range 

#--------------------------------Import--------------------------------
from Core.Instrument_Driver.Instrument_Interface import *
#InputSource
from Core.Instrument_Driver.Source.Chroma_6560 import Chroma_6560
from Core.Instrument_Driver.Source.Kikusui_PCR import Kikusui_PCR
from Core.Instrument_Driver.Source.Chroma_61512 import Chroma_61512
from Core.Instrument_Driver.Source.Chroma_61509 import Chroma_61509
from Core.Instrument_Driver.Source.NF_DP120S import NF_DP120S
#PowerMeter
from Core.Instrument_Driver.Meter.Yokogawa_WT3000 import Yokogawa_WT3000
#E-Load
from Core.Instrument_Driver.Load.Chroma_632xx import Chroma_632xx
from Core.Instrument_Driver.Load.Chroma_636xx import Chroma_63600
#Fan_DC_Source
from Core.Instrument_Driver.DC_Power_Supply.Chroma_62015L import Chroma_62015L
#-----------------------------------------------------------------------



#-----------------------------Configuration----------------------------
# DC_Power_Supply.append(Chroma_62015L("GPIB0::20::INSTR"))
Meter.append(Yokogawa_WT3000("GPIB0::1::INSTR"))

Source.append(Chroma_6560("GPIB0::30::INSTR")) 
Load.append(Chroma_632xx("GPIB0::7::INSTR"))
#-----------------------------------------------------------------------










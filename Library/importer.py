from Core.Tools.Tools import *
from Core.Instrument_Driver.Scope.iScope_Lib.Utility import *
from Core.Instrument_Driver.Instrument_Interface import *
from Core.Instrument_Driver.Instrument_InterfaceEX import *
from .library import *
from ..Library import ItemCore
from Core.Main.Sub_Task.Test_Plan.Reader import LoadModuleFromFullPath,LoadModulePath
from Core.Main.Sub_Task import Main_Configuration_Unit
import enum
import os
from typing import Literal

from Core.Instrument_Driver.Meter.iMeter_Lib.Meter_Measure_Mode import Meter_Measure_Mode
from Core.Instrument_Driver.Source.Kikusui_PCR import Kikusui_PCR
from Core.Instrument_Driver.Source.Chroma_Lib.Chroma_DSTWaveform import Chroma_DSTWaveform

PSU1 = PSUx_Unit()
PSU2 = PSUx_Unit()
PSUx = [PSU1,PSU2]

working_path = os.getcwd()
exec("from " + LoadModulePath("\\Project\\" + Main_Configuration_Unit.main_Config.ProjectName + "\\Library\\library.py" + " import *"))
LoadModuleFromFullPath("\\Project\\" + Main_Configuration_Unit.main_Config.ProjectName + "\\Instrument\\" + Main_Configuration_Unit.main_Config.Instrument_FileName)




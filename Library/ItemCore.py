from Core import ItemCore

# from ..Instrument.Custom import iScopeEX
from . import library
from typing import List


class LogUnit(ItemCore.LogUnit):
    def __init__(self) -> None:
        super().__init__()
        # self.Scope_Setting = iScopeEX.ScopeEX_Data_Unit()
        self.VoutName: List[str] = []
        for vout in library.PSU.Output:
            self.VoutName.append(vout.Name)


class TestItem(ItemCore.TestItem):

    def First_Run(self):
        super().First_Run()

    pass

    def Run_All_Condition(self):
        for i in range(len(library.PSU.Output)):
            library.PSU.Output[i].Set_Max_Current_Ratio(self.Test_Plan_Data.Current_Ratio)
        return super().Run_All_Condition()

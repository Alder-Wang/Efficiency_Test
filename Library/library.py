from typing import overload, List
from Core.Instrument_Driver.Instrument_Interface import *
from Core.Tools.Tools import *
from Core.Instrument_Driver.Scope.iScope_Lib.Utility import *
from Core.Instrument_Driver.Extend_Instrument.ScopeEX.Utility import DefaultChannelList as DefltChanelList
from Core.Instrument_Driver._Low_Level.VISA import Setting

# 這裡定義了CRPS需要的內容


class Event_Type(enum.Enum):
    PSU_TurnOff = 1
    OCP = 2
    PSU_TurnON = 3
    Communication = 4
    Vin_Dropout = 5
    # 尚缺CR_Bus 00 01 02 03


class PSU_Output:
    Name = ""
    Voltage_Set_Point = 0
    Current_Max = [0]

    def __init__(
        self,
        Name: str,
        Voltage_Set_Point: float,
        Current_Max: List[float],
        OC_Point: float,
        Max_Current_Ratio: float,
    ) -> None:
        self.Name = Name
        self.Voltage_Set_Point = Voltage_Set_Point
        self._Current_Max = Current_Max
        self.Max_Current_Ratio = Max_Current_Ratio
        # 每一個Current_Max都放大Max_Current_Ratio倍
        self.Current_Max = [x * self.Max_Current_Ratio for x in Current_Max]
        self.OC_Point = OC_Point

    def Set_Max_Current_Ratio(self, Ratio: float):
        self.Max_Current_Ratio = Ratio
        self.Current_Max = [x * self.Max_Current_Ratio for x in self._Current_Max]


class PSU_Intput:
    Name = ""
    Normal_Voltage = 0
    Min_Voltage = 0
    Max_Voltage = 0
    Frequency = 0

    def __init__(
        self,
        Name: str,
        Min_Voltage: float,
        Normal_Voltage: float,
        Max_Voltage: float,
        Frequency: float,
    ) -> None:
        self.Name = Name
        self.Normal_Voltage = Normal_Voltage
        self.Min_Voltage = Min_Voltage
        self.Max_Voltage = Max_Voltage
        self.Frequency = Frequency


class PSU_System:

    def __init__(self) -> None:
        self.Output = [
            # Name   Volt    Current(Low/High)   Current數量需與Input數量相同
            PSU_Output("+12V", 12, [123, 81.9, 123], 150, 1),
            PSU_Output("Vsb", 12, [3, 3, 3], 5, 1),
            # PSU_Output("+12V", 12.2, [45.08, 45.08, 45.08], 50),
            # PSU_Output("Vsb", 3.3, [3, 3, 3], 5),
        ]

        self.Input = [
            # Name   Min     Normal  Max     Freq
            PSU_Intput("Vin", 180, 230, 264, 63),
            PSU_Intput("Vin", 80, 120, 140, 47),
            PSU_Intput("Vin", 150, 230, 310, 0),
        ]

    def PSU_OFF(self):
        """
        關閉所有單體
        1. 關閉所有輸入
        2. 所有負載1A, 持續3秒
        3. 關閉所有負載
        """
        for s in Source:
            s.Turn_OFF()

        for l in Load:
            l.Load_CC_ON_Amp(1)
        Delay(3)
        for l in Load:
            l.Load_OFF()

    @overload
    def get_LoadMax(self, Channel: int, Input: float, Freq: float) -> float:
        return self.get_LoadMax(Channel, Input, Freq)

    @overload
    def get_LoadMax(self, Channel: int, Input: Voltage_Data) -> float:
        return self.get_LoadMax(Channel, Input)

    def get_LoadMax(self, Channel: int, Input: Voltage_Data | float, Freq: float = -1, Percent=-1) -> float:
        """
        取得負載最大電流
        """
        ivin = -1
        ifreq = -1
        if isinstance(Input, Voltage_Data):
            ivin = Input.Voltage
            ifreq = Input.Frequency
        else:
            ivin = Input
            ifreq = Freq

        RangeIndex = 0
        for i in range(len(self.Input)):
            if not ((self.Input[i].Frequency == 0) ^ (ifreq == 0)):
                if CheckInRange(self.Input[i].Min_Voltage, ivin, self.Input[i].Max_Voltage):
                    return self.Output[Channel].Current_Max[i]

        # when not in all Ranges
        return 0


class CMD_STATUS_WORD:
    def __init__(self, Value: int) -> None:
        self.Value = Value
        self.CML = Value & 0b00000010  # bit 1
        self.TEMPERATURE = Value & 0b00000100  # bit 2
        self.VIN_UV_FAULT = Value & 0b00001000  # bit 3
        self.IOUT_OC_FAULT = Value & 0b00010000  # bit 4
        self.OFF = Value & 0b01000000  # bit 6
        HValue = Value >> 8
        self.FANS = HValue & 0b00000100  # bit 2
        self.POWER_GOOD = HValue & 0b00001000  # bit 3
        self.INPUT = HValue & 0b00100000  # bit 5
        self.IOUT_POUT = HValue & 0b01000000  # bit 6
        self.VOUT = HValue & 0b10000000  # bit 7


class CMD_STATUS_VOUT:
    def __init__(self, Value: int) -> None:
        self.Value = Value
        self.VOUT_OV_FAULT = Value & 0b10000000  # bit 7
        self.VOUT_UV_FAULT = Value & 0b00010000  # bit 4


class CMD_STATUS_IOUT:
    def __init__(self, Value: int) -> None:
        self.Value = Value
        self.IOUT_OC_FAULT = Value & 0b10000000  # bit 7
        self.IOUT_OC_WARNING = Value & 0b00100000  # bit 5
        self.POUT_OP_FAULT = Value & 0b00000010  # bit 1
        self.POUT_OP_WARNING = Value & 0b00000001  # bit 0


class CMD_STATUS_INPUT:
    def __init__(self, Value: int) -> None:
        self.Value = Value
        self.VIN_UV_WARNING = Value & 0b00100000  # bit 5
        self.VIN_UV_FAULT = Value & 0b00010000  # bit 4
        self.VIN_UNIT_OFF_FOR_LOW_INPUT_VOLTAGE = Value & 0b00001000  # bit 3
        self.IIN_OC_WARNING = Value & 0b00000010  # bit 1
        self.PIN_OP_WARNING = Value & 0b00000001  # bit 0


class CMD_STATUS_TEMPERATURE:
    def __init__(self, Value: int) -> None:
        self.Value = Value
        self.TEMPERATURE_WARNING = Value & 0b01000000  # bit 6
        self.TEMPERATURE_FAULT = Value & 0b10000000  # bit 7


class CMD_STATUS_FAN_1_2:
    def __init__(self, Value: int) -> None:
        self.Value = Value
        self.FAN_1_WARNING = Value & 0b00100000  # bit 5
        self.FAN_1_FAULT = Value & 0b10000000  # bit 7


class CMD_STATUS_CML:
    def __init__(self, Value: int) -> None:
        self.Value = Value
        self.INVALID_UNSUPPORT_COMMAND = Value & 0b10000000  # bit 7
        self.INVALID_UNSUPPORT_DATA = Value & 0b01000000  # bit 6
        self.PEC_FAULT = Value & 0b00100000  # bit 5
        self.MEMORY_FAULT = Value & 0b00010000  # bit 4
        self.PROCESSOR_FAULT = Value & 0b00001000  # bit 3
        self.COMMUNICATION_FAULT = Value & 0b00000100  # bit 2
        # bit 1 reserved
        self.MEMORY_LOGIC_FAULT = Value & 0b00000001  # bit 0


# Fast Operation
class Cold_Redundancy_Status(enum.Enum):
    # Command is 0xD0
    Standard = 0x00  # 開機起始狀態
    Active = 0x01
    CR1 = 0x02
    CR2 = 0x03
    CR3 = 0x04
    Always_Standby = 0x05
    Reserved_Unknown = 0x06  # 0x06~0xFF
    NO_ACK = 0xFF


class PSUx_Unit:
    def __init__(self) -> None:
        self.PSON: iGPIO.GPIO_Interface
        self.I2C: iI2C.I2C_Interface

    def Get_HW_Revision(self) -> str:
        r = self.I2C.ReadWrite([0x9B], 10)

        if not r.success:
            return "NO_ACK"
        else:
            # 根據第一Byte的值取得後面的長度，如02,03,04,05
            # 再將後面的Byte轉成acsii
            # 再將acsii合併成字串
            return "".join([chr(x) for x in r.data[1 : r.data[0] + 1]])

    def Get_FW1st_Revision(self) -> str:
        r = self.I2C.ReadWrite([0xD9], 10)
        if not r.success:
            return "NO_ACK"
        else:
            # 根據第一Byte的值取得後面的長度，如03,03,04,05
            # 取回資料Buf為03,04,05
            # 其中 1st FW Revision為Buf[3] + Buf[2] = '0504'
            # 將Buf[3], Buf[2]轉為16進制的字串，合併後回傳
            # 如'0504'

            return "{:02X}{:02X}".format(r.data[3], r.data[2])

    def Get_FW2nd_Revision(self) -> str:
        r = self.I2C.ReadWrite([0xD9], 10)
        if not r.success:
            return "NO_ACK"
        else:
            # 根據第一Byte的值取得後面的長度，如03,03,04,05
            # 取回資料Buf為03,04,05
            # 其中 1st FW Revision為Buf[3] + Buf[1] = '0503'
            # 將Buf[3], Buf[2]轉為16進制的字串，合併後回傳
            # 如'0503'

            return "{:02X}{:02X}".format(r.data[3], r.data[1])

    def CR_Mode(self, Mode: Cold_Redundancy_Status | None = None) -> Cold_Redundancy_Status:
        if isinstance(Mode, Cold_Redundancy_Status):
            for i in range(10):
                self.I2C.Write([0xD0, Mode.value])
                r = self.I2C.ReadWrite([0xD0], 1)
                if r.success:
                    if Cold_Redundancy_Status(r.data[0]) == Mode:
                        return Cold_Redundancy_Status(r.data[0])

            return Cold_Redundancy_Status.NO_ACK
        else:
            r = self.I2C.ReadWrite([0xD0], 1)
            if not r.success:
                return Cold_Redundancy_Status.NO_ACK
            else:
                return Cold_Redundancy_Status(r.data[0])

    def Get_IinOCW_Status(self) -> bool:
        return False

    def Get_Iin_OCW_Min(self) -> float:
        pass
        return 0

    def Set_IinOCW_Setpoint(self, Setpoint: float):
        pass

    def Set_Vout_Margining(self, Enable: bool):
        # 如果是True,下0x02 0x00
        # 如果是False, 下0x00 0x00
        if Enable:
            self.I2C.Write([0xED, 0x02, 0x00])
        else:
            self.I2C.Write([0xED, 0x00, 0x00])

    def Get_Vout_Margining(self) -> bool:
        r = self.I2C.ReadWrite([0xED], 2)
        if not r.success:
            return False
        else:
            if r.data[0] == 0x20 and r.data[1] == 0x00:
                return True
            else:
                return False

    def Clear_Fault(self):
        self.I2C.Write([0x03])
        pass

    def Read_Status_Word(self) -> CMD_STATUS_WORD:
        # r = self.I2C.Write([0x00,0xFF])
        r = 0
        r = self.I2C.ReadWrite([0x79], 2)
        if not r.success:
            return CMD_STATUS_WORD(0xFF)
        else:
            return CMD_STATUS_WORD((r.data[0] << 8) + r.data[1])

    def Read_Status_Vout(self) -> CMD_STATUS_VOUT:
        r = self.I2C.ReadWrite([0x7A], 1)
        if not r.success:
            return CMD_STATUS_VOUT(0xFF)
        else:
            return CMD_STATUS_VOUT(r.data[0])

    def Read_Status_Iout(self) -> CMD_STATUS_IOUT:
        r = self.I2C.ReadWrite([0x7B], 1)
        if not r.success:
            return CMD_STATUS_IOUT(0xFF)
        else:
            return CMD_STATUS_IOUT(r.data[0])

    def Read_Input_Status(self) -> CMD_STATUS_INPUT:
        r = self.I2C.ReadWrite([0x7C], 1)
        if not r.success:
            return CMD_STATUS_INPUT(0xFF)
        else:
            return CMD_STATUS_INPUT(r.data[0])

    def Read_Status_Temperature(self) -> CMD_STATUS_TEMPERATURE:
        r = self.I2C.ReadWrite([0x7C], 1)
        if not r.success:
            return CMD_STATUS_TEMPERATURE(0xFF)
        else:
            return CMD_STATUS_TEMPERATURE(r.data[0])

    def Read_Status_CML(self) -> CMD_STATUS_CML:
        r = self.I2C.ReadWrite([0x7E], 1)
        if not r.success:
            return CMD_STATUS_CML(0xFF)
        else:
            return CMD_STATUS_CML(r.data[0])

    def Read_Status_FAN(self) -> CMD_STATUS_FAN_1_2:
        r = self.I2C.ReadWrite([0x81], 1)
        if not r.success:
            return CMD_STATUS_FAN_1_2(0xFF)
        else:
            return CMD_STATUS_FAN_1_2(r.data[0])

    def Read_Vin(self) -> float:
        r = self.I2C.ReadWrite([0x88], 2)
        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            return self.I2C.Linear11_2_float([r.data[1], r.data[0]])

    def Read_Iin(self) -> float:
        r = self.I2C.ReadWrite([0x89], 2)
        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            return self.I2C.Linear11_2_float([r.data[1], r.data[0]])

    def Set_Page(self, Index: int = 0):
        self.I2C.Write([0, Index])

    def Read_Vout(self, Index: int = 0) -> float:
        self.Set_Page(Index)
        r = self.I2C.ReadWrite([0x8B], 2)

        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            buf = (r.data[1] << 8) + r.data[0]
            scale = self.Read_Vout_Scale(Index)
            return buf * scale

    def Read_Vout_Scale(self, Index: int = 0) -> float:
        self.Set_Page(Index)
        r = self.I2C.ReadWrite([0x20], 2)
        # 將r.data[0]bit4的值，儲存到buf
        # 如果buf=0，則r.data[0]bit5~7都是0
        # 如果buf=1，則r.data[0]bit5~7都是1

        buf = r.data[0] & 0b00010000
        if buf == 0:
            r.data[0] = r.data[0] & 0b00001111
        else:
            r.data[0] = r.data[0] | 0b11110000
            # 將r.data[0]轉成signed int
        if r.data[0] > 0x7F:
            r.data[0] = r.data[0] - 256
        return pow(2, r.data[0])

    def Read_Iout(self, Index: int = 0) -> float:
        self.Set_Page(Index)
        r = self.I2C.ReadWrite([0x8C], 2)
        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            return self.I2C.Linear11_2_float([r.data[1], r.data[0]])

    def Read_Temperature_1(self) -> float:
        r = self.I2C.ReadWrite([0x8D], 2)
        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            return self.I2C.Linear11_2_float([r.data[1], r.data[0]])

    def Read_Temperature_2(self) -> float:
        r = self.I2C.ReadWrite([0x8E], 2)
        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            return self.I2C.Linear11_2_float([r.data[1], r.data[0]])

    def Read_Fan_Speed(self) -> float:
        r = self.I2C.ReadWrite([0x90], 2)
        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            return self.I2C.Linear11_2_float([r.data[1], r.data[0]])

    def Write_Fan_Speed(self, value: float):
        # 這個命令還要釐清
        r = self.I2C.ReadWrite([0x3B], 2)
        new_spd = self.I2C.float_2_Linear11([0x00, 0x01], value)
        self.I2C.Write([0x3B, new_spd[1], new_spd[0]])

    def Read_Pout(self) -> float:
        r = self.I2C.ReadWrite([0x96], 2)
        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            return self.I2C.Linear11_2_float([r.data[1], r.data[0]])

    def Read_Pin(self) -> float:
        r = self.I2C.ReadWrite([0x97], 2)
        if not r.success:
            return FLOAT_UNDIFEINED
        else:
            return self.I2C.Linear11_2_float([r.data[1], r.data[0]])


PSU1 = PSUx_Unit()
PSU2 = PSUx_Unit()

import numpy as np

def FindLevel(
    Target_Scope: iScope.ScopeInterface,
    Waveform: List[float],
    CheckPoint: float,
    Type: EdgeTriggerSlope,
    Torrance: float = 0.0,
    Offset: float = 0,
    All_Points: bool = False,
) -> List[float]:
    # 計算Main Output Delay
    # Waveform = Target_Scope.GetWaveformData(PSU.ChannelList.Vout)
    Time_Offset = Target_Scope.Timebase.Scale * 10 * Target_Scope.Timebase.Position / 100
    Waveform_Time_Unit = Target_Scope.GetWaveformTimeUnit()

    if not Setting.VISA_Send_Enable:
        Waveform_Time_Unit = 0.01
    Torrance_Point = Torrance / Waveform_Time_Unit

    Offset_Point = Offset / Waveform_Time_Unit
    if Offset_Point == 0:
        Offset_Point = 1
    Data_Find: List[float] = []
    # Upper
    nparray = np.array(Waveform)
    if Type == EdgeTriggerSlope.RISE:
        res = np.where((nparray[:-1] < CheckPoint) & (nparray[1:] >= CheckPoint))
    elif Type == EdgeTriggerSlope.FALL:
        res = np.where((nparray[:-1] > CheckPoint) & (nparray[1:] <= CheckPoint))
    else:
        res = np.where(((nparray[:-1] < CheckPoint) & (nparray[1:] >= CheckPoint)) | ((nparray[:-1] > CheckPoint) & (nparray[1:] <= CheckPoint)))
    Data_Find = res[0].tolist()

    # 計算開機時間
    for i, x in enumerate(Data_Find):
        Data_Find[i] = Data_Find[i] * Waveform_Time_Unit - Time_Offset

    return Data_Find

PSU = PSU_System()

class CursorSetting(Serializable_Data):
    def __init__(self, Channel: str, Level: float) -> None:
        super().__init__()
        self.ChannelSet = Channel
        self.Level = Level
        self.Slope = EdgeTriggerSlope.EITHER
from ...Library.importer import *
import copy

"""
此項目通用於
效率
**重要 還缺THD series功能
"""


class THD_Data(Serializable_Data):
    def __init__(self, CSVName=""):
        super().__init__(CSVName)
        self.Series: List[float] = [0.0]
        self.Total_Harmonic = JudgementData_Float()


class Measure_Setting(Serializable_Data):
    def __init__(self, CSVName=""):
        super().__init__(CSVName)
        self.Burning_Sec = 1.0
        self.Integration_Sec = 1
        self.Vin_Torrance = 1.0  # Unit: V
        self.Vin_Adjustment_Ratio = 0.5
        self.Vin_Adjustment_Retry = 50
        self.Average_Count = 32
        self.Harmonic_Order = 40
 

class LogUnit(ItemCore.LogUnit):
    def __init__(self) -> None:
        super().__init__()
        self.Input = Voltage_Data()
        self.RealInput = Voltage_Data()
        self.Turn_On_Delay = 3.0
        self.Measure_Setting = Measure_Setting()

        self.LoadLabel: List[str] = [""]
        self.LoadA: List[float] = [0.0]
        self.ITHD = THD_Data()
        self.VTHD = THD_Data()
        self.Efficiency = JudgementData_Float()

        self.Iin = JudgementData_Float()
        self.Vin = JudgementData_Float()
        self.Pin = JudgementData_Float()
        self.Power_Factor = JudgementData_Float()

        self.Vout = [JudgementData_Float()]
        self.Iout = [JudgementData_Float()]
        self.Pout = JudgementData_Float()

        self.Iin_History = [0.0]
        self.Vin_History = [0.0]
        self.Pin_History = [0.0]
        self.Power_Factor_History = [0.0]

        self.Remark = ""


class TestItem(ItemCore.TestItem):
    def __init__(self, Name: str = "", logUnit: LogUnit = LogUnit()) -> None:
        super().__init__(Name, logUnit)
        self.input_Condition_Str = ""

    def First_Run(self):
        super().First_Run()
        DC_Power_Supply[0].Set_Imax(4)
        DC_Power_Supply[0].Turn_ON(12)

    def Last_Run(self):
        super().Last_Run()
        DC_Power_Supply[0].Turn_OFF()
        Source[0].Turn_OFF()
        Delay(3, False)
        for L in Load:
            L.Load_OFF()
    
    def Run_Single_Condition(self, case: LogUnit):
        super().Run_Single_Condition(case)
        from Core.Instrument_Driver.Meter.Yokogawa_WT3000 import Yokogawa_WT3000
        C1 = self.Parameters[case.Index-2]
        C2 = self.Parameters[case.Index-1]
        if isinstance(C1,LogUnit) and isinstance(C2,LogUnit):
            restart = not (C1.Input == C2.Input)
        else:
            restart = True
        if restart:
            Source[0].Turn_OFF()
            Delay(3)
            Source[0].Turn_ON(case.Input)
            
        self.Parameter_Init(case)

        m = Meter[0]
        if isinstance(m, Yokogawa_WT3000):
            m._Set_Filter(0)
        m.Set_Voltage_Range_Auto(True)
        m.Set_Current_Range_Auto(True)
        # m.Set_Current_Range_Auto(False)
        # m.Set_Current_Range(10)
        m.Set_AVG_Count(case.Measure_Setting.Average_Count)

        self.PSU_Turn_ON(case)

        # self.Input_Voltage_Adjustment(case)
        self.Burning_PSU(case)

        # adjust source voltage to reach the target input voltage
        case.PassFail = self.Input_Voltage_Adjustment(case)
        Delay(case.Turn_On_Delay*10)

        if not case.PassFail:
            for L in Load:
                L.Load_OFF()
            return
        # if integration time is set, then use integration to get the power and current

        self.Get_Pin_Iin(case)
        import math

        for i in range(100):
            if math.isnan(m.Get_VoltageRMS()):
                Delay(1, False)
                continue
            # Get Vin, PF
            case.Power_Factor.Judge(m.GetPF())
            case.Vin.Judge(m.Get_VoltageRMS())

        # Get Pout, Iout, Vout
        pout_total = 0
        for i in range(len(case.Vout)):
            for j in range(10):
                try:
                    case.Vout[i].Judge(Load[i].read_voltage())
                    case.Iout[i].Judge(Load[i].read_current())
                    break
                except:
                    print("Load Communication Error")
                    continue
            pout_total += case.Vout[i].MeasureData * case.Iout[i].MeasureData
        case.Pout.Judge(pout_total)

        self.Get_Harmonic_Data(case)

        # case.ITHD.Series 還缺這個功能 :NUMeric:LIST?
        case.Efficiency.Judge(case.Pout.MeasureData / case.Pin.MeasureData * 100)

        self.Export_2_CSV()

    def Input_Voltage_Adjustment(self, case: LogUnit):
        """
        Adjusts the input voltage to match the target voltage within a specified tolerance.
        Parameters:
            case (LogUnit): The test case containing input voltage settings and measurement configurations.
        Returns:
            bool: True if the voltage adjustment is successful, False otherwise.
        Description:
            The function attempts to adjust the input voltage to match the target voltage (Volt_CMD) within a specified tolerance (case.Measure_Setting.Vin_Torrance).
            It retries the adjustment process up to a maximum number of times (case.Measure_Setting.Vin_Adjustment_Retry) if the measured voltage (Volt_Meter)
            differs from the target voltage. If the adjustment fails after the maximum retries, it logs the failure and returns False.
            If successful, it logs the success and returns True.
        """
        Meter[0].Set_AVG_Count(1)
        Delay(1, False)
        Volt_Meter = Meter[0].Get_VoltageRMS()
        Volt_CMD = case.Input.Voltage
        if case.RealInput.Voltage == FLOAT_UNDIFEINED:
            case.RealInput = case.Input
        retry_times = 0

        old_diff = 0
        offset = 0
        P = 1
        I = 1
        D = 1

        while abs(Volt_Meter - Volt_CMD) > case.Measure_Setting.Vin_Torrance and retry_times < case.Measure_Setting.Vin_Adjustment_Retry:
            retry_times += 1
            print("Target Voltage: {}, Measured Voltage: {}, Diff Voltage: {}".format(Volt_CMD, Volt_Meter, Volt_CMD - Volt_Meter))
            print("adjusting voltage({})...".format(retry_times))

            diff = (Volt_CMD - Volt_Meter)

            if old_diff == 0:
                old_diff = diff
            case.RealInput.Voltage += diff*case.Measure_Setting.Vin_Adjustment_Ratio*(1-retry_times/case.Measure_Setting.Vin_Adjustment_Retry)
            Source[0].Turn_ON(case.RealInput)
            old_diff = diff

            Delay(5, False)
            Volt_Meter = Meter[0].Get_VoltageRMS()
        Meter[0].Set_AVG_Count(case.Measure_Setting.Average_Count)
        if retry_times >= case.Measure_Setting.Vin_Adjustment_Retry:
            print("Voltage Adjustment Failed")
            case.Fail_Description.append("Voltage Adjustment Failed, retry times: {}".format(retry_times))
            return False
        else:
            print("Voltage Adjustment Success")
            print("Target Voltage: {}, Measured Voltage: {}, Diff Voltage: {}".format(Volt_CMD, Volt_Meter, Volt_CMD - Volt_Meter))
            return True

    def Parameter_Init(self, case: LogUnit):
        for i in range(len(case.LoadA)):
            if len(case.Vout) <= i:
                case.Vout.append(JudgementData_Float())
            if len(case.Iout) <= i:
                case.Iout.append(JudgementData_Float())

    def Burning_PSU(self, case: LogUnit):
        print("Burning PSU...")
        # delay for burning
        case.Iin_History = []
        case.Vin_History = []
        case.Pin_History = []
        case.Power_Factor_History = []
        TimeNow = time.time()
        while time.time() - TimeNow < case.Measure_Setting.Burning_Sec:
            case.Iin_History.append(Meter[0].Get_CurrentRMS())
            case.Vin_History.append(Meter[0].Get_VoltageRMS())
            case.Pin_History.append(Meter[0].Get_Power_Real())
            case.Power_Factor_History.append(Meter[0].GetPF())
            Delay(1, False)

    def PSU_Turn_ON(self, case: LogUnit):
        Source[0].Turn_ON(case.Input)
        Delay(case.Turn_On_Delay, False)
        for i in range(len(case.LoadA)):
            Load[i].Load_CC_ON_Amp(case.LoadA[i])

    def Get_Pin_Iin(self, case: LogUnit):
        print("Getting Pin and Iin...")
        from Core.Instrument_Driver.Meter.Yokogawa_WT3000 import Yokogawa_WT3000
        from Core.Instrument_Driver.Meter.Yokogawa_WT310 import Yokogawa_WT310

        m = Meter[0]
        if (isinstance(m, Yokogawa_WT3000) or isinstance(m,Yokogawa_WT310)) and case.Measure_Setting.Integration_Sec > 0:
            res = m.Integration(case.Measure_Setting.Integration_Sec)  # Watt, Current
            case.Pin.Judge(res[0])
            case.Iin.Judge(res[1])
        else:
            pin_total = 0
            iin_total = 0
            for i in range(case.Measure_Setting.Average_Count):
                pin_total += m.Get_Power_Real()
                iin_total += m.Get_CurrentRMS()
            case.Pin.Judge(pin_total / case.Measure_Setting.Average_Count)
            case.Iin.Judge(iin_total / case.Measure_Setting.Average_Count)

    def Get_Harmonic_Data(self, case: LogUnit):
        print("Getting THD Data...")
        from Core.Instrument_Driver.Meter.Yokogawa_WT3000 import Yokogawa_WT3000

        m = Meter[0]
        if isinstance(m, Yokogawa_WT3000):
            m.Harmonic_Order(case.Measure_Setting.Harmonic_Order)
            m._Set_Filter(5000)
            Delay(5, False)

        for i in range(100):

            case.ITHD.Total_Harmonic.Judge(m.GetITHD())
            case.VTHD.Total_Harmonic.Judge(m.GetVTHD())
            case.ITHD.Series = m.Get_Current_Harmonic_Series(1).Series
            case.VTHD.Series = m.Get_Voltage_Harmonic_Series(1).Series
            if case.ITHD.Series[0]<90:
                Delay(1, False)
            else:
                break

        if isinstance(m, Yokogawa_WT3000):
            m._Set_Filter(0)

import serial
import time
import math
from scanf import scanf

class DeviceController:
    def __init__(self, port):
        """
        初始化设备控制器
        """
        self.ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=serial.SEVENBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        if not self.ser.isOpen():
            raise Exception(f"无法打开串口 {port}")
        
        self.last_send_time = 0  # 上次发送指令的时间
        
    @staticmethod
    def calculate_checksum(data):
        etx = 0x03  # ETX字节
        checksum = (sum(data) + etx) & 0xFF  # 校验和是数据正文与ETX的和的低8位
        hex_str = format(checksum, '02X')
    
    # 将每个字符转换为其ASCII值，并形成bytearray
        byte_array = bytearray([ord(hex_str[0])]) + bytearray([ord(hex_str[1])])
        return byte_array
    
    @staticmethod
    def print_echo(data):
        hex_data = data.hex(" ")
        ascii_data = ''.join([chr(byte) if 32 <= byte <= 126 else '.' for byte in data])
        print(f"\n回显数据 (ASCII): {ascii_data}")
        print(f"回显数据 (HEX): {hex_data}\n")
    
    def send_instruction(self, command, need_response=False):
        # 确保命令之间的延迟大于等于500ms
        current_time = time.time()
        delay = current_time - self.last_send_time
        if delay < 0.5:  # 如果上次发送时间小于500ms之前
            time.sleep(0.5 - delay) #日文版手册推荐指令时间500ms
            
        data = bytearray(command, 'ascii')
        checksum = self.calculate_checksum(data)
        enq, etx = 0x05, 0x03
        instruction = bytearray([enq]) + data + bytearray([etx]) + checksum

        # 清空接收缓冲区
        self.ser.reset_input_buffer()
        
        print(f"发送的指令: {instruction.hex(' ')}")
        self.ser.write(instruction)

        received_data = bytearray()
        start_time = time.time()
        first_etx_received = False
        ack_received_count = 0

        while True:
            if self.ser.in_waiting > 0:
                byte = self.ser.read(1)
                received_data.extend(byte)
                if byte == b'\x03':
                    if not first_etx_received:
                        first_etx_received = True
                    else:
                        break
                        
                elif not need_response and ack_received_count >= 2:
                    break
                else:
                    ack_received_count += 1  # 增加ACK计数器
                    
            if time.time() - start_time > 5:
                received_data = bytearray()
                break

        self.print_echo(received_data)
        self.last_send_time = time.time()  # 更新最后一次发送的时间
        
        return received_data
    
    def set_voltage(self, voltage, memoryObj="workspace"):
        memoryObjCode = ""
        if (memoryObj == "workspace"):
            memoryObjCode = "A"
        elif (memoryObj == "memory1"):
            memoryObjCode = "E"
        elif (memoryObj == "memory2"):
            memoryObjCode = "J"
        elif (memoryObj == "memory3"):
            memoryObjCode = "N"
        else:
            return {"code": -1, "msg": "Invalid memory object"}
        
        self.send_instruction(f"AV{memoryObjCode}{voltage:.3f}")
        return {"code": 0, "msg": "Success"}
    def set_current(self, current, is_uaAccuracy = False, memoryObj="workspace"):
        memoryObjCode = ""
        if (is_uaAccuracy == False):
            if (memoryObj == "workspace"):
                memoryObjCode = "A"
            elif (memoryObj == "memory1"):
                memoryObjCode = "E"
            elif (memoryObj == "memory2"):
                memoryObjCode = "J"
            elif (memoryObj == "memory3"):
                memoryObjCode = "N"
            else:
                return {"code": -1, "msg": "Invalid memory object"}
        else:
            # 检查一下输入电流是否小于等于1A
            if (current > 1):
                return {"code": -1, "msg": "In uaAccuracy, The current value should be less than or equal to 1A"}
            
            if (memoryObj == "workspace"):
                memoryObjCode = "B"
            elif (memoryObj == "memory1"):
                memoryObjCode = "F"
            elif (memoryObj == "memory2"):
                memoryObjCode = "K"
            elif (memoryObj == "memory3"):
                memoryObjCode = "P"
            else:
                return {"code": -1, "msg": "Invalid memory object"}
        
        self.send_instruction(f"AA{memoryObjCode}{current:.3f}")
        return {"code": 0, "msg": "Success"}

    #写一个函数用于选择输出，之行为PR0/PR1/PR2/PR3 分别为：工作区、记忆1、记忆2、记忆3，传入参数memoryObj
    def select_output(self, memoryObj):
        if (memoryObj == "workspace"):
            self.send_instruction("APR0")
        elif (memoryObj == "memory1"):
            self.send_instruction("APR1")
        elif (memoryObj == "memory2"):
            self.send_instruction("APR2")
        elif (memoryObj == "memory3"):
            self.send_instruction("APR3")
        else:
            return {"code": -1, "msg": "Invalid memory object"}
        return {"code": 0, "msg": "Success"}
    
    def control_output(self, enable):
        """控制电源输出，enable为True时开启输出，False时关闭"""
        self.send_instruction("ASW1" if enable else "ASW0")
        return {"code": 0, "msg": "Success"}
    
    def unlock_panel(self):
        self.send_instruction("ALC1")
    
    def toggle_protection(self, enable=True):
        self.send_instruction("APT1" if enable else "APT0")
    
    def getOutputStatus(self):
        # 执行指令ST0，返回：
        # 回显数据 (ASCII): .AST0.1B.A.@MS0,01,1200,0200,2150,0000.5D
        # 回显数据 (HEX): 05 41 53 54 30 03 31 42 06 41 05 40 4d 53 30 2c 30 31 2c 31 32 30 30 2c 30 32 30 30 2c 32 31 35 30 2c 30 30 30 30 03 35 44
        # MS0, 2字符地址，4字符电压（换算到实际的电压需要先/100,然后用第二位小数四舍五入得到第三位小数），4字符电流（换算到实际的电流需要先/100,然后用第二位小数四舍五入得到第三位小鼠）
        received_data = self.send_instruction("AST4", need_response=True)
        if received_data:
            # 找到实际数据的起始位置
            start_index = received_data.find(b'MS4')
            if start_index == -1:
                return {"code": -1, "msg": "未找到有效数据起始位置"}
            
            # 解析返回的数据
            raw_result = scanf("MS4,%d,%f,%f,%f,%d", received_data[start_index:].decode())
            voltage = raw_result[1]
            current = raw_result[2]
            OVP = raw_result[3]
            is_CC = raw_result[4]
            # 调试打印
            print(f"电压: {voltage} V")
            print(f"电流: {current} A")
            print(f"OVP: {OVP} V")
            print(f"CC状态: {is_CC}")
            return {"code": 0, "msg": "Success", "voltage": voltage, "current": current, "OVP": OVP, "is_CC": is_CC}
        
    def getMemoryPreset(self):
        received_data = self.send_instruction("AST5", need_response=True)
        if received_data:
            # 找到实际数据的起始位置
            start_index = received_data.find(b'MS5')
            # 有没有类似C语言的scanf函数，可以直接从字符串中提取数字？
            # @MS5,01,1.234,2.333,0.0000,3.300,0.500,0.5000,5.000,0.150,0.1500,12.000,2.000,0.3152.13
            # @MS5,设备地址,工作区电压，工作区电流1ma档，工作区电流0.1ma档，记忆1电压，记忆1电流1ma档，记忆1电流0.1ma档，记忆2电压，记忆2电流1ma档，记忆2电流0.1ma档，记忆3电压，记忆3电流1ma档，记忆3电流0.1ma档
            if start_index == -1:
                return {"code": -1, "msg": "未找到有效数据起始位置"}
            # 删除末尾的0x03
            received_data = received_data[:-1]
            raw_result = scanf("MS5,%d,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f", received_data[start_index:].decode())
            print(raw_result)
            #需要输出一个树形结构，首先一开始有4个节点分别是工作区、记忆1、记忆2、记忆3，每个节点下面有3个子节点分别是电压、电流1ma档、电流0.1ma档
            reselt = {
                "workspace": {
                    "voltage": raw_result[1],
                    "current": raw_result[2],
                    "current_ua": raw_result[3]
                },
                "memory1": {
                    "voltage": raw_result[4],
                    "current": raw_result[5],
                    "current_ua": raw_result[6]
                },
                "memory2": {
                    "voltage": raw_result[7],
                    "current": raw_result[8],
                    "current_ua": raw_result[9]
                },
                "memory3": {
                    "voltage": raw_result[10],
                    "current": raw_result[11],
                    "current_ua": raw_result[12]
                }
            }
            print(reselt)
            return {"code": 0, "msg": "Success", "data": reselt}
            
    def close(self):
        self.ser.close()

def breathing_light(controller, duration, min_voltage, max_voltage, cycle_time):#@MS5,01,1.234,2.333,0.0000,3.300,0.500,0.5000,5.000,0.150,0.1500,12.000,2.000,0.3152.13
    start_time = time.time()
    controller.set_current(0.05)
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        t = (elapsed % cycle_time) / cycle_time  # Normalize to [0, 1]
        voltage = min_voltage + (max_voltage - min_voltage) * (math.sin(math.pi * t) ** 2)
        controller.set_voltage(voltage)
    
    # Safety shutdown after the demo
    controller.control_output(False)
    controller.set_voltage(0)
    controller.set_current(0)
    controller.toggle_protection(False)
    controller.unlock_panel()

if __name__ == "__main__":
    # 用户可以在这里指定串口名称，例如 '/dev/ttyUSB0' 或 'COM47'
    controller = DeviceController(port='COM47')
    #关闭输出
    controller.control_output(False)
    
    
    #设定工作区电压为1.5V， 电流为0.15A
    controller.set_voltage(1.5)
    controller.set_current(1.5)
    controller.set_current(0.15, is_uaAccuracy=True)
    #设置记忆1电压为3.3V，电流为1A，ua档0.15A
    controller.set_voltage(3.3, memoryObj="memory1")
    controller.set_current(1, memoryObj="memory1")
    controller.set_current(0.15, is_uaAccuracy=True, memoryObj="memory1")
    #设置记忆2电压为5V，电流为2A，ua档1A
    controller.set_voltage(5, memoryObj="memory2")
    controller.set_current(2, memoryObj="memory2")
    controller.set_current(1, is_uaAccuracy=True, memoryObj="memory2")
    #设置记忆3电压为12V，电流为4A，ua档1A
    controller.set_voltage(12, memoryObj="memory3")
    controller.set_current(4, memoryObj="memory3")
    controller.set_current(1, is_uaAccuracy=True, memoryObj="memory3")
    time.sleep(1)
    #获取预设值
    controller.getMemoryPreset()
    
    #演示打开输出保护，切换到记忆1，打开输出，3秒后关闭输出
    controller.toggle_protection(True)
    controller.select_output("memory1")
    controller.control_output(True)
    time.sleep(3)
    controller.control_output(False)
    
    #演示切换记忆2，打开输出，3秒后关闭输出
    controller.select_output("memory2")
    controller.control_output(True)
    time.sleep(3)
    controller.control_output(False)
    
    #演示切换记忆3，打开输出，3秒后关闭输出
    controller.select_output("memory3")
    controller.control_output(True)
    time.sleep(3)
    controller.control_output(False)
    
    #设置工作区输出1V 电流0.1A 使能输出 切换到工作区
    controller.set_voltage(0)
    controller.set_current(0)
    controller.select_output("workspace")
    controller.control_output(False)
    
    
    try:
        #运行呼吸灯DEMO
        breathing_light(controller, 15, 2.5, 3.3, 2.5)
    finally:
        # 关闭串口连接
        controller.close()




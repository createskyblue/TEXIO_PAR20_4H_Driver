import serial
import time
import math

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
        self.voltage_setting = None  # 记忆电压设置
        self.current_setting = None  # 记忆电流设置
        
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
    
    def send_instruction(self, command):
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

        while True:
            if self.ser.in_waiting > 0:
                byte = self.ser.read(1)
                if byte == b'\x03':
                    if not first_etx_received:
                        first_etx_received = True
                        received_data.extend(byte)
                    else:
                        received_data.extend(byte)
                        break
                else:
                    received_data.extend(byte)

            if time.time() - start_time > 0.5:
                received_data = bytearray()
                break

        if received_data:
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
        self.voltage_setting = voltage  # 更新记忆电压设置
        return {"code": 0, "msg": "Success"}
    
    def get_voltage(self):
        """获取当前设定的电压"""
        return self.voltage_setting
    
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
        self.current_setting = current  # 更新记忆电流设置
        return {"code": 0, "msg": "Success"}
    
    def get_current(self):
        """获取当前设定的电流"""
        return self.current_setting
    
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
    
    def syncOutputStatus(self):
        # 执行指令ST0，返回：
        # 回显数据 (ASCII): .AST0.1B.A.@MS0,01,1200,0200,2150,0000.5D
        # 回显数据 (HEX): 05 41 53 54 30 03 31 42 06 41 05 40 4d 53 30 2c 30 31 2c 31 32 30 30 2c 30 32 30 30 2c 32 31 35 30 2c 30 30 30 30 03 35 44
        # MS0, 2字符地址，4字符电压（换算到实际的电压需要先/100,然后用第二位小数四舍五入得到第三位小数），4字符电流（换算到实际的电流需要先/100,然后用第二位小数四舍五入得到第三位小鼠）
        received_data = self.send_instruction("AST0")
        if received_data:
            # 找到实际数据的起始位置
            start_index = received_data.find(b'MS0')
            if start_index == -1:
                return {"code": -1, "msg": "未找到有效数据起始位置"}
            
            # 解析返回的数据
            voltage = int(received_data[start_index+7:start_index+11]) / 100
            current = int(received_data[start_index+12:start_index+16]) / 100
            power = voltage * current
            output_status = ""
            # 调试打印
            print(f"电压: {voltage} V")
            print(f"电流: {current} A")
            print(f"功率: {power} W")
            print(f"输出状态: {output_status}")
            
            return {"code": 0, "msg": "Success", "voltage": voltage, "current": current, "power": power, "output_status": output_status}
    def close(self):
        self.ser.close()

def breathing_light(controller, duration, min_voltage, max_voltage, cycle_time):
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
    
    try:
        while(1):
            controller.syncOutputStatus()
            time.sleep(1)
    finally:
        # 关闭串口连接
        controller.close()




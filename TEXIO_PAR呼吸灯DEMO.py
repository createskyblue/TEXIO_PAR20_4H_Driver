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
        
        print(f"发送的指令: {instruction.hex(' ')}")
        self.ser.write(instruction)
        time.sleep(0.1)  # 给设备一些时间响应
        
        received_data = self.ser.read(self.ser.in_waiting)
        if received_data:
            self.print_echo(received_data)

        self.last_send_time = time.time()  # 更新最后一次发送的时间
    
    def set_voltage(self, voltage):
        self.send_instruction(f"AVA{voltage:.3f}")
        self.voltage_setting = voltage  # 更新记忆电压设置
    
    def get_voltage(self):
        """获取当前设定的电压"""
        return self.voltage_setting
    
    def set_current(self, current):
        self.send_instruction(f"AAA{current:.3f}")
        self.current_setting = current  # 更新记忆电流设置
    
    def get_current(self):
        """获取当前设定的电流"""
        return self.current_setting
    
    def control_output(self, enable):
        """控制电源输出，enable为True时开启输出，False时关闭"""
        self.send_instruction("ASW1" if enable else "ASW0")
    
    def unlock_panel(self):
        self.send_instruction("ALC1")
    
    def toggle_protection(self, enable=True):
        self.send_instruction("APT1" if enable else "APT0")
    
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
        # 设置初始电压为0
        controller.set_voltage(0)
        
        # 启用输出保护
        controller.toggle_protection(True)
        
        # 控制电源输出（例如：开启电源）
        controller.control_output(True)
        
        # 设置初始电流（假设为1A）
        controller.set_current(1.0)
        
        # 运行呼吸灯demo
        breathing_light(controller, 15, 2.5, 3.3, 2.5)
    finally:
        # 关闭串口连接
        controller.close()




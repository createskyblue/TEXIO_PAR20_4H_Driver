import serial
import time

# 打开串口
ser = serial.Serial(
    port='COM47',  # 根据实际情况替换为您的串口号
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

if ser.isOpen():
    print(f"{ser.port} is open")
else:
    print("Failed to open serial port")
    exit()
    
base_packet = [0x05, 0x41, 0x53, 0x57, 0x31, 0x03]  # 基础数据包
start_value = 0x0000  # 开始值
end_value = 0xFFFF  # 结束值

for i in range(start_value, end_value + 1):
    packet = base_packet.copy()
    packet.append(i >> 8)  # 添加高字节
    packet.append(i & 0xFF)  # 添加低字节
    
    ser.write(packet)
    print(f"Sent: {packet}")
    
    time.sleep(0.1)  # 每条指令间隔100ms

print("Data transmission completed.")
ser.close()  # 关闭串口
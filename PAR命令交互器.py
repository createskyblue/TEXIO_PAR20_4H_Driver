import serial
import binascii
import time
# 函数：计算校验和
def calculate_checksum(data):
    etx = 0x03  # ETX字节
    checksum = (sum(data) + etx) & 0xFF  # 校验和是数据正文与ETX的和的低8位
    return checksum

# 打开串口COM47，波特率9600，无校验
ser = serial.Serial(
    port='COM47',           # 根据实际情况替换为您的串口号
    baudrate=9600,          # 波特率设置为9600
    bytesize=serial.SEVENBITS,  # 数据位设置为7
    parity=serial.PARITY_EVEN,  # 设置偶校验
    stopbits=serial.STOPBITS_ONE,  # 停止位设置为1
    timeout=1               # 超时时间设置为1秒
)
# 函数：打印回显数据（以HEX和ASCII格式显示）
def print_echo(data):
    hex_data = data.hex(" ")
    ascii_data = ''.join([chr(byte) if 32 <= byte <= 126 else '.' for byte in data])  # 转换为ASCII，非打印字符用'.'表示
    print(f"\n回显数据 (ASCII): {ascii_data}")
    print(f"回显数据 (HEX): {hex_data}\n")
    
def decimal_to_custom_bytearray(decimal_value):
    # 将十进制值转换为十六进制字符串，并去掉前缀'0x'，同时确保始终有两位数
    hex_str = format(decimal_value, '02X')
    
    # 将每个字符转换为其ASCII值，并形成bytearray
    byte_array = bytearray([ord(hex_str[0])]) + bytearray([ord(hex_str[1])])
    
    return byte_array

# 死循环：持续等待用户输入，发送指令并回显接收到的数据
while True:
    # 用户输入数据正文
    data_input = input("请输入数据正文（ASCII字符）：")

    # 将输入的 ASCII 字符转换为字节数组
    data = bytearray(data_input, 'ascii')

    # 计算校验和
    checksum = calculate_checksum(data)

    # 构造完整指令：ENQ + 数据正文 + ETX + 校验和
    enq = 0x05  # ENQ字节
    etx = 0x03  # ETX字节

    # 创建最终的指令：ENQ + 数据正文 + ETX + 校验和（拆分后的高低位ASCII）
    instruction = bytearray([enq]) + data + bytearray([etx]) + decimal_to_custom_bytearray(checksum)

    # 打印发送的指令，优化输出为 %02X %02X 格式
    print("发送的指令: " + instruction.hex(" "))

    # 发送指令到串口
    ser.write(instruction)
    
    接收计时器 = time.time()
    接收缓冲区 = bytearray()
    while time.time() - 接收计时器 < 0.3:
        # 从串口读取一个字节
        byte = ser.read(1)
        if byte:
            接收缓冲区 += byte
            接收计时器 = time.time()
            
    # 打印回显数据
    print_echo(接收缓冲区)

# 关闭串口
ser.close()

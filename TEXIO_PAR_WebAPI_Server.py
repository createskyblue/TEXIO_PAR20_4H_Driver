import serial
import time
import math
from scanf import scanf
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio  # 添加 asyncio 模块

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中建议设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            timeout=0.1
        )
        if not self.ser.isOpen():
            raise Exception(f"无法打开串口 {port}")
        
        self.last_send_time = 0  # 上次发送指令的时间
        self.lock = asyncio.Lock()  # 添加异步锁
        self.last_get_output_status_time = 0  # 添加记录上次调用get_output_status的时间

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
        print(f"数据 (ASCII): {ascii_data}")
        print(f"数据 (HEX): {hex_data}\n")
    
    async def send_instruction(self, command, need_response=False):  # 修改为异步方法
        data = bytearray(command, 'ascii')
        checksum = self.calculate_checksum(data)
        enq, etx = 0x05, 0x03
        instruction = bytearray([enq]) + data + bytearray([etx]) + checksum

        # 清空接收缓冲区
        self.ser.reset_input_buffer()
        
        print("发送的指令:")
        self.print_echo(instruction)
        self.ser.write(instruction)

        接收缓冲区 = bytearray()
        字符接收超时 = 0.1  # 每个字符的接收超时时间
        最后接收时间 = time.time()
        
        while (time.time() - 最后接收时间) < 字符接收超时:
            # 从串口读取一个字节
            byte = self.ser.read(1)
            if byte:
                接收缓冲区 += self.ser.read(1)
                最后接收时间 = time.time()
                    
        print(f"接收数据耗时: {time.time() - 最后接收时间:.3f} 秒")
                
        print("接收到的数据:")
        self.print_echo(接收缓冲区)
        
        return 接收缓冲区 if need_response else None
    
    async def set_voltage(self, voltage, memoryObj="workspace"):  # 修改为异步方法
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
        
        async with self.lock:  # 使用异步锁
            await self.send_instruction(f"AV{memoryObjCode}{voltage:.3f}")
        return {"code": 0, "msg": "Success"}
    
    async def set_current(self, current, is_uaAccuracy = False, memoryObj="workspace"):  # 修改为异步方法
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
        
        async with self.lock:  # 使用异步锁
            await self.send_instruction(f"AA{memoryObjCode}{current:.3f}")
        return {"code": 0, "msg": "Success"}

    #写一个函数用于选择输出，之行为PR0/PR1/PR2/PR3 分别为：工作区、记忆1、记忆2、记忆3，传入参数memoryObj
    async def select_output(self, memoryObj):  # 修改为异步方法
        if (memoryObj == "workspace"):
            await self.send_instruction("APR0")
        elif (memoryObj == "memory1"):
            await self.send_instruction("APR1")
        elif (memoryObj == "memory2"):
            await self.send_instruction("APR2")
        elif (memoryObj == "memory3"):
            await self.send_instruction("APR3")
        else:
            return {"code": -1, "msg": "Invalid memory object"}
        return {"code": 0, "msg": "Success"}
    
    async def control_output(self, enable):  # 修改为异步方法
        """控制电源输出，enable为True时开启输出，False时关闭"""
        async with self.lock:  # 使用异步锁
            await self.send_instruction("ASW1" if enable else "ASW0")
        return {"code": 0, "msg": "Success"}
    
    async def unlock_panel(self):  # 修改为异步方法
        await self.send_instruction("ALC1")
    
    async def toggle_protection(self, enable=True):  # 修改为异步方法
        await self.send_instruction("APT1" if enable else "APT0")
        
    # RA0 和 RA1 来切换是否使用微安模式，RA1为激活
    async def set_ua_accuracy(self, enable):
        await self.send_instruction("ARA1" if enable else "ARA0")
        
        
    #增加方法，获取系统状态，指令ST2，响应数据为：.AST2.1D.A.@MS2,01,1,0,1,0,0,0 响应数据含义：@MS2,2字符设备地址，1字符OVP状态，1字符输出是否开启，1字符输出保护是否开启，1字符未知，1字符记忆预设选择（0：工作区，1：记忆1，2：记忆2，3：记忆3），1字符微安精度是否选择
    async def getSystemStatus(self):  # 修改为异步方法
        async with self.lock:
            received_data = await self.send_instruction("AST2", need_response=True)
        if received_data:
            # 找到实际数据的起始位置
            start_index = received_data.find(b'MS2')
            if start_index == -1:
                return {"code": -1, "msg": "未找到有效数据起始位置"}
            
            # 解析返回的数据
            raw_result = scanf("MS2,%d,%d,%d,%d,%d,%d,%d", received_data[start_index:].decode())
            return {"code": 0, "msg": "Success", "data": {"OVP/电压电流显示": raw_result[1], "is_output_on": raw_result[2], "is_protection_on": raw_result[3], "トラッキング": raw_result[4], "memory_preset": raw_result[5], "is_ua_accuracy": raw_result[6]}}
    
    async def getOutputStatus(self):  # 修改为异步方法
        async with self.lock:  # 使用异步锁
            received_data = await self.send_instruction("AST4", need_response=True)
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
            is_CC = raw_result[4]==1000
            # 调试打印
            print(f"电压: {voltage} V")
            print(f"电流: {current} A")
            print(f"OVP: {OVP} V")
            print(f"CC状态: {is_CC}")
            return {"code": 0, "msg": "Success", "data":{"voltage": voltage, "current": current, "OVP": OVP, "is_CC": is_CC}}
    
    async def getMemoryPreset(self):  # 修改为异步方法
        async with self.lock:  # 使用异步锁
            received_data = await self.send_instruction("AST5", need_response=True)
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

# 创建全局的 DeviceController 实例
controller = DeviceController(port='COM47')

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

class SetVoltageRequest(BaseModel):
    voltage: float
    memoryObj: str = "workspace"

class SetCurrentRequest(BaseModel):
    current: float
    is_uaAccuracy: bool = False
    memoryObj: str = "workspace"

class SelectOutputRequest(BaseModel):
    memoryObj: str

@app.post("/api/set_voltage")
async def set_voltage(request: SetVoltageRequest):
    response = await controller.set_voltage(request.voltage, request.memoryObj)  # 使用异步调用
    return response

@app.post("/api/set_current")
async def set_current(request: SetCurrentRequest):
    response = await controller.set_current(request.current, request.is_uaAccuracy, request.memoryObj)  # 使用异步调用
    return response

@app.post("/api/select_output")
async def select_output(request: SelectOutputRequest):
    response = await controller.select_output(request.memoryObj)  # 使用异步调用
    return response

@app.post("/api/control_output")
async def control_output(enable: bool):
    response = await controller.control_output(enable)  # 使用异步调用
    return response

@app.post("/api/unlock_panel")
async def unlock_panel():
    await controller.unlock_panel()  # 使用异步调用
    return {"code": 0, "msg": "Success"}

@app.post("/api/toggle_protection")
async def toggle_protection(enable: bool = True):
    await controller.toggle_protection(enable)  # 使用异步调用
    return {"code": 0, "msg": "Success"}

@app.post("/api/set_ua_accuracy")
async def set_ua_accuracy(enable: bool):
    await controller.set_ua_accuracy(enable)  # 使用 await 关键字调用异步方法
    return {"code": 0, "msg": "Success"}

@app.get("/api/get_output_status")
async def get_output_status():
    response = await controller.getOutputStatus()  # 使用异步调用
    return response

@app.get("/api/get_memory_preset")
async def get_memory_preset():
    response = await controller.getMemoryPreset()  # 使用异步调用
    return response

@app.get("/api/getSystemStatus")
async def getSystemStatus():
    response = await controller.getSystemStatus()  # 使用异步调用
    return response

#启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# PAR20-4H 驱动程序

## 项目简介
PAR20-4H驱动程序是一个用于控制PAR20-4H电源设备的Python驱动程序，支持通过串口和HTTP接口进行设备控制。该驱动程序提供了设置电压、电流、选择输出、控制输出等功能。

## 环境依赖
- Python 3.x
- `pyserial` 库
- `fastapi` 库（仅用于Web API服务器）
- `uvicorn` 库（仅用于Web API服务器）
- `scanf` 库

```bash
pip install pyserial scanf fastapi uvicorn
```

## 使用说明
### 初始化与连接电源设备
1. 确保电源设备已正确连接到计算机的串口。
2. 在代码中指定正确的串口号，例如 `COM47` 或 `/dev/ttyUSB0`。

### 运行呼吸灯演示脚本
1. 打开 `TEXIO_PAR呼吸灯DEMO.py` 文件。
2. 运行脚本：
   ```bash
   python TEXIO_PAR呼吸灯DEMO.py
   ```

### 启动Web API服务器
1. 打开 `TEXIO_PAR_WebAPI_Server.py` 文件。
2. 运行脚本：
   ```bash
   python TEXIO_PAR_WebAPI_Server.py
   ```
3. 访问 `http://localhost:8000/docs` 查看API文档。

### 使用串口命令交互器
1. 打开 `PAR命令交互器.py` 文件。
2. 运行脚本：
   ```bash
   python PAR命令交互器.py
   ```
3. 输入数据正文（ASCII字符），程序将自动计算校验和并发送指令到串口，同时接收并显示回显数据。

## 注意事项
- 确保串口设备驱动已正确安装。
- 在使用Web API时，确保防火墙允许访问端口8000。
- 在使用串口命令交互器时，确保输入的指令格式正确。

## 参考资料
- [数码之家介绍](https://www.mydigit.cn/forum.php?mod=viewthread&tid=497094&page=1&extra=#pid17548377)
- [演示视频](https://www.bilibili.com/video/BV1ozNWewE1k/)
- [ApiPost 调用http接口控制电源文档](https://console-docs.apipost.cn/preview/59224492af6b8c08/f786640544847da4)
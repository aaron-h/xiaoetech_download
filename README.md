# M3U8视频下载器

## 项目简介

M3U8视频下载器是一个功能强大的工具，用于下载和转换M3U8格式的视频文件。该工具支持多种用户界面，包括Web界面、终端界面和GUI界面，适用于不同用户的需求。

## 功能特点

- ✅ **支持多种M3U8格式**：兼容小鹅通、腾讯云等多种平台的M3U8视频
- ✅ **多种用户界面**：提供Web界面、终端界面和GUI界面
- ✅ **批量下载**：支持同时下载多个M3U8链接
- ✅ **多线程下载**：可配置线程数，提高下载速度
- ✅ **实时进度显示**：实时显示下载进度和状态
- ✅ **动态日志记录**：详细的日志输出，便于调试和问题排查
- ✅ **自动转换格式**：使用FFmpeg自动将M3U8转换为MP4格式
- ✅ **跨平台支持**：支持macOS、Windows、Linux系统

## 系统要求

- **操作系统**：macOS 10.12+ / Windows 7+ / Linux
- **Python版本**：Python 3.6或更高版本
- **FFmpeg**：必须安装FFmpeg工具
- **网络环境**：稳定的互联网连接

## 安装步骤

### 1. 安装Python

#### macOS
系统自带Python 3，或使用Homebrew安装：
```bash
brew install python3
```

#### Windows
1. 访问 [Python官网](https://www.python.org/) 下载安装包
2. 运行安装包，勾选"Add Python to PATH"
3. 点击"Install Now"

#### Linux
使用包管理器安装：
```bash
sudo apt install python3 python3-pip  # Ubuntu/Debian
sudo yum install python3 python3-pip  # CentOS/RHEL
```

### 2. 安装FFmpeg

#### macOS
```bash
brew install ffmpeg
```

#### Windows
1. 访问 [FFmpeg官网](https://ffmpeg.org/download.html) 下载Windows版本
2. 解压到任意目录（如C:\ffmpeg）
3. 将该目录添加到系统环境变量PATH中

#### Linux
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg  # CentOS/RHEL
```

### 3. 安装Python依赖

```bash
pip install flask requests
```

## 使用方法

### 方法1：Web界面（推荐）

Web界面是最直观易用的方式，适合大多数用户。

#### 步骤1：启动Web服务器

```bash
python3 m3u8_web_ui.py
```

#### 步骤2：访问Web界面

在浏览器中打开：http://127.0.0.1:5001

#### 步骤3：下载视频

1. 在文本框中输入一个或多个M3U8链接（每行一个）
2. 调整下载配置（线程数、超时时间、重试次数）
3. 点击"开始下载"按钮
4. 查看实时进度和日志
5. 下载完成后，在"已下载文件"中查看结果

### 方法2：终端界面

终端界面适合习惯命令行操作的用户。

#### 步骤1：启动终端界面

```bash
python3 m3u8_terminal_ui.py
```

#### 步骤2：使用终端菜单

按数字键选择功能：
- `1`：添加M3U8链接
- `2`：设置输出目录
- `3`：设置线程数
- `4`：开始下载
- `5`：查看日志
- `6`：退出

### 方法3：GUI界面

GUI界面适合Windows用户，提供图形化操作。

#### 步骤1：启动GUI

```bash
python3 m3u8_gui_downloader.py
```

#### 步骤2：使用GUI界面

1. 在输入框中粘贴M3U8链接
2. 设置输出目录和线程数
3. 点击"开始下载"按钮
4. 查看进度条和日志

## 配置选项

### 通用配置

| 配置项 | 默认值 | 说明 |
|-------|-------|------|
| 线程数 | 8 | 同时下载的线程数量，推荐8-16 |
| 超时时间 | 60秒 | 每个请求的最大等待时间 |
| 重试次数 | 3 | 下载失败时的重试次数 |
| 输出目录 | ./video_output | 视频文件保存目录 |

### Web界面特殊配置

| 配置项 | 默认值 | 说明 |
|-------|-------|------|
| Web端口 | 5001 | Web服务器监听端口 |
| 调试模式 | 开启 | Flask调试模式 |
| 访问地址 | 0.0.0.0 | 允许所有IP访问 |

## 常见问题

### Q1: 启动Web服务器时提示端口被占用

**解决方法**：修改代码中的PORT变量，使用其他端口：

```python
# 在m3u8_web_ui.py中修改
PORT = 5002  # 改为其他可用端口
```

### Q2: 下载失败，提示"未找到ffmpeg"

**解决方法**：
1. 确保已正确安装FFmpeg
2. 验证FFmpeg是否在系统PATH中：
   ```bash
   ffmpeg -version
   ```
3. 如果仍有问题，重新安装FFmpeg

### Q3: 下载速度很慢

**解决方法**：
1. 增加线程数（Web界面或终端界面中设置）
2. 检查网络连接是否稳定
3. 尝试减少同时下载的链接数量

### Q4: 视频下载后无法播放

**可能原因**：
1. M3U8链接无效或已过期
2. 网络中断导致下载不完整
3. FFmpeg转换失败

**解决方法**：
1. 检查M3U8链接是否仍可访问
2. 重新下载该视频
3. 查看日志中的错误信息

### Q5: Web界面无法访问

**解决方法**：
1. 检查服务器是否正在运行
2. 检查防火墙是否阻止了端口访问
3. 尝试使用localhost代替IP地址

## 测试脚本

项目包含完整的测试脚本，用于验证下载功能：

```bash
python3 test_m3u8_downloader.py
```

测试内容包括：
1. 下载M3U8文件
2. 检查下载的文件格式
3. 测试多线程下载

## 项目结构

```
├── m3u8_web_ui.py          # Web界面版本
├── m3u8_terminal_ui.py     # 终端界面版本
├── m3u8_gui_downloader.py  # GUI界面版本
├── xiaoe_downloader.py      # 初始小鹅通下载脚本
├── test_m3u8_downloader.py  # 测试脚本
├── templates/
│   └── index.html          # Web界面模板
├── M3U8_Downloader_User_Guide.md  # 用户使用指南
└── README.md               # 项目说明文档
```

## 许可证

本项目采用MIT许可证，详情请见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request，共同改进项目。

## 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues：https://github.com/aaron-h/xiaoetech_download/issues
- 邮件：[项目维护者邮箱]

## 更新日志

### v1.0.0 (2025-12-05)
- 初始版本
- 支持Web界面、终端界面和GUI界面
- 支持批量下载和多线程
- 支持实时进度显示和日志记录
- 支持多种M3U8格式
- 提供完整的测试脚本和用户指南

---

**祝您使用愉快！** 🎉

#!/usr/bin/env python3 
# -*- coding: utf-8 -*- 
""" 
M3U8视频下载器 - 终端交互界面
功能: 下载M3U8播放列表并使用ffmpeg合并为MP4文件
支持: 小鹅通、腾讯云等多种M3U8格式
更新时间: 2025-12-05 
""" 

import os
import re
import time
import subprocess
import shutil
import sys
import curses
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ================================ 配置区 ================================

# 默认并发线程数 
DEFAULT_THREAD_NUM = 8 

# 默认视频输出目录 
DEFAULT_OUTPUT_DIR = "./video_output" 

# 默认请求头 - 改进请求头配置，提高与不同服务器的兼容性
DEFAULT_HEADERS = { 
    "Accept": "*/*", 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
    "Referer": "https://",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://",
}

# 默认超时设置 (秒)
DEFAULT_REQUEST_TIMEOUT = 60

# 默认重试次数
DEFAULT_RETRY_COUNT = 3

# ====================================================================== 


class M3UDownloader:
    """M3U8下载器类"""
    
    def __init__(self, output_dir=DEFAULT_OUTPUT_DIR, thread_num=DEFAULT_THREAD_NUM, 
                 headers=DEFAULT_HEADERS, timeout=DEFAULT_REQUEST_TIMEOUT, retry_count=DEFAULT_RETRY_COUNT):
        """初始化下载器"""
        self.output_dir = output_dir
        self.thread_num = thread_num
        self.headers = headers
        self.timeout = timeout
        self.retry_count = retry_count
        self.session = requests.Session()
        self.session.headers.update(headers)
        
    def is_m3u8_file(self, file_path):
        """检查文件是否为M3U8格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(100)
                return '#EXTM3U' in content
        except:
            return False
    
    def download_file(self, url, output_path):
        """下载单个文件"""
        for i in range(self.retry_count):
            try:
                # 添加HTTPS证书验证选项，支持自签名证书
                response = self.session.get(url, timeout=self.timeout, verify=False)
                response.raise_for_status()
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            except Exception as e:
                if i == self.retry_count - 1:
                    return False
                time.sleep(2)
        return False
    
    def process_m3u8(self, m3u8_url, output_filename="output.mp4"):
        """处理M3U8文件并转换为MP4"""
        # 创建临时目录
        temp_dir = os.path.join(self.output_dir, f"temp_{int(time.time())}")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 自动调整Referer，提高下载成功率
            from urllib.parse import urlparse
            parsed_url = urlparse(m3u8_url)
            self.headers['Referer'] = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            self.headers['Origin'] = f"{parsed_url.scheme}://{parsed_url.netloc}"
            self.session.headers.update(self.headers)
            
            # 下载M3U8播放列表
            m3u8_path = os.path.join(temp_dir, "playlist.m3u8")
            if not self.download_file(m3u8_url, m3u8_path):
                return False, f"无法下载M3U8文件: {m3u8_url}"
            
            # 检查是否为有效的M3U8文件
            if not self.is_m3u8_file(m3u8_path):
                return False, f"下载的文件不是有效的M3U8格式: {m3u8_url}"
            
            # 处理M3U8文件中的相对路径
            with open(m3u8_path, 'r', encoding='utf-8') as f:
                m3u8_content = f.read()
            
            # 更新M3U8文件中的相对路径为绝对路径
            updated_content = []
            for line in m3u8_content.split('\n'):
                line = line.strip()
                # 处理相对路径的TS片段
                if line and not line.startswith('#') and not line.startswith('http'):
                    # 构建绝对路径
                    from urllib.parse import urljoin
                    absolute_url = urljoin(m3u8_url, line)
                    updated_content.append(absolute_url)
                else:
                    updated_content.append(line)
            
            # 保存更新后的M3U8文件
            with open(m3u8_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(updated_content))
            
            # 使用ffmpeg直接转换M3U8为MP4，添加更多兼容性参数
            output_path = os.path.join(self.output_dir, output_filename)
            # 构建带请求头的ffmpeg命令，支持加密视频和各种M3U8格式
            headers_str = ''
            for key, value in self.headers.items():
                headers_str += f'{key}: {value}\\r\\n'
            
            cmd = [
                "ffmpeg",
                "-headers", headers_str,
                "-i", m3u8_path,
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",  # 修复音频流
                "-y",  # 覆盖现有文件
                "-timeout", "60",  # 设置超时时间
                "-user_agent", self.headers.get("User-Agent", ""),
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return True, f"转换成功: {output_filename}"
            else:
                # 记录更详细的FFmpeg错误信息
                error_msg = result.stderr[-500:]  # 只显示最后500个字符
                return False, f"转换失败 (返回码: {result.returncode}): {error_msg}"
                
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def download_m3u8(self, m3u8_url, output_filename=None):
        """下载并处理M3U8"""
        # 生成输出文件名
        if not output_filename:
            # 从URL提取文件名或使用时间戳
            filename = re.search(r'([^/]+)\.m3u8', m3u8_url)
            if filename:
                output_filename = f"{filename.group(1)}.mp4"
            else:
                output_filename = f"video_{int(time.time())}.mp4"
        
        return self.process_m3u8(m3u8_url, output_filename)


class M3UTerminalUI:
    """M3U8下载器终端交互界面"""
    
    def __init__(self):
        """初始化终端界面"""
        self.screen = None
        self.m3u8_urls = []
        self.config = {
            "output_dir": DEFAULT_OUTPUT_DIR,
            "thread_num": DEFAULT_THREAD_NUM,
            "timeout": DEFAULT_REQUEST_TIMEOUT,
            "retry_count": DEFAULT_RETRY_COUNT
        }
        self.logs = []
        self.current_input = ""
        self.in_input_mode = False
        self.input_field = ""
    
    def init_curses(self):
        """初始化curses"""
        self.screen = curses.initscr()
        curses.curs_set(1)  # 显示光标
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.noecho()  # 不回显输入
        curses.cbreak()  # 立即处理输入
        self.screen.keypad(True)  # 启用键盘特殊键
    
    def cleanup_curses(self):
        """清理curses"""
        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()
    
    def add_log(self, message, color=0):
        """添加日志信息"""
        self.logs.append((message, color))
        # 限制日志数量
        if len(self.logs) > 20:
            self.logs.pop(0)
    
    def draw_header(self):
        """绘制头部"""
        height, width = self.screen.getmaxyx()
        header_text = "M3U8视频下载器 - 终端版"
        self.screen.addstr(0, 0, "=" * width, curses.A_BOLD)
        self.screen.addstr(1, (width - len(header_text)) // 2, header_text, curses.A_BOLD | curses.color_pair(1))
        self.screen.addstr(2, 0, "=" * width, curses.A_BOLD)
    
    def draw_menu(self):
        """绘制菜单"""
        menu_items = [
            "1. 添加M3U8链接",
            "2. 设置输出目录",
            "3. 设置线程数",
            "4. 开始下载",
            "5. 查看日志",
            "6. 退出"
        ]
        
        height, width = self.screen.getmaxyx()
        start_y = 4
        
        self.screen.addstr(start_y, 2, "菜单选项:", curses.A_BOLD | curses.color_pair(3))
        for i, item in enumerate(menu_items, start=1):
            self.screen.addstr(start_y + i, 4, item)
    
    def draw_status(self):
        """绘制状态"""
        height, width = self.screen.getmaxyx()
        status_y = height - 6
        
        self.screen.addstr(status_y, 0, "=" * width, curses.A_BOLD)
        self.screen.addstr(status_y + 1, 2, f"当前配置: 输出目录={self.config['output_dir']}, 线程数={self.config['thread_num']}", curses.color_pair(4))
        self.screen.addstr(status_y + 2, 2, f"已添加 {len(self.m3u8_urls)} 个M3U8链接")
        self.screen.addstr(status_y + 3, 2, "按对应数字键选择菜单选项...")
        self.screen.addstr(status_y + 4, 0, "=" * width, curses.A_BOLD)
    
    def draw_urls(self):
        """绘制已添加的URL"""
        height, width = self.screen.getmaxyx()
        start_y = 12
        
        if self.m3u8_urls:
            self.screen.addstr(start_y, 2, "已添加的M3U8链接:", curses.A_BOLD | curses.color_pair(3))
            for i, url in enumerate(self.m3u8_urls, start=1):
                if start_y + i < height - 8:  # 留出底部空间
                    display_url = url[:width - 10] + "..." if len(url) > width - 10 else url
                    self.screen.addstr(start_y + i, 4, f"{i}. {display_url}")
    
    def draw_logs(self):
        """绘制日志"""
        height, width = self.screen.getmaxyx()
        log_start_y = 12
        log_end_y = height - 8
        
        self.screen.addstr(log_start_y, 2, "日志输出:", curses.A_BOLD | curses.color_pair(3))
        
        # 显示最新的日志
        log_y = log_start_y + 1
        for log_msg, color in self.logs:
            if log_y < log_end_y:
                display_msg = log_msg[:width - 10] + "..." if len(log_msg) > width - 10 else log_msg
                if color == 0:
                    self.screen.addstr(log_y, 4, display_msg)
                else:
                    self.screen.addstr(log_y, 4, display_msg, curses.color_pair(color))
                log_y += 1
    
    def draw_input_field(self):
        """绘制输入字段"""
        height, width = self.screen.getmaxyx()
        input_y = height - 2
        
        self.screen.addstr(input_y, 0, "=" * width)
        if self.in_input_mode:
            self.screen.addstr(input_y + 1, 2, f"> {self.input_field}", curses.A_REVERSE)
        else:
            self.screen.addstr(input_y + 1, 2, f"> ", curses.A_REVERSE)
    
    def draw_screen(self, show_logs=False):
        """绘制整个屏幕"""
        self.screen.clear()
        self.draw_header()
        
        if not show_logs:
            self.draw_menu()
            self.draw_urls()
        else:
            self.draw_logs()
        
        self.draw_status()
        self.draw_input_field()
        self.screen.refresh()
    
    def get_user_input(self, prompt):
        """获取用户输入"""
        self.in_input_mode = True
        self.input_field = ""
        self.screen.addstr(10, 2, prompt, curses.A_BOLD)
        
        while True:
            self.draw_screen()
            key = self.screen.getch()
            
            if key == 10:  # Enter键
                self.in_input_mode = False
                return self.input_field
            elif key == 27:  # ESC键
                self.in_input_mode = False
                return None
            elif key == 127:  # 退格键
                if self.input_field:
                    self.input_field = self.input_field[:-1]
            elif 32 <= key <= 126:  # 可打印字符
                self.input_field += chr(key)
    
    def handle_menu(self, choice):
        """处理菜单选择"""
        if choice == '1':
            # 添加M3U8链接
            url = self.get_user_input("请输入M3U8链接 (按Enter确认，ESC取消):")
            if url and url.strip():
                self.m3u8_urls.append(url.strip())
                self.add_log(f"已添加M3U8链接: {url.strip()}", 1)
        elif choice == '2':
            # 设置输出目录
            dir_path = self.get_user_input("请输入输出目录 (默认: ./video_output):")
            if dir_path and dir_path.strip():
                self.config['output_dir'] = dir_path.strip()
                self.add_log(f"已设置输出目录: {dir_path.strip()}", 1)
            else:
                self.add_log("使用默认输出目录: ./video_output", 1)
        elif choice == '3':
            # 设置线程数
            thread_num = self.get_user_input(f"请输入线程数 (当前: {self.config['thread_num']}):")
            if thread_num and thread_num.isdigit():
                self.config['thread_num'] = int(thread_num)
                self.add_log(f"已设置线程数: {thread_num}", 1)
        elif choice == '4':
            # 开始下载
            if not self.m3u8_urls:
                self.add_log("没有添加任何M3U8链接!", 2)
                return
            
            self.add_log("开始下载...", 1)
            self.draw_screen()
            self.screen.refresh()
            
            # 创建输出目录
            os.makedirs(self.config['output_dir'], exist_ok=True)
            
            # 检查ffmpeg
            if shutil.which("ffmpeg") is None:
                self.add_log("错误: 未找到ffmpeg，请先安装!", 2)
                return
            
            # 创建下载器
            downloader = M3UDownloader(
                output_dir=self.config['output_dir'],
                thread_num=self.config['thread_num']
            )
            
            # 下载过程
            total = len(self.m3u8_urls)
            success_count = 0
            failed_count = 0
            
            with ThreadPoolExecutor(max_workers=self.config['thread_num']) as executor:
                futures = {
                    executor.submit(downloader.download_m3u8, url): url
                    for url in self.m3u8_urls
                }
                
                for i, future in enumerate(as_completed(futures), 1):
                    url = futures[future]
                    try:
                        success, message = future.result()
                        if success:
                            success_count += 1
                            self.add_log(f"✓ {url} - {message}", 1)
                        else:
                            failed_count += 1
                            self.add_log(f"✗ {url} - {message}", 2)
                    except Exception as e:
                        failed_count += 1
                        self.add_log(f"✗ {url} - 处理失败: {e}", 2)
                    
                    # 显示进度
                    progress = i / total * 100
                    status_line = f"进度: {i}/{total} ({progress:.1f}%) - 成功: {success_count}, 失败: {failed_count}"
                    self.screen.addstr(3, 0, status_line.ljust(80))
                    self.screen.refresh()
            
            self.add_log(f"下载完成! 成功: {success_count}, 失败: {failed_count}", 1)
        elif choice == '5':
            # 查看日志
            self.show_logs_screen()
        elif choice == '6':
            # 退出
            self.add_log("退出程序...", 1)
            return False
        return True
    
    def show_logs_screen(self):
        """显示日志屏幕"""
        while True:
            self.draw_screen(show_logs=True)
            key = self.screen.getch()
            if key == 27:  # ESC键返回
                break
    
    def run(self):
        """运行终端界面"""
        try:
            self.init_curses()
            
            while True:
                self.draw_screen()
                key = self.screen.getch()
                
                # 处理数字键
                if 48 <= key <= 57:  # ASCII数字键
                    choice = chr(key)
                    if not self.handle_menu(choice):
                        break
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup_curses()


if __name__ == "__main__":
    try:
        ui = M3UTerminalUI()
        ui.run()
    except Exception as e:
        print(f"程序运行出错: {e}")
        sys.exit(1)

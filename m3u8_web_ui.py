#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M3U8视频下载器 - Web界面版
功能: 通过Web浏览器下载M3U8播放列表并转换为MP4
支持: 小鹅通、腾讯云等多种M3U8格式
更新时间: 2025-12-05
"""

import os
import re
import time
import subprocess
import shutil
import threading
from flask import Flask, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ================================ 配置区 ================================

# 默认并发线程数
DEFAULT_THREAD_NUM = 8

# 默认视频输出目录
DEFAULT_OUTPUT_DIR = "./video_output"

# 默认请求头 - 添加更多必要的请求头，提高下载成功率
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://",  # 默认Referer，会根据实际URL自动调整
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br",
}

# 默认超时设置 (秒)
DEFAULT_REQUEST_TIMEOUT = 60

# 默认重试次数
DEFAULT_RETRY_COUNT = 3

# Web服务器配置
HOST = "0.0.0.0"
PORT = 5001
DEBUG = True

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
        self.progress = 0
        self.status = "准备就绪"
        self.logs = []
        self.success_count = 0
        self.failed_count = 0
    
    def reset(self):
        """重置状态"""
        self.progress = 0
        self.status = "准备就绪"
        self.logs = []
        self.success_count = 0
        self.failed_count = 0
    
    def is_m3u8_file(self, file_path):
        """检查文件是否为M3U8格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(100)
                return '#EXTM3U' in content
        except:
            return False
    
    def add_log(self, message, level="info"):
        """添加日志"""
        self.logs.append({
            "time": time.strftime("%H:%M:%S"),
            "message": message,
            "level": level
        })
        # 限制日志数量
        if len(self.logs) > 50:
            self.logs.pop(0)
    
    def download_file(self, url, output_path):
        """下载单个文件"""
        for i in range(self.retry_count):
            try:
                self.add_log(f"正在下载: {url}")
                # 支持HTTPS证书验证选项
                response = self.session.get(url, headers=self.headers, timeout=self.timeout, verify=False)
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                return True
            except Exception as e:
                if i == self.retry_count - 1:
                    self.add_log(f"下载失败: {str(e)} | URL: {url}", "error")
                    return False
                self.add_log(f"下载失败，重试 ({i+1}/{self.retry_count}): {str(e)}", "warning")
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
            
            self.add_log(f"正在使用ffmpeg转换为MP4，输出文件: {output_path}")
            self.add_log(f"FFmpeg命令: {' '.join(cmd[:-1])} [输出文件]")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.add_log(f"转换成功: {output_filename}", "success")
                return True, f"转换成功: {output_filename}"
            else:
                # 记录更详细的FFmpeg错误信息
                error_msg = result.stderr[-500:]  # 只显示最后500个字符
                self.add_log(f"FFmpeg返回码: {result.returncode}", "error")
                self.add_log(f"转换失败: {error_msg}", "error")
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
    
    def batch_download(self, m3u8_urls):
        """批量下载多个M3U8链接"""
        self.reset()
        self.status = "开始下载..."
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 检查ffmpeg
        if shutil.which("ffmpeg") is None:
            self.add_log("错误: 未找到ffmpeg，请先安装!", "error")
            self.status = "下载失败"
            return
        
        total_urls = len(m3u8_urls)
        
        try:
            # 批量下载
            with ThreadPoolExecutor(max_workers=self.thread_num) as executor:
                futures = {
                    executor.submit(self.download_m3u8, url): url
                    for url in m3u8_urls
                }
                
                # 处理结果
                for i, future in enumerate(as_completed(futures), 1):
                    url = futures[future]
                    try:
                        success, message = future.result()
                        if success:
                            self.success_count += 1
                        else:
                            self.failed_count += 1
                    except Exception as e:
                        self.failed_count += 1
                        self.add_log(f"✗ {url} - 处理失败: {e}", "error")
                    
                    # 更新进度
                    self.progress = (i / total_urls) * 100
                    self.status = f"已完成 {i}/{total_urls} 个视频 (成功: {self.success_count}, 失败: {self.failed_count})"
        except Exception as e:
            self.add_log(f"下载过程中发生错误: {e}", "error")
        finally:
            self.status = f"下载完成! 成功: {self.success_count}, 失败: {self.failed_count}"
            self.progress = 100


# 创建Flask应用
app = Flask(__name__)

# 创建下载器实例
downloader = M3UDownloader()

# 下载线程
download_thread = None


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/start_download', methods=['POST'])
def start_download():
    """开始下载"""
    global download_thread
    
    data = request.json
    m3u8_urls = data.get('urls', [])
    if not m3u8_urls:
        return jsonify({
            "status": "error",
            "message": "请提供M3U8链接"
        })
    
    # 获取用户配置
    thread_num = data.get('thread_num', DEFAULT_THREAD_NUM)
    timeout = data.get('timeout', DEFAULT_REQUEST_TIMEOUT)
    retry_count = data.get('retry_count', DEFAULT_RETRY_COUNT)
    
    # 创建新的下载器实例，应用用户配置
    global downloader
    downloader = M3UDownloader(
        thread_num=thread_num,
        timeout=timeout,
        retry_count=retry_count
    )
    
    # 启动下载线程
    download_thread = threading.Thread(target=downloader.batch_download, args=(m3u8_urls,))
    download_thread.daemon = True
    download_thread.start()
    
    return jsonify({
        "status": "success",
        "message": "下载已开始"
    })


@app.route('/api/get_status')
def get_status():
    """获取下载状态"""
    return jsonify({
        "progress": downloader.progress,
        "status": downloader.status,
        "logs": downloader.logs,
        "success_count": downloader.success_count,
        "failed_count": downloader.failed_count
    })


@app.route('/api/reset')
def reset():
    """重置下载状态"""
    downloader.reset()
    return jsonify({
        "status": "success",
        "message": "已重置"
    })


@app.route('/api/get_files')
def get_files():
    """获取已下载的文件列表"""
    files = []
    try:
        for filename in os.listdir(downloader.output_dir):
            if filename.endswith('.mp4'):
                file_path = os.path.join(downloader.output_dir, filename)
                files.append({
                    "name": filename,
                    "size": os.path.getsize(file_path),
                    "mtime": time.ctime(os.path.getmtime(file_path))
                })
        # 按修改时间排序
        files.sort(key=lambda x: os.path.getmtime(os.path.join(downloader.output_dir, x['name'])), reverse=True)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })
    
    return jsonify({
        "status": "success",
        "files": files
    })


# 运行Flask应用
if __name__ == '__main__':
    # 确保输出目录存在
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    app.run(host=HOST, port=PORT, debug=DEBUG)
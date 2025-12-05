#!/usr/bin/env python3 
# -*- coding: utf-8 -*- 
""" 
M3U8视频下载工具 - 带GUI界面
功能: 下载M3U8播放列表并使用ffmpeg合并为MP4文件
支持: 小鹅通、腾讯云等多种M3U8格式
更新时间: 2025-12-05 
""" 

import os
import re
import time
import subprocess
import shutil
import threading
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ================================ 配置区 ================================

# 默认并发线程数 
DEFAULT_THREAD_NUM = 8 

# 默认视频输出目录 
DEFAULT_OUTPUT_DIR = "./video_output" 

# 默认请求头 
DEFAULT_HEADERS = { 
    "Accept": "*/*", 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
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
                response = self.session.get(url, timeout=self.timeout)
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
            # 下载M3U8播放列表
            m3u8_path = os.path.join(temp_dir, "playlist.m3u8")
            if not self.download_file(m3u8_url, m3u8_path):
                return False, f"无法下载M3U8文件: {m3u8_url}"
            
            # 检查是否为有效的M3U8文件
            if not self.is_m3u8_file(m3u8_path):
                return False, f"下载的文件不是有效的M3U8格式: {m3u8_url}"
            
            # 使用ffmpeg直接转换M3U8为MP4
            output_path = os.path.join(self.output_dir, output_filename)
            cmd = [
                "ffmpeg",
                "-i", m3u8_path,
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",  # 修复音频流
                "-y",  # 覆盖现有文件
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return True, f"转换成功: {output_filename}"
            else:
                return False, f"转换失败: {result.stderr}"
                
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


class M3UGUIApp:
    """M3U8下载器GUI应用"""
    
    def __init__(self, master):
        """初始化GUI应用"""
        self.master = master
        self.master.title("M3U8视频下载工具")
        self.master.geometry("800x600")
        self.master.resizable(True, True)
        
        # 设置主题
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 下载器实例
        self.downloader = None
        
        # 下载线程
        self.download_thread = None
        
        # 配置选项
        self.output_dir = StringVar(value=DEFAULT_OUTPUT_DIR)
        self.thread_num = StringVar(value=str(DEFAULT_THREAD_NUM))
        self.timeout = StringVar(value=str(DEFAULT_REQUEST_TIMEOUT))
        self.retry_count = StringVar(value=str(DEFAULT_RETRY_COUNT))
        
        # 状态变量
        self.is_downloading = False
        
        # 初始化界面
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        title_label = Label(main_frame, text="M3U8视频下载工具", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 输入区域
        input_frame = Frame(main_frame)
        input_frame.pack(fill=X, pady=5)
        
        # M3U8链接标签
        m3u8_label = Label(input_frame, text="M3U8链接 (每行一个):")
        m3u8_label.pack(anchor=W)
        
        # M3U8链接输入框
        self.m3u8_text = Text(input_frame, height=5, wrap=WORD, bg="white")
        scrollbar = Scrollbar(input_frame, command=self.m3u8_text.yview)
        self.m3u8_text.config(yscrollcommand=scrollbar.set)
        self.m3u8_text.pack(side=LEFT, fill=X, expand=True, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 配置区域
        config_frame = Frame(main_frame, bd=1, relief=RIDGE)
        config_frame.pack(fill=X, pady=10, padx=5)
        
        # 输出目录选择
        dir_frame = Frame(config_frame, padx=10, pady=5)
        dir_frame.pack(fill=X)
        
        dir_label = Label(dir_frame, text="输出目录:", width=10, anchor=W)
        dir_label.pack(side=LEFT)
        
        self.dir_entry = Entry(dir_frame, textvariable=self.output_dir, state="readonly")
        self.dir_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        dir_button = Button(dir_frame, text="浏览...", command=self.select_output_dir)
        dir_button.pack(side=RIGHT, padx=5)
        
        # 下载配置
        settings_frame = Frame(config_frame, padx=10, pady=5)
        settings_frame.pack(fill=X)
        
        # 线程数
        thread_label = Label(settings_frame, text="线程数:", width=10, anchor=W)
        thread_label.pack(side=LEFT)
        
        thread_entry = Entry(settings_frame, textvariable=self.thread_num, width=10)
        thread_entry.pack(side=LEFT, padx=5)
        
        # 超时时间
        timeout_label = Label(settings_frame, text="超时时间 (秒):", width=15, anchor=W)
        timeout_label.pack(side=LEFT, padx=10)
        
        timeout_entry = Entry(settings_frame, textvariable=self.timeout, width=10)
        timeout_entry.pack(side=LEFT, padx=5)
        
        # 重试次数
        retry_label = Label(settings_frame, text="重试次数:", width=10, anchor=W)
        retry_label.pack(side=LEFT, padx=10)
        
        retry_entry = Entry(settings_frame, textvariable=self.retry_count, width=10)
        retry_entry.pack(side=LEFT, padx=5)
        
        # 操作按钮
        button_frame = Frame(main_frame, pady=10)
        button_frame.pack(fill=X)
        
        # 开始下载按钮
        self.start_button = Button(button_frame, text="开始下载", command=self.start_download, bg="green", fg="white", font=("Arial", 12, "bold"))
        self.start_button.pack(side=LEFT, padx=5)
        
        # 停止下载按钮
        self.stop_button = Button(button_frame, text="停止下载", command=self.stop_download, bg="red", fg="white", font=("Arial", 12, "bold"), state=DISABLED)
        self.stop_button.pack(side=LEFT, padx=5)
        
        # 清空日志按钮
        clear_button = Button(button_frame, text="清空日志", command=self.clear_log, bg="gray", fg="white")
        clear_button.pack(side=RIGHT, padx=5)
        
        # 进度条
        self.progress_frame = Frame(main_frame, pady=5)
        self.progress_frame.pack(fill=X)
        
        self.progress_var = DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100, mode="determinate")
        self.progress_bar.pack(fill=X)
        
        # 进度标签
        self.progress_label = Label(self.progress_frame, text="准备就绪")
        self.progress_label.pack(anchor=W, pady=2)
        
        # 日志区域
        log_frame = Frame(main_frame, bd=1, relief=RIDGE)
        log_frame.pack(fill=BOTH, expand=True, pady=10)
        
        log_label = Label(log_frame, text="日志输出:")
        log_label.pack(anchor=W, padx=10, pady=5)
        
        self.log_text = Text(log_frame, wrap=WORD, bg="#f0f0f0", state=DISABLED)
        log_scrollbar = Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        log_scrollbar.pack(side=RIGHT, fill=Y)
    
    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(initialdir=self.output_dir.get(), title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
    
    def add_log(self, message):
        """添加日志信息"""
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=NORMAL)
        self.log_text.delete(1.0, END)
        self.log_text.config(state=DISABLED)
    
    def update_progress(self, value, status):
        """更新进度"""
        self.progress_var.set(value)
        self.progress_label.config(text=status)
        self.master.update_idletasks()
    
    def start_download(self):
        """开始下载"""
        # 检查是否正在下载
        if self.is_downloading:
            messagebox.showwarning("警告", "下载正在进行中，请勿重复点击")
            return
        
        # 获取M3U8链接
        m3u8_text = self.m3u8_text.get(1.0, END).strip()
        if not m3u8_text:
            messagebox.showerror("错误", "请输入M3U8链接")
            return
        
        # 解析M3U8链接列表
        m3u8_urls = [url.strip() for url in m3u8_text.split('\n') if url.strip()]
        if not m3u8_urls:
            messagebox.showerror("错误", "请输入有效的M3U8链接")
            return
        
        # 检查输出目录
        output_dir = self.output_dir.get()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {e}")
                return
        
        # 检查ffmpeg是否安装
        if shutil.which("ffmpeg") is None:
            messagebox.showerror("错误", "未找到ffmpeg，请先安装ffmpeg")
            return
        
        # 更新状态
        self.is_downloading = True
        self.start_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)
        self.update_progress(0, f"准备下载 {len(m3u8_urls)} 个视频")
        self.add_log("开始下载...")
        
        # 读取配置
        try:
            thread_num = int(self.thread_num.get())
            timeout = int(self.timeout.get())
            retry_count = int(self.retry_count.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的配置参数")
            self.reset_state()
            return
        
        # 创建下载器实例
        self.downloader = M3UDownloader(
            output_dir=output_dir,
            thread_num=thread_num
        )
        self.downloader.timeout = timeout
        self.downloader.retry_count = retry_count
        
        # 启动下载线程
        self.download_thread = threading.Thread(target=self.download_task, args=(m3u8_urls,))
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def download_task(self, m3u8_urls):
        """下载任务"""
        total_urls = len(m3u8_urls)
        success_count = 0
        failed_count = 0
        
        try:
            # 批量下载
            with ThreadPoolExecutor(max_workers=int(self.thread_num.get())) as executor:
                # 提交所有任务
                futures = {
                    executor.submit(self.downloader.download_m3u8, url): url
                    for url in m3u8_urls
                }
                
                # 处理结果
                for i, future in enumerate(as_completed(futures)):
                    url = futures[future]
                    try:
                        success, message = future.result()
                        if success:
                            success_count += 1
                            self.add_log(f"✓ {url} - {message}")
                        else:
                            failed_count += 1
                            self.add_log(f"✗ {url} - {message}")
                    except Exception as e:
                        failed_count += 1
                        self.add_log(f"✗ {url} - 处理失败: {e}")
                    
                    # 更新进度
                    progress = (i + 1) / total_urls * 100
                    status = f"已完成 {i + 1}/{total_urls} 个视频 (成功: {success_count}, 失败: {failed_count})"
                    self.update_progress(progress, status)
        except Exception as e:
            self.add_log(f"下载过程中发生错误: {e}")
        finally:
            # 重置状态
            self.reset_state()
            
            # 显示结果
            self.add_log(f"下载完成! 成功: {success_count}, 失败: {failed_count}")
            messagebox.showinfo("完成", f"下载完成!\n成功: {success_count}\n失败: {failed_count}")
    
    def stop_download(self):
        """停止下载"""
        if messagebox.askyesno("确认", "确定要停止下载吗?"):
            # 这里可以添加停止下载的逻辑
            # 目前无法直接停止线程池中的任务，只能等待当前任务完成
            self.add_log("已请求停止下载，正在等待当前任务完成...")
            self.reset_state()
    
    def reset_state(self):
        """重置状态"""
        self.is_downloading = False
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.update_progress(0, "准备就绪")
    
    def run(self):
        """运行应用"""
        self.master.mainloop()


if __name__ == "__main__":
    root = Tk()
    app = M3UGUIApp(root)
    app.run()
#!/usr/bin/env python3 
# -*- coding: utf-8 -*- 
""" 
M3U8视频下载工具 
功能: 下载M3U8播放列表并使用ffmpeg合并为MP4文件 
支持: 小鹅通、腾讯云等多种M3U8格式 
更新时间: 2025-12-05 
""" 

import os
import re
import time
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ================================ 配置区 ================================

# 并发线程数 
THREAD_NUM = 8 

# 视频输出目录 
OUTPUT_DIR = "./video_output" 

# 请求头 
HEADERS = { 
    "Accept": "*/*", 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
}

# 超时设置 (秒)
REQUEST_TIMEOUT = 60

# 重试次数
RETRY_COUNT = 3

# 视频片段列表 - 支持多个M3U8链接
SEGMENTS = [ 
    # 添加你的M3U8链接 here
    # "https://example.com/video.m3u8",
]

# ====================================================================== 


class M3UDownloader:
    """M3U8下载器类"""
    
    def __init__(self, output_dir=OUTPUT_DIR, thread_num=THREAD_NUM):
        """初始化下载器"""
        self.output_dir = output_dir
        self.thread_num = thread_num
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
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
        for i in range(RETRY_COUNT):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            except Exception as e:
                print(f"下载失败 (尝试 {i+1}/{RETRY_COUNT}): {e}")
                if i == RETRY_COUNT - 1:
                    return False
                time.sleep(2)
        return False
    
    def process_m3u8(self, m3u8_url, output_filename="output.mp4"):
        """处理M3U8文件并转换为MP4"""
        print(f"\n开始处理 M3U8: {m3u8_url}")
        
        # 创建临时目录
        temp_dir = os.path.join(self.output_dir, f"temp_{int(time.time())}")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 下载M3U8播放列表
            m3u8_path = os.path.join(temp_dir, "playlist.m3u8")
            if not self.download_file(m3u8_url, m3u8_path):
                print(f"无法下载M3U8文件: {m3u8_url}")
                return False
            
            # 检查是否为有效的M3U8文件
            if not self.is_m3u8_file(m3u8_path):
                print(f"下载的文件不是有效的M3U8格式: {m3u8_url}")
                return False
            
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
            
            print(f"正在使用ffmpeg转换为MP4...")
            print(f"输出文件: {output_path}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ 转换成功: {output_filename}")
                return True
            else:
                print(f"✗ 转换失败: {result.stderr}")
                return False
                
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
        print(f"开始批量下载，共 {len(m3u8_urls)} 个任务")
        print("=" * 60)
        
        success_count = 0
        failed_count = 0
        start_time = time.time()
        
        # 使用线程池批量处理
        with ThreadPoolExecutor(max_workers=self.thread_num) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self.download_m3u8, url): url
                for url in m3u8_urls
            }
            
            # 处理结果
            for future in as_completed(futures):
                url = futures[future]
                try:
                    if future.result():
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"✗ 处理失败: {url} - {e}")
                
                # 显示进度
                total = success_count + failed_count
                progress = (total / len(m3u8_urls)) * 100
                print(f"\r进度: {total}/{len(m3u8_urls)} ({progress:.1f}%) - 成功: {success_count}, 失败: {failed_count}", end="")
        
        print()
        print("=" * 60)
        
        # 统计信息
        elapsed = time.time() - start_time
        minutes, seconds = divmod(int(elapsed), 60)
        
        print(f"\n批量下载完成!")
        print(f"总耗时: {minutes:02d}:{seconds:02d}")
        print(f"成功: {success_count}, 失败: {failed_count}")
        print(f"成功率: {success_count/len(m3u8_urls)*100:.1f}%")
        
        return success_count, failed_count


def main():
    """主函数"""
    print("=" * 60)
    print("M3U8视频下载工具")
    print("支持: 小鹅通、腾讯云、阿里云等多种M3U8格式")
    print("=" * 60)
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 获取用户输入的M3U8链接
    while True:
        m3u8_input = input("\n请输入M3U8链接 (多个链接用逗号分隔，直接回车使用配置中的链接): ").strip()
        
        m3u8_urls = []
        
        if m3u8_input:
            # 处理用户输入的链接
            m3u8_urls = [url.strip() for url in m3u8_input.split(',')]
        elif SEGMENTS and SEGMENTS[0]:
            # 使用配置中的链接
            m3u8_urls = SEGMENTS
        else:
            print("错误: 没有提供M3U8链接")
            continue
            
        break
    
    # 创建下载器实例
    downloader = M3UDownloader()
    
    # 开始下载
    downloader.batch_download(m3u8_urls)
    
    print("\n所有任务处理完成!")
    print(f"视频已保存至: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
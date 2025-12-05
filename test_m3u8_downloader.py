#!/usr/bin/env python3 
# -*- coding: utf-8 -*- 
""" 
M3U8下载器测试脚本
测试M3U8下载功能是否正常工作
""" 

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# 测试用的M3U8链接 - 更新为更可靠的测试链接
TEST_M3U8_URLS = [
    "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8",  # 公开测试M3U8链接
    "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",  # 可靠的M3U8测试链接
]

# 输出目录
TEST_OUTPUT_DIR = "./test_output"

# 请求头 - 改进请求头配置，提高与不同服务器的兼容性
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://",
}


def is_m3u8_content(content):
    """判断内容是否为M3U8格式"""
    try:
        text = content.decode('utf-8', errors='ignore')
        return '#EXTM3U' in text
    except:
        return False


def download_file(url, output_path):
    """下载单个文件"""
    try:
        print(f"正在下载: {url}")
        # 自动调整Referer
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        headers = HEADERS.copy()
        headers['Referer'] = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        headers['Origin'] = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # 支持HTTPS证书验证选项
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        # 检查是否为M3U8内容
        if is_m3u8_content(response.content):
            print(f"✓ 成功下载M3U8文件: {output_path}")
            return True, "m3u8"
        else:
            print(f"✓ 成功下载文件: {output_path}")
            return True, "other"
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        return False, str(e)


def test_m3u8_downloader():
    """测试M3U8下载器功能"""
    print("=" * 60)
    print("M3U8下载器测试")
    print("=" * 60)
    
    # 创建测试目录
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    
    # 测试1: 下载M3U8文件
    print("\n测试1: 下载M3U8文件")
    print("-" * 60)
    
    success_count = 0
    failed_count = 0
    
    for url in TEST_M3U8_URLS:
        # 生成输出文件名
        filename = url.split('/')[-1] if '.' in url.split('/')[-1] else f"test_{int(time.time())}.m3u8"
        output_path = os.path.join(TEST_OUTPUT_DIR, filename)
        
        success, result = download_file(url, output_path)
        if success:
            success_count += 1
        else:
            failed_count += 1
    
    print(f"\n测试结果: 成功 {success_count}, 失败 {failed_count}")
    
    # 测试2: 检查下载的文件
    print("\n测试2: 检查下载的文件")
    print("-" * 60)
    
    m3u8_files = [f for f in os.listdir(TEST_OUTPUT_DIR) if f.endswith('.m3u8')]
    print(f"找到 {len(m3u8_files)} 个M3U8文件")
    
    for m3u8_file in m3u8_files:
        file_path = os.path.join(TEST_OUTPUT_DIR, m3u8_file)
        size = os.path.getsize(file_path)
        print(f"- {m3u8_file} ({size} 字节)")
        
        # 读取文件内容的前100字符检查格式
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(100)
            if '#EXTM3U' in content:
                print(f"  ✓ 格式正确: 包含 #EXTM3U 标记")
            else:
                print(f"  ✗ 格式错误: 缺少 #EXTM3U 标记")
    
    # 测试3: 测试多线程下载
    print("\n测试3: 测试多线程下载")
    print("-" * 60)
    
    test_urls = TEST_M3U8_URLS * 2  # 使用重复的URL测试多线程
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(download_file, url, os.path.join(TEST_OUTPUT_DIR, f"thread_test_{i}.m3u8")):
            url for i, url in enumerate(test_urls)
        }
        
        thread_success = 0
        thread_failed = 0
        
        for future in as_completed(futures):
            success, _ = future.result()
            if success:
                thread_success += 1
            else:
                thread_failed += 1
    
    elapsed = time.time() - start_time
    print(f"多线程下载结果: 成功 {thread_success}, 失败 {thread_failed}")
    print(f"耗时: {elapsed:.2f} 秒")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print(f"总测试结果: 成功 {success_count + thread_success}, 失败 {failed_count + thread_failed}")
    print("测试文件保存在:", TEST_OUTPUT_DIR)
    print("=" * 60)


if __name__ == "__main__":
    test_m3u8_downloader()

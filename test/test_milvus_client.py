"""
Milvus 客户端测试脚本
用于验证修复后的 Milvus 客户端是否能正常工作
"""

import sys
import os

from utils.milvus_client import MilvusClient
import time

def test_with_localhost():
    """测试使用 localhost 的连接"""
    print("测试使用 localhost 连接...")
    client = MilvusClient("http://localhost:5002")
    
    # 测试插入
    test_data = [{
        "description": "测试数据：机器人找到了一个球",
        "timestamp": int(time.time())
    }]
    
    print("插入测试数据...")
    result = client.insert_experience("测试数据：机器人找到了一个球")
    print(f"插入结果: {result}")
    
    if result.get("status") != "success":
        print("插入失败")
        return False
    
    # 等待处理
    time.sleep(1)
    
    # 测试搜索
    print("搜索测试数据...")
    query = "测试数据：机器人一个球"
    result = client.search_experience(query)
    print(f"搜索结果: {result}")
    
    return True

def test_with_127_0_0_1():
    """测试使用 127.0.0.1 的连接"""
    print("测试使用 127.0.0.1 连接...")
    client = MilvusClient("http://127.0.0.1:5002")
    
    # 测试插入
    test_data = [{
        "description": "测试数据：机器人发现了一个方块",
        "timestamp": int(time.time())
    }]
    
    print("插入测试数据...")
    result = client.insert_experience(test_data)
    print(f"插入结果: {result}")
    
    if result.get("status") != "success":
        print("插入失败")
        return False
    
    # 等待处理
    time.sleep(1)
    
    # 测试搜索
    print("搜索测试数据...")
    query = "找一个方块"
    result = client.search_experience(query)
    print(f"搜索结果: {result}")
    
    return True

def main():
    print("开始测试 Milvus 客户端...")
    print("=" * 50)
    
    try:
        # 测试 localhost 连接
        print("1. 测试 localhost 连接")
        success1 = test_with_localhost()
        print(f"结果: {'通过' if success1 else '失败'}")
        print()
        
        # 测试 127.0.0.1 连接
        # print("2. 测试 127.0.0.1 连接")
        # success2 = test_with_127_0_0_1()
        # print(f"结果: {'通过' if success2 else '失败'}")
        # print()
        
        # if success1 and success2:
        #     print("所有测试通过!")
        # else:
        #     print("部分测试失败!")
            
    except Exception as e:
        print(f"测试过程中出现异常: {e}")

if __name__ == "__main__":
    main()
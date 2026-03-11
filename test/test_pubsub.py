#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redis发布/订阅功能测试程序
用于测试机器人任务指令发送和执行结果返回功能
"""

import sys
import time
import threading
from utils.redis_client import RedisClient
import json

tasks = [
        {"robot_name": "robot_2", "subtask": "navigate to Loading Area", "subtask_order": "0"},
        {"robot_name": "robot_1", "subtask": "grasp Cargo 1", "subtask_order": "1"},
        {"robot_name": "robot_1", "subtask": "place Cargo 1 on robot_2", "subtask_order": "2"},
        {"robot_name": "robot_2", "subtask": "navigate to Unloading Area", "subtask_order": "3"},
        {"robot_name": "robot_2", "subtask": "unload Cargo 1", "subtask_order": "4"}
    ]

def task_allocate(task_list):
    i = 0
    task_allocate_list = []
    while i < len(task_list):                            
        subtask = task_list[i]
        subtask_order = subtask['subtask_order']
        next_index = i + 1
        while next_index < len(task_list) and subtask["subtask_order"] == subtask_order:
            next_index += 1
        task_allocate_list.append(tasks[i:next_index])
    

def test_pubsub_functionality():
    """
    测试Redis客户端的发布/订阅功能
    """
    print("=== Redis发布/订阅功能测试 ===")
    
    # 创建Redis客户端实例
    redis_client = RedisClient(host='localhost', port=5555, db=0)
    
    # 测试数据
    robot_name = "test_robot_001"
    task_data = {
        "task_id": "task_001",
        "command": "move_to_location",
        "destination": "kitchen",
        "priority": "high"
    }
    
    result_data = {
        "task_id": "task_001",
        "status": "completed",
        "result": "Successfully moved to kitchen",
        "execution_time": "2.5s"
    }
    
    # 用于测试的标志位
    task_received = threading.Event()
    result_received = threading.Event()
    
    # 任务处理回调函数
    def task_handler(task):
        print(f"[Robot] 收到任务指令: {task}")
        assert task == task_data, "接收的任务与发送的任务不匹配"
        task_received.set()
        
        # 模拟任务执行并返回结果
        time.sleep(1)
        print(f"[Robot] 任务执行完成，返回结果...")
        redis_client.publish_result(robot_name, result_data)
    
    # 结果处理回调函数
    def result_handler(robot_name_received, result):
        print(f"[Planner] 收到机器人 {robot_name_received} 的执行结果: {result}")
        assert robot_name_received == robot_name, "返回结果的机器人名称不匹配"
        assert result == result_data, "接收的结果与发送的结果不匹配"
        result_received.set()
    
    # 启动订阅任务指令的线程
    print("[System] 启动机器人任务订阅线程...")
    task_thread = threading.Thread(target=redis_client.subscribe_task, args=(robot_name, task_handler))
    task_thread.daemon = True
    task_thread.start()
    
    # 启动订阅执行结果的线程
    print("[System] 启动结果订阅线程...")
    result_thread = threading.Thread(target=redis_client.subscribe_result, args=(result_handler,))
    result_thread.daemon = True
    result_thread.start()
    
    # 等待订阅建立
    time.sleep(1)
    
    # 发布任务指令
    print(f"[Planner] 发送任务指令给 {robot_name}...")
    success = redis_client.publish_task(robot_name, task_data)
    assert success, "发布任务指令失败"
    
    # 等待任务接收
    task_received.wait(timeout=5)
    assert task_received.is_set(), "机器人未接收到任务指令"
    
    # 等待结果返回
    result_received.wait(timeout=5)
    assert result_received.is_set(), "Planner未接收到执行结果"
    
    print("=== 所有测试通过 ===")


def test_pubsub_with_multiple_robots():
    """
    测试多个机器人的发布/订阅功能
    """
    print("\n=== 多机器人发布/订阅功能测试 ===")
    
    # 创建Redis客户端实例
    redis_client = RedisClient(host='localhost', port=6379, db=0)
    
    # 测试数据
    robot_names = ["robot_alpha", "robot_beta", "robot_gamma"]
    tasks = [
        {"task_id": "task_alpha", "command": "pick_object", "object": "apple"},
        {"task_id": "task_beta", "command": "place_object", "location": "table"},
        {"task_id": "task_gamma", "command": "navigate", "destination": "living_room"}
    ]
    
    results = [
        {"task_id": "task_alpha", "status": "completed", "object": "apple picked"},
        {"task_id": "task_beta", "status": "completed", "object": "object placed"},
        {"task_id": "task_gamma", "status": "completed", "location": "living_room reached"}
    ]
    
    # 用于测试的标志位
    tasks_received = {name: threading.Event() for name in robot_names}
    results_received = {name: threading.Event() for name in robot_names}
    
    # 任务处理回调函数
    def multi_task_handler(robot_name, task):
        print(f"[{robot_name}] 收到任务指令: {task}")
        tasks_received[robot_name].set()
        
        # 找到对应的结果并返回
        index = robot_names.index(robot_name)
        time.sleep(0.5)  # 模拟执行时间
        print(f"[{robot_name}] 任务执行完成，返回结果...")
        redis_client.publish_result(robot_name, results[index])
    
    # 结果处理回调函数
    def multi_result_handler(robot_name, result):
        print(f"[Planner] 收到机器人 {robot_name} 的执行结果: {result}")
        results_received[robot_name].set()
    
    # 启动各机器人的任务订阅线程
    threads = []
    for i, robot_name in enumerate(robot_names):
        print(f"[System] 启动 {robot_name} 的任务订阅线程...")
        # 使用闭包确保正确的robot_name和task传递给handler
        def make_handler(name):
            def handler(task):
                multi_task_handler(name, task)
            return handler
        
        task_thread = threading.Thread(
            target=redis_client.subscribe_task, 
            args=(robot_name, make_handler(robot_name))
        )
        task_thread.daemon = True
        task_thread.start()
        threads.append(task_thread)
    
    # 启动结果订阅线程
    print("[System] 启动多机器人结果订阅线程...")
    result_thread = threading.Thread(target=redis_client.subscribe_result, args=(multi_result_handler,))
    result_thread.daemon = True
    result_thread.start()
    threads.append(result_thread)
    
    # 等待订阅建立
    time.sleep(1)
    
    # 发布任务给各机器人
    for i, robot_name in enumerate(robot_names):
        print(f"[Planner] 发送任务指令给 {robot_name}...")
        success = redis_client.publish_task(robot_name, tasks[i])
        assert success, f"发布任务指令给 {robot_name} 失败"
    
    # 等待所有任务接收
    for robot_name in robot_names:
        tasks_received[robot_name].wait(timeout=5)
        assert tasks_received[robot_name].is_set(), f"机器人 {robot_name} 未接收到任务指令"
    
    # 等待所有结果返回
    for robot_name in robot_names:
        results_received[robot_name].wait(timeout=5)
        assert results_received[robot_name].is_set(), f"Planner未接收到机器人 {robot_name} 的执行结果"
    
    print("=== 多机器人测试通过 ===")


if __name__ == "__main__":
    print("Redis发布/订阅功能测试程序")
    print("确保Redis服务器正在运行 (redis-server --port 6379)")
    
    try:
        # 运行基本功能测试
        test_pubsub_functionality()
        
        # 运行多机器人测试
        test_pubsub_with_multiple_robots()
        
        print("\n所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        sys.exit(1)
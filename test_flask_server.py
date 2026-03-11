#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Flask Server 测试客户端
用于测试flask_server.py提供的API接口
"""

import requests
import json
import time

def test_health_check():
    """测试健康检查接口"""
    print("=== 测试健康检查接口 ===")
    try:
        response = requests.get('http://127.0.0.1:5000/health')
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"健康检查失败: {str(e)}")
        return False

def test_execute_task():
    """测试任务执行接口"""
    print("\n=== 测试任务执行接口 ===")
    try:
        task_data = {
            # "task": "Please transfer Cargo 1 to the unloading area."
            "task": "Move all cargos to the corresponding Exit Bay. For example, move Cargo with kind A to Exit Bay A and Cargo with kind B to Exit Bay B."
        }
        response = requests.post(
            'http://127.0.0.1:5000/execute_task',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(task_data)
        )
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"任务执行测试失败: {str(e)}")
        return False

def test_robots_status():
    """测试机器人状态查询接口"""
    print("\n=== 测试机器人状态查询接口 ===")
    try:
        response = requests.get('http://127.0.0.1:5000/robots/status')
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"机器人状态查询失败: {str(e)}")
        return False

def test_robot_properties(robot_name="dog1"):
    """测试特定机器人属性查询接口"""
    print(f"\n=== 测试机器人{robot_name}属性查询接口 ===")
    try:
        response = requests.get(f'http://127.0.0.1:5000/robots/{robot_name}/properties')
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"机器人属性查询失败: {str(e)}")
        return False

def test_get_all_items():
    """测试获取所有物品信息接口"""
    print("\n=== 测试获取所有物品信息接口 ===")
    try:
        response = requests.get('http://127.0.0.1:5000/items')
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"获取物品信息失败: {str(e)}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("开始测试Flask服务端...")
    
    # 等待服务启动
    print("等待服务启动...")
    time.sleep(3)
    
    tests = [
        test_health_check,
        test_robots_status,
        test_robot_properties,
        test_get_all_items,  # 新增的测试
        test_execute_task,
        test_get_all_items,  # 新增的测试
        test_robots_status,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"测试 {test.__name__} 出现异常: {str(e)}")
            results.append(False)
        time.sleep(1)  # 避免请求过快
    
    print("\n=== 测试结果汇总 ===")
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "通过" if result else "失败"
        print(f"{i+1}. {test.__name__}: {status}")
    
    passed = sum(results)
    total = len(results)
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("所有测试通过!")
    else:
        print("部分测试失败，请检查服务端实现!")

if __name__ == "__main__":
    run_all_tests()
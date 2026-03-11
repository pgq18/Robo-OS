import redis
import json
from typing import Dict, Any, Optional, List, Union, Callable
import atexit
import signal
import sys


class RedisClient:
    """
    Redis客户端类，用于管理机器人的属性更新
    """

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None, robot_agent=False):
        """
        初始化Redis客户端

        Args:
            host: Redis服务器主机地址
            port: Redis服务器端口
            db: 数据库编号
            password: Redis密码（如果有的话）
        """
        self.client = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
        self.registered_robots = set()
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.online_robots_list_key = "online_robots"  # 在线机器人列表的键名
        self.online_items_list_key = "online_items"   # 在线物品列表的键名

        self.robot_agent = robot_agent
        
        if self.robot_agent:
            # 注册退出处理函数
            atexit.register(self._cleanup_on_exit)
            # 注册信号处理函数，处理中断信号
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _cleanup_on_exit(self):
        """
        程序退出时的清理函数
        """
        self._unregister_all_robots()

    def _signal_handler(self, signum, frame):
        """
        信号处理函数
        """
        self._unregister_all_robots()
        sys.exit(0)

    def _unregister_all_robots(self):
        """
        取消注册所有机器人
        """
        print("Unregistering all robots...")
        for robot_name in list(self.registered_robots):
            self.unregister_robot(robot_name)
        # 注意：不删除物品列表，因为物品信息需要持久化保存

    def register_robot(self, robot_name: str, robot_properties: Dict[str, Any]) -> bool:
        """
        注册机器人到Redis

        Args:
            robot_name: 机器人名称
            robot_properties: 机器人属性字典

        Returns:
            bool: 注册成功返回True，否则返回False
        """
        try:
            key = f"robot:{robot_name}"
            # 处理复杂对象，转换为JSON字符串
            processed_properties = {}
            for prop_name, prop_value in robot_properties.items():
                if isinstance(prop_value, (dict, list)):
                    processed_properties[prop_name] = json.dumps(prop_value)
                else:
                    processed_properties[prop_name] = prop_value

            self.client.hmset(key, processed_properties)
            self.registered_robots.add(robot_name)
            # 将机器人添加到在线机器人列表中
            self.client.lpush(self.online_robots_list_key, robot_name)
            return True
        except Exception as e:
            print(f"注册机器人时出错: {e}")
            return False

    def unregister_robot(self, robot_name: str) -> bool:
        """
        从Redis中取消注册机器人

        Args:
            robot_name: 机器人名称

        Returns:
            bool: 取消注册成功返回True，否则返回False
        """
        try:
            key = f"robot:{robot_name}"
            if self.client.exists(key):
                self.client.delete(key)
            if robot_name in self.registered_robots:
                self.registered_robots.remove(robot_name)
            # 从在线机器人列表中移除机器人
            self.client.lrem(self.online_robots_list_key, 0, robot_name)
            return True
        except Exception as e:
            print(f"取消注册机器人时出错: {e}")
            return False

    def update_robot_property(self, robot_name: str, property_name: str, property_value: Any) -> bool:
        """
        更新机器人的指定属性

        Args:
            robot_name: 机器人名称
            property_name: 属性名称
            property_value: 属性值

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        try:
            key = f"robot:{robot_name}"
            # 如果属性值是复杂对象，转换为JSON字符串
            if isinstance(property_value, (dict, list)):
                value = json.dumps(property_value)
            else:
                value = property_value
            self.client.hset(key, property_name, value)
            return True
        except Exception as e:
            print(f"更新机器人属性时出错: {e}")
            return False

    def update_robot_properties(self, robot_name: str, properties: Dict[str, Any]) -> bool:
        """
        批量更新机器人的多个属性

        Args:
            robot_name: 机器人名称
            properties: 属性字典

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        try:
            key = f"robot:{robot_name}"
            # 处理复杂对象，转换为JSON字符串
            processed_properties = {}
            for prop_name, prop_value in properties.items():
                if isinstance(prop_value, (dict, list)):
                    processed_properties[prop_name] = json.dumps(prop_value)
                else:
                    processed_properties[prop_name] = prop_value

            self.client.hmset(key, processed_properties)
            return True
        except Exception as e:
            print(f"批量更新机器人属性时出错: {e}")
            return False

    def get_robot_property(self, robot_name: str, property_name: str) -> Optional[Any]:
        """
        获取机器人的指定属性

        Args:
            robot_name: 机器人名称
            property_name: 属性名称

        Returns:
            Optional[Any]: 属性值，如果不存在则返回None
        """
        try:
            key = f"robot:{robot_name}"
            value = self.client.hget(key, property_name)
            
            # 尝试解析JSON字符串
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            print(f"获取机器人属性时出错: {e}")
            return None

    def get_robot_all_properties(self, robot_name: str) -> Optional[Dict[str, Any]]:
        """
        获取机器人的所有属性

        Args:
            robot_name: 机器人名称

        Returns:
            Optional[Dict[str, Any]]: 包含所有属性的字典，如果出错则返回None
        """
        try:
            key = f"robot:{robot_name}"
            properties = self.client.hgetall(key)
            
            # 尝试解析JSON字符串
            parsed_properties = {}
            for prop_name, prop_value in properties.items():
                try:
                    parsed_properties[prop_name] = json.loads(prop_value)
                except json.JSONDecodeError:
                    parsed_properties[prop_name] = prop_value
                    
            return parsed_properties
        except Exception as e:
            print(f"获取机器人所有属性时出错: {e}")
            return None

    def delete_robot_property(self, robot_name: str, property_name: str) -> bool:
        """
        删除机器人的指定属性

        Args:
            robot_name: 机器人名称
            property_name: 属性名称

        Returns:
            bool: 删除成功返回True，否则返回False
        """
        try:
            key = f"robot:{robot_name}"
            return bool(self.client.hdel(key, property_name))
        except Exception as e:
            print(f"删除机器人属性时出错: {e}")
            return False

    def robot_exists(self, robot_name: str) -> bool:
        """
        检查机器人是否存在

        Args:
            robot_name: 机器人名称

        Returns:
            bool: 存在返回True，否则返回False
        """
        try:
            key = f"robot:{robot_name}"
            return bool(self.client.exists(key))
        except Exception as e:
            print(f"检查机器人是否存在时出错: {e}")
            return False

    def get_online_robots(self) -> List[str]:
        """
        获取当前在线的机器人列表

        Returns:
            List[str]: 在线机器人名称列表
        """
        try:
            return self.client.lrange(self.online_robots_list_key, 0, -1)
        except Exception as e:
            print(f"获取在线机器人列表时出错: {e}")
            return []

    def update_robot_state(self, robot_name: str, state: str) -> bool:
        """
        更新机器人状态

        Args:
            robot_name: 机器人名称
            state: 新的状态

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.update_robot_property(robot_name, "robot_state", state)

    def update_robot_position(self, robot_name: str, position: str) -> bool:
        """
        更新机器人位置

        Args:
            robot_name: 机器人名称
            position: 新的位置

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.update_robot_property(robot_name, "current_position", position)

    def update_robot_tools(self, robot_name: str, tools: List[str]) -> bool:
        """
        更新机器人工具列表

        Args:
            robot_name: 机器人名称
            tools: 工具列表

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.update_robot_property(robot_name, "robot_tool", tools)

    def add_item(self, item_name: str, item_properties: Dict[str, Any]) -> bool:
        """
        添加物品到Redis

        Args:
            item_name: 物品名称
            item_properties: 物品属性字典

        Returns:
            bool: 添加成功返回True，否则返回False
        """
        try:
            key = f"item:{item_name}"
            # 处理复杂对象，转换为JSON字符串
            processed_properties = {}
            for prop_name, prop_value in item_properties.items():
                if isinstance(prop_value, (dict, list)):
                    processed_properties[prop_name] = json.dumps(prop_value)
                else:
                    processed_properties[prop_name] = prop_value

            self.client.hmset(key, processed_properties)
            # 将物品添加到在线物品列表中
            self.client.lpush(self.online_items_list_key, item_name)
            return True
        except Exception as e:
            print(f"添加物品时出错: {e}")
            return False

    def update_item_property(self, item_name: str, property_name: str, property_value: Any) -> bool:
        """
        更新物品的指定属性

        Args:
            item_name: 物品名称
            property_name: 属性名称
            property_value: 属性值

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        try:
            key = f"item:{item_name}"
            # 如果属性值是复杂对象，转换为JSON字符串
            if isinstance(property_value, (dict, list)):
                value = json.dumps(property_value)
            else:
                value = property_value
            self.client.hset(key, property_name, value)
            return True
        except Exception as e:
            print(f"更新物品属性时出错: {e}")
            return False

    def update_item_properties(self, item_name: str, properties: Dict[str, Any]) -> bool:
        """
        批量更新物品的多个属性

        Args:
            item_name: 物品名称
            properties: 属性字典

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        try:
            key = f"item:{item_name}"
            # 处理复杂对象，转换为JSON字符串
            processed_properties = {}
            for prop_name, prop_value in properties.items():
                if isinstance(prop_value, (dict, list)):
                    processed_properties[prop_name] = json.dumps(prop_value)
                else:
                    processed_properties[prop_name] = prop_value

            self.client.hmset(key, processed_properties)
            return True
        except Exception as e:
            print(f"批量更新物品属性时出错: {e}")
            return False

    def get_item_property(self, item_name: str, property_name: str) -> Optional[Any]:
        """
        获取物品的指定属性

        Args:
            item_name: 物品名称
            property_name: 属性名称

        Returns:
            Optional[Any]: 属性值，如果不存在则返回None
        """
        try:
            key = f"item:{item_name}"
            value = self.client.hget(key, property_name)
            
            # 尝试解析JSON字符串
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            print(f"获取物品属性时出错: {e}")
            return None

    def get_item_all_properties(self, item_name: str) -> Optional[Dict[str, Any]]:
        """
        获取物品的所有属性

        Args:
            item_name: 物品名称

        Returns:
            Optional[Dict[str, Any]]: 包含所有属性的字典，如果出错则返回None
        """
        try:
            key = f"item:{item_name}"
            properties = self.client.hgetall(key)
            
            # 尝试解析JSON字符串
            parsed_properties = {}
            for prop_name, prop_value in properties.items():
                try:
                    parsed_properties[prop_name] = json.loads(prop_value)
                except json.JSONDecodeError:
                    parsed_properties[prop_name] = prop_value
                    
            return parsed_properties
        except Exception as e:
            print(f"获取物品所有属性时出错: {e}")
            return None

    def delete_item_property(self, item_name: str, property_name: str) -> bool:
        """
        删除物品的指定属性

        Args:
            item_name: 物品名称
            property_name: 属性名称

        Returns:
            bool: 删除成功返回True，否则返回False
        """
        try:
            key = f"item:{item_name}"
            return bool(self.client.hdel(key, property_name))
        except Exception as e:
            print(f"删除物品属性时出错: {e}")
            return False

    def delete_item(self, item_name: str) -> bool:
        """
        删除物品

        Args:
            item_name: 物品名称

        Returns:
            bool: 删除成功返回True，否则返回False
        """
        try:
            key = f"item:{item_name}"
            # 从在线物品列表中移除物品
            self.client.lrem(self.online_items_list_key, 0, item_name)
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"删除物品时出错: {e}")
            return False

    def item_exists(self, item_name: str) -> bool:
        """
        检查物品是否存在

        Args:
            item_name: 物品名称

        Returns:
            bool: 存在返回True，否则返回False
        """
        try:
            key = f"item:{item_name}"
            return bool(self.client.exists(key))
        except Exception as e:
            print(f"检查物品是否存在时出错: {e}")
            return False

    def get_online_items(self) -> List[str]:
        """
        获取当前在线的物品列表

        Returns:
            List[str]: 在线物品名称列表
        """
        try:
            return self.client.lrange(self.online_items_list_key, 0, -1)
        except Exception as e:
            print(f"获取在线物品列表时出错: {e}")
            return []
            
    # ==================== 发布/订阅机制 ====================

    def publish_task(self, robot_name: str, task: Dict[str, Any]) -> bool:
        """
        向指定机器人发布任务指令

        Args:
            robot_name: 机器人名称
            task: 任务指令字典

        Returns:
            bool: 发布成功返回True，否则返回False
        """
        try:
            channel = f"task:{robot_name}"
            task_json = json.dumps(task)
            self.client.publish(channel, task_json)
            return True
        except Exception as e:
            print(f"发布任务指令时出错: {e}")
            return False

    def subscribe_task(self, robot_name: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        订阅指定机器人的任务指令

        Args:
            robot_name: 机器人名称
            handler: 处理任务指令的回调函数
        """
        try:
            channel = f"task:{robot_name}"
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            
            # 处理消息
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # 检查消息数据是否为空或仅包含空白字符
                        data = message['data']
                        if not data or not str(data).strip():
                            print("收到空的任务指令消息")
                            continue
                        
                        # 尝试解析JSON之前，先打印数据类型和内容
                        # print(f"收到任务指令数据类型: {type(data)}")
                        # print(f"收到任务指令数据内容: {repr(data)}")
                        
                        # 如果数据是bytes类型，尝试解码
                        if isinstance(data, bytes):
                            data = data.decode('utf-8')
                            
                        task = json.loads(data)
                        handler(task)
                    except json.JSONDecodeError as e:
                        print(f"解析任务指令时出错: {e}")
                        print(f"收到的数据类型: {type(data)}")
                        print(f"收到的数据内容: {repr(data)}")
                    except Exception as e:
                        print(f"处理任务指令时发生未知错误: {e}")
                        print(f"收到的数据类型: {type(data)}")
                        print(f"收到的数据内容: {repr(data)}")
        except Exception as e:
            print(f"订阅任务指令时出错: {e}")

    def publish_result(self, robot_name: str, result: Dict[str, Any]) -> bool:
        """
        发布机器人任务执行结果

        Args:
            robot_name: 机器人名称
            result: 任务执行结果字典

        Returns:
            bool: 发布成功返回True，否则返回False
        """
        try:
            channel = f"result:{robot_name}"
            result_json = json.dumps(result)
            self.client.publish(channel, result_json)
            return True
        except Exception as e:
            print(f"发布任务结果时出错: {e}")
            return False

    def subscribe_result(self, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        订阅所有机器人的任务执行结果

        Args:
            handler: 处理任务执行结果的回调函数，参数为(robot_name, result)
        """
        try:
            pubsub = self.client.pubsub()
            # 订阅所有机器人结果频道
            pubsub.psubscribe("result:*")
            
            # 处理消息
            for message in pubsub.listen():
                if message['type'] == 'pmessage':
                    try:
                        # 从频道名中提取机器人名称
                        robot_name = message['channel'].split(':', 1)[1]
                        result = json.loads(message['data'])
                        handler(robot_name, result)
                    except (json.JSONDecodeError, IndexError) as e:
                        print(f"解析任务结果时出错: {e}")
        except Exception as e:
            print(f"订阅任务结果时出错: {e}")

    def publish_exception(self, exception_data: Dict[str, Any]) -> bool:
        """
        发布异常信息

        Args:
            exception_data: 异常信息字典

        Returns:
            bool: 发布成功返回True，否则返回False
        """
        try:
            channel = f"exception"
            exception_json = json.dumps(exception_data)
            self.client.publish(channel, exception_json)
            return True
        except Exception as e:
            print(f"发布异常信息时出错: {e}")
            return False

    def publish_planner_interrupt(self) -> bool:
        """
        向planner发布中断信号

        Returns:
            bool: 发布成功返回True，否则返回False
        """
        try:
            channel = "planner:interrupt"
            interrupt_signal = json.dumps({"type": "interrupt", "target": "planner"})
            self.client.publish(channel, interrupt_signal)
            return True
        except Exception as e:
            print(f"发布planner中断信号时出错: {e}")
            return False

    def publish_robot_agent_interrupt(self, robot_name: str) -> bool:
        """
        向指定的robot agent发布中断信号

        Args:
            robot_name: 机器人名称

        Returns:
            bool: 发布成功返回True，否则返回False
        """
        try:
            channel = f"robot:interrupt:{robot_name}"
            interrupt_signal = json.dumps({"type": "interrupt", "target": robot_name})
            self.client.publish(channel, interrupt_signal)
            return True
        except Exception as e:
            print(f"发布robot agent中断信号时出错: {e}")
            return False

    def publish_task_allocater_interrupt(self) -> bool:
        """
        向task_allocater发布中断信号

        Returns:
            bool: 发布成功返回True，否则返回False
        """
        try:
            channel = "task_allocater:interrupt"
            interrupt_signal = json.dumps({"type": "interrupt", "target": "task_allocater"})
            self.client.publish(channel, interrupt_signal)
            return True
        except Exception as e:
            print(f"发布task_allocater中断信号时出错: {e}")
            return False

    def subscribe_exception(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        订阅异常信息

        Args:
            handler: 处理异常信息的回调函数
        """
        try:
            channel = "exception"
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            
            # 处理消息
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        exception_data = json.loads(message['data'])
                        handler(exception_data)
                    except json.JSONDecodeError as e:
                        print(f"解析异常信息时出错: {e}")
        except Exception as e:
            print(f"订阅异常信息时出错: {e}")

    def subscribe_planner_interrupt(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        订阅planner中断信号

        Args:
            handler: 处理中断信号的回调函数
        """
        try:
            channel = "planner:interrupt"
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            
            # 处理消息
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        interrupt_signal = json.loads(message['data'])
                        handler(interrupt_signal)
                    except json.JSONDecodeError as e:
                        print(f"解析planner中断信号时出错: {e}")
        except Exception as e:
            print(f"订阅planner中断信号时出错: {e}")

    def subscribe_robot_agent_interrupt(self, robot_name: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        订阅指定robot agent的中断信号

        Args:
            robot_name: 机器人名称
            handler: 处理中断信号的回调函数
        """
        try:
            channel = f"robot:interrupt:{robot_name}"
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            
            # 处理消息
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        interrupt_signal = json.loads(message['data'])
                        handler(interrupt_signal)
                    except json.JSONDecodeError as e:
                        print(f"解析robot agent中断信号时出错: {e}")
        except Exception as e:
            print(f"订阅robot agent中断信号时出错: {e}")

    def subscribe_task_allocater_interrupt(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        订阅task_allocater中断信号

        Args:
            handler: 处理中断信号的回调函数
        """
        try:
            channel = "task_allocater:interrupt"
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            
            # 处理消息
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        interrupt_signal = json.loads(message['data'])
                        handler(interrupt_signal)
                    except json.JSONDecodeError as e:
                        print(f"解析task_allocater中断信号时出错: {e}")
        except Exception as e:
            print(f"订阅task_allocater中断信号时出错: {e}")

    def publish_subtask_list(self, subtask_list: List[Dict[str, Any]]) -> bool:
        """
        发布子任务列表给指定机器人

        Args:
            robot_name: 机器人名称
            subtask_list: 子任务列表

        Returns:
            bool: 发布成功返回True，否则返回False
        """
        try:
            channel = "subtask_list"
            subtask_json = json.dumps(subtask_list)
            self.client.publish(channel, subtask_json)
            return True
        except Exception as e:
            print(f"发布子任务列表时出错: {e}")
            return False

    def publish_all_tasks_completed(self, completion_status: Dict[str, Any]) -> bool:
        """
        发布所有任务完成状态

        Args:
            completion_status: 任务完成状态信息字典，应包含以下字段：
                - status: 任务完成状态（成功/失败）
                - task_id: 完成的任务ID（可选）
                - robot_name: 执行任务的机器人名称（可选）
                - timestamp: 任务完成时间戳（可选）
                - details: 任务完成的详细信息（可选）

        Returns:
            bool: 发布成功返回True，否则返回False
        """
        try:
            channel = "all_tasks_completed"
            status_json = json.dumps(completion_status)
            self.client.publish(channel, status_json)
            return True
        except Exception as e:
            print(f"发布任务完成状态时出错: {e}")
            return False

    def subscribe_subtask_list(self, handler: Callable[[List[Dict[str, Any]]], None]) -> None:
        """
        订阅指定机器人的子任务列表

        Args:
            robot_name: 机器人名称
            handler: 处理子任务列表的回调函数
        """
        try:
            channel = "subtask_list"
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            
            # 处理消息
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        subtask_list = json.loads(message['data'])
                        handler(subtask_list)
                    except json.JSONDecodeError as e:
                        print(f"解析子任务列表时出错: {e}")
        except Exception as e:
            print(f"订阅子任务列表时出错: {e}")

    def subscribe_all_tasks_completed(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        订阅所有任务完成状态

        Args:
            handler: 处理任务完成状态的回调函数
        """
        try:
            channel = "all_tasks_completed"
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            
            # 处理消息
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        completion_status = json.loads(message['data'])
                        handler(completion_status)
                    except json.JSONDecodeError as e:
                        print(f"解析任务完成状态时出错: {e}")
        except Exception as e:
            print(f"订阅任务完成状态时出错: {e}")

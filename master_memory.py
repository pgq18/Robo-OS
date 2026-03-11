from utils.utils import Config
from utils.redis_client import RedisClient
from utils.milvus_client import MilvusClient
import time
import json
from typing import Dict, Any, Optional, List, Union, Callable

class MasterMemory():
    def __init__(self, redis_client: RedisClient, milvus_server_ip: str=None):
        self.redis_client = redis_client
        if milvus_server_ip is not None:
            self.milvus_client = MilvusClient(milvus_server_ip)
        else:
            pass
        
    def get_online_robots(self):
        return self.redis_client.get_online_robots()
    
    def get_idle_robots(self):
        """
        获取所有状态为idle的机器人列表

        Returns:
            list: 包含所有空闲机器人名称的列表
        """
        idle_robots = []
        # 获取所有在线机器人
        online_robots = self.redis_client.get_online_robots()
        
        # 检查每个机器人的状态
        for robot_name in online_robots:
            state = self.redis_client.get_robot_property(robot_name, "robot_state")
            if state == "idle":
                idle_robots.append(robot_name)
                
        return idle_robots
    
    def get_robot_properties(self, robot_name: str):
        return self.redis_client.get_robot_all_properties(robot_name)
    
    def get_robot_property(self, robot_name: str, property_name: str):
        return self.redis_client.get_robot_property(robot_name, property_name)
    
    def init_items(self, config_path: str):
        config = Config.load_config(config_path)
        items = config['scene']
        for i in range(len(items)):
            self.redis_client.add_item(items[i]['recep_name'], items[i])

    def get_online_items(self):
        return self.redis_client.get_online_items()
    
    def get_item_property(self, item_name: str, property_name: str):
        return self.redis_client.get_item_property(item_name, property_name)

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
        return self.redis_client.update_item_property(item_name, property_name, property_value)

    def add_object_to_item(self, item_name: str, object_name: list) -> bool:
        """
        向指定物品中添加物体

        Args:
            item_name: 物品名称
            object_name: 要添加的物体名称list

        Returns:
            bool: 添加成功返回True，否则返回False
        """
        # 获取物品当前属性
        item_properties = self.redis_client.get_item_all_properties(item_name)
        if not item_properties:
            return False
        
        # 获取当前物体列表
        recep_objects = item_properties.get('recep_object', [])
        if isinstance(recep_objects, str):
            try:
                recep_objects = json.loads(recep_objects)
            except json.JSONDecodeError:
                recep_objects = []
        
        # 添加新物体
        updated = False
        for obj in object_name:
            if obj not in recep_objects:
                recep_objects.append(obj)
                updated = True
        
        # 更新物品属性
        if updated:
            return self.redis_client.update_item_property(item_name, 'recep_object', recep_objects)
        return True  # 物体已存在，视为添加成功

    def remove_object_from_item(self, item_name: str, object_name: str) -> bool:
        """
        从指定物品中删除物体

        Args:
            item_name: 物品名称
            object_name: 要删除的物体名称

        Returns:
            bool: 删除成功返回True，否则返回False
        """
        # 获取物品当前属性
        item_properties = self.redis_client.get_item_all_properties(item_name)
        if not item_properties:
            return False
        
        # 获取当前物体列表
        recep_objects = item_properties.get('recep_object', [])
        if isinstance(recep_objects, str):
            try:
                recep_objects = json.loads(recep_objects)
            except json.JSONDecodeError:
                recep_objects = []
        
        # 删除物体
        if object_name in recep_objects:
            recep_objects.remove(object_name)
            # 更新物品属性
            return self.redis_client.update_item_property(item_name, 'recep_object', recep_objects)
        return True  # 物体不存在，视为删除成功

    def register_robot(self, robot_name: str, robot_properties):
        return self.redis_client.register_robot(robot_name, robot_properties)
    
    def update_robot_state(self, robot_name: str, state: str) -> bool:
        """
        更新机器人状态

        Args:
            robot_name: 机器人名称
            state: 新的状态

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.redis_client.update_robot_state(robot_name, state)
    
    def update_robot_position(self, robot_name: str, position: str) -> bool:
        """
        更新机器人位置

        Args:
            robot_name: 机器人名称
            position: 新的位置

        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.redis_client.update_robot_position(robot_name, position)
    
    def add_object_to_robot(self, robot_name: str, object_name: list) -> bool:
        """
        向指定机器人添加携带的物体

        Args:
            robot_name: 机器人名称
            object_name: 要添加的物体名称list

        Returns:
            bool: 添加成功返回True，否则返回False
        """
        # 获取机器人当前属性
        robot_properties = self.redis_client.get_robot_all_properties(robot_name)
        if not robot_properties:
            return False
        
        # 获取当前携带的物体列表
        carrying_objects = robot_properties.get('carrying_objects', [])
        if isinstance(carrying_objects, str):
            try:
                carrying_objects = json.loads(carrying_objects)
            except json.JSONDecodeError:
                carrying_objects = []
        
        # 添加新物体
        updated = False
        for obj in object_name:
            if obj not in carrying_objects:
                carrying_objects.append(obj)
                updated = True
        
        # 更新机器人属性
        if updated:
            return self.redis_client.update_robot_property(robot_name, 'carrying_objects', carrying_objects)
        return True  # 物体已存在，视为添加成功

    def remove_object_from_robot(self, robot_name: str, object_name: str) -> bool:
        """
        从指定机器人删除携带的物体

        Args:
            robot_name: 机器人名称
            object_name: 要删除的物体名称

        Returns:
            bool: 删除成功返回True，否则返回False
        """
        # 获取机器人当前属性
        robot_properties = self.redis_client.get_robot_all_properties(robot_name)
        if not robot_properties:
            return False
        
        # 获取当前携带的物体列表
        carrying_objects = robot_properties.get('carrying_objects', [])
        if isinstance(carrying_objects, str):
            try:
                carrying_objects = json.loads(carrying_objects)
            except json.JSONDecodeError:
                carrying_objects = []
        
        # 删除物体
        if object_name == None:
            carrying_objects = []
        else:
            if object_name in carrying_objects:
                carrying_objects.remove(object_name)
                # 更新机器人属性
                return self.redis_client.update_robot_property(robot_name, 'carrying_objects', carrying_objects)
        return True  # 物体不存在，视为删除成功

    def insert_experience(self, data):
        inserted_time = int(time.time())
        inserted_data = [
            {
                "description": data,
                "timestamp": inserted_time
            }
        ]
        return self.milvus_client.insert_experience(inserted_data)
    
    def search_experience(self, query_data):
        query_data = [query_data]
        experience = self.milvus_client.search_experience(query_data)
        print(experience)
        return experience
    
    def update_task_summary(self, robot_name: str, task_id: str, summary: str) -> bool:
        """
        存储机器人执行子任务的总结
        
        Args:
            robot_name: 机器人名称
            task_id: 任务ID
            summary: 任务总结内容
            
        Returns:
            bool: 存储成功返回True，否则返回False
        """
        try:
            # 构造任务总结键名
            key = "task_summary"
            
            # 获取现有的总结列表
            existing_summary = self.redis_client.client.get(key)
            if existing_summary:
                try:
                    summary_list = json.loads(existing_summary)
                except json.JSONDecodeError:
                    summary_list = []
            else:
                summary_list = []
            
            # 添加新的总结条目
            sub_summary = f'{task_id}: [{robot_name}]: {summary}'
            summary_list.append(sub_summary)
            
            # 存储到Redis
            self.redis_client.client.set(key, json.dumps(summary_list))
            
            return True
        except Exception as e:
            print(f"存储任务总结时出错: {e}")
            return False
    
    def clear_all_memory(self) -> bool:
        """
        清除所有内存（包括Redis中的所有数据和Milvus中的经验数据）
        
        Returns:
            bool: 清除成功返回True，否则返回False
        """
        try:
            # 清除Redis中的所有数据
            self.redis_client.client.flushdb()
            
            # 注意：Milvus中的数据是持久化的，无法通过客户端直接清除
            # 如果需要清除Milvus数据，需要通过Milvus服务端操作
            
            return True
        except Exception as e:
            print(f"清除所有内存时出错: {e}")
            return False
    
    def clear_summary(self) -> bool:
        """
        清除记忆中的summary数据
        
        Returns:
            bool: 清除成功返回True，否则返回False
        """
        try:
            key = "task_summary"
            # 删除summary键
            self.redis_client.client.delete(key)
            return True
        except Exception as e:
            print(f"清除summary时出错: {e}")
            return False
    
    def get_all_summaries(self) -> list:
        """
        获取记忆中所有summary数据
        
        Returns:
            list: 包含所有summary的列表，如果出错则返回空列表
        """
        try:
            key = "task_summary"
            # 获取summary数据
            summary_data = self.redis_client.client.get(key)
            if summary_data:
                try:
                    return json.loads(summary_data)
                except json.JSONDecodeError:
                    return []
            return []
        except Exception as e:
            print(f"获取所有summary时出错: {e}")
            return []
    
if __name__ == "__main__":
    config = Config.load_config("./config/planner_agent_config.yaml")
    redis_client = RedisClient(
            host=config['redis']['HOST'], 
            port=config['redis']['PORT'], 
            db=config['redis']['DB'], 
            password=config['redis']['PASSWORD'],
            robot_agent=False
            )
    master_memory = MasterMemory(redis_client)
    print(master_memory.get_online_robots())
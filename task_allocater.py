"""
Task Allocator Module for managing and distributing tasks among robots in the system.
This module handles task allocation, result processing, and coordination between multiple robots.
"""

from utils.utils import Config
from utils.redis_client import RedisClient
from master_memory import MasterMemory
import threading
import time
from utils.logger import get_logger

logger = get_logger(__name__)

# Sample tasks for demonstration purposes
tasks = [
        {"robot_name": "robot2", "subtask": "navigate to Loading Area", "subtask_order": "0"},
        {"robot_name": "robot1", "subtask": "grasp Cargo 1", "subtask_order": "1"},
        {"robot_name": "robot1", "subtask": "place Cargo 1 on robot2", "subtask_order": "2"},
        {"robot_name": "robot2", "subtask": "navigate to Unloading Area", "subtask_order": "3"},
        {"robot_name": "robot2", "subtask": "unload Cargo 1", "subtask_order": "4"}
    ]

class TaskAllocater():
    """
    TaskAllocater class manages the distribution of tasks to robots and monitors their execution.
    It handles task allocation, result collection, and coordination of multi-robot operations.
    """
    
    def __init__(self, config_path):
        """
        Initialize the TaskAllocater with configuration from the provided path.
        
        Args:
            config_path (str): Path to the configuration file
        """
        config = Config.load_config(config_path)
        self.redis_client = RedisClient(
            host=config['redis']['HOST'], 
            port=config['redis']['PORT'], 
            db=config['redis']['DB'], 
            password=config['redis']['PASSWORD'],
            robot_agent=False
            )
        self.master_memory = MasterMemory(self.redis_client)
        self.task_all_success = False
        self.task_complete = threading.Event()
        self.task_id = 0
        self.subtask_id_list = []
        result_thread = threading.Thread(target=self.redis_client.subscribe_result, args=(self._result_handler,))
        result_thread.daemon = True
        result_thread.start()
        allocater_thread = threading.Thread(target=self.redis_client.subscribe_subtask_list, args=(self._task_allocater_handler,))
        allocater_thread.daemon = True
        allocater_thread.start()
        logger.info("[Task Allocater] TaskAllocater initialized successfully")
    
    # Result handling callback function
    def _result_handler(self, robot_name_received, result):
        """
        Handle results from robots after task execution.
        
        Args:
            robot_name_received (str): Name of the robot that executed the task
            result (dict): Result data including status, task_id, and execution result
        """
        task_status = result['status']
        task_id = result['task_id']
        self.subtask_id_list.remove(task_id)
        if task_status == 'success':
            logger.info("[Task Allocater] 机器人 %s 任务执行成功，结果为：%s", robot_name_received, result['result'])
            self.master_memory.update_task_summary(robot_name_received, task_id, result['result'])
            if len(self.subtask_id_list) == 0:
                self.task_complete.set()
                self.task_all_success = True
        elif task_status == 'failure':
            logger.error("[Task Allocater] 机器人 %s 运行任务失败，失败原因为：%s", robot_name_received, result['result'])
            self.master_memory.update_task_summary(robot_name_received, task_id, result['result'])
            self.redis_client.publish_exception({'role': 'task_allocater', 'data': {'status': 'failure', 'message': result}})
            self.task_complete.set()
            self.task_all_success = False
        else:
            logger.warning("[Task Allocater] 机器人 %s 返回格式不正确", robot_name_received)
            self.master_memory.update_task_summary(robot_name_received, task_id, f'机器人 {robot_name_received} 返回格式不正确')
            self.redis_client.publish_exception({'role': 'task_allocater', 'data': {'status': 'failure', 'message': result}})
            self.task_complete.set()
            self.task_all_success = False

    def _task_allocater_handler(self, data):
        """
        Handle incoming task allocation requests.
        
        Args:
            data (list): List of tasks to be allocated
        """
        self.allocate(data)

    def allocate(self, task_list):
        """
        Allocate and execute tasks in the provided task list.
        
        Args:
            task_list (list): List of tasks to be executed
            
        Returns:
            bool: True if all tasks were executed successfully, False otherwise
        """
        t1 = time.time()
        self.master_memory.clear_summary()
        i = 0
        task_allocate_list = []
        while i < len(task_list):                            
            subtask = task_list[i]
            subtask_order = subtask['subtask_order']
            next_index = i + 1
            while next_index < len(task_list) and task_list[next_index]["subtask_order"] == subtask_order:
                next_index += 1
            task_allocate_list.append(task_list[i:next_index])
            i = next_index
        self.task_all_success = True
        self.task_complete.clear()
        logger.info("[Task Allocater] Starting to allocate %d task groups", len(task_allocate_list))
        for sub_tasks in task_allocate_list:
            self.subtask_id_list = []
            self.task_complete.clear()
            for task in sub_tasks:
                task_data = {
                    "task_id": self.task_id,
                    "command": task['subtask']
                }
                self.subtask_id_list.append(self.task_id)
                self.task_id += 1
                self.redis_client.publish_task(task['robot_name'], task_data)
                logger.info("[Task Allocater] 发送给机器人 %s 执行%s", task['robot_name'], task_data)
            self.task_complete.wait()
            if not self.task_all_success:
                t2 = time.time()
                logger.error("[Task Allocater] 任务失败, 总耗时%s秒", t2-t1)
                break
        if self.task_all_success:
            t2 = time.time()
            logger.info("[Task Allocater] 所有任务成功完成, 总耗时%s秒", t2-t1)
            self.redis_client.publish_all_tasks_completed({'role': 'task_allocater', 'data': {'status':'success'}})
            return True
        self.task_all_success = True
        return False

if __name__ == "__main__":
    """
    Main execution block to initialize and run the TaskAllocater.
    """
    TA = TaskAllocater("./config/planner_agent_config.yaml")
    TA.allocate(tasks)
    while True:
        time.sleep(1)
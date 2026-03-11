"""
Robot Agent Module for controlling and managing individual robots in the system.
This module handles robot registration, task execution, and communication with Redis.
"""

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.utils import Config, parse_response
from utils.redis_client import RedisClient
from utils.model import RobotModel
from master_memory import MasterMemory
import threading
import tools
from robot_prompt import SYSTEM_PROMPT, USER_PROMPT, CARRYING_INFORMATION
import time
from utils.logger import get_logger

logger = get_logger(__name__)

class RobotAgent():
    """
    RobotAgent class manages individual robot operations including task execution,
    state management, and communication with the central system via Redis.
    """
    
    def __init__(self, config_path):
        """
        Initialize the RobotAgent with configuration from the provided path.
        
        Args:
            config_path (str): Path to the robot agent configuration file
        """
        config = Config.load_config(config_path)
        self.robot_config = config['robot'][0]
        tools_dict = tools.get_all_tools()
        self.tools_list = list(tools_dict.keys())
        self.model = RobotModel(
            config['model']['MODEL_NAME'], 
            config['model']['CLOUD_API_KEY'], 
            config['model']['CLOUD_SERVER'],
            self.tools_list,
            SYSTEM_PROMPT
            )
        self.redis_client = RedisClient(
            host=config['redis']['HOST'], 
            port=config['redis']['PORT'], 
            db=config['redis']['DB'], 
            password=config['redis']['PASSWORD'],
            robot_agent=True
            )
        self.master_memory = MasterMemory(self.redis_client)
        task_thread = threading.Thread(target=self.redis_client.subscribe_task, args=(self.robot_config['robot_name'], self._task_handler))
        task_thread.daemon = True
        task_thread.start()
        logger.info("[Robot Agent] RobotAgent for %s initialized successfully", self.robot_config['robot_name'])

    def register_robot(self):
        """
        Register the robot to Redis database with its properties.
        
        Returns:
            bool: True if registration is successful, False otherwise
        """
        robot_name = self.robot_config['robot_name']
        robot_properties = {
            'robot_type': self.robot_config['robot_type'],
            'robot_state': self.robot_config['robot_state'],
            'robot_tool': self.robot_config['robot_tool'],
            'current_position': self.robot_config['current_position'],
            'navigate_position': self.robot_config['navigate_position'],
            'carrying_objects': self.robot_config['carrying_objects']  # Initialize carrying objects list
        }
        
        success = self.master_memory.register_robot(robot_name, robot_properties)
        if success:
            logger.info("[Robot Agent] 机器人 %s 成功注册到Redis", robot_name)
        else:
            logger.error("[Robot Agent] 机器人 %s 注册失败", robot_name)
        return success
    
    # Task handling callback function
    def _task_handler(self, task):
        """
        Handle incoming tasks assigned to this robot.
        
        Args:
            task (dict): Task information containing task_id and command
        """
        robot_name = self.robot_config['robot_name']
        logger.info("[Robot Agent] [%s] 收到任务指令: %s", robot_name, task)
        self.master_memory.update_robot_state(robot_name, "busy")
        
        # Execute task and return results
        t1 = time.time()
        response = self.carry_task(task['command'])
        logger.debug("[Robot Agent] [%s] Raw response: %s", robot_name, response)
        response = response[-1]['content']
        t2 = time.time()
        logger.debug("[Robot Agent] [%s] Response content: %s", robot_name, response)
        response_json = parse_response(response)
        logger.info("[Robot Agent] [%s] 任务执行完毕，返回结果: %s", robot_name, response_json['summary'])
        if response_json['final_status'] == 'success':
            status = 'success'
            logger.info("[Robot Agent] [%s] 任务执行成功，耗时: %fs", robot_name, t2-t1)
        else:
            status = 'failure'
            logger.error("[Robot Agent] [%s] 任务执行失败，耗时: %fs", robot_name, t2-t1)
        result_data = {
            "task_id": task['task_id'],
            "status": status,
            "result": response_json['summary'],
            "execution_time": t2-t1
        }
        self.master_memory.update_robot_state(robot_name, "idle")
        logger.info("[Robot Agent] [%s] 任务执行完成，返回结果...", robot_name)
        self.redis_client.publish_result(robot_name, result_data)

    def carry_task(self, task):
        """
        Execute the given task using the robot's model and tools.
        
        Args:
            task (str): Task command to be executed
            
        Returns:
            list: Model response containing the execution result
        """
        previous_tasks = self.master_memory.get_all_summaries()
        # previous_tasks = []
        robot_name = self.robot_config['robot_name']
        robot_type = self.robot_config['robot_type']
        robot_all_properties = self.redis_client.get_robot_all_properties(robot_name)
        current_position = robot_all_properties['current_position']
        robot_state = robot_all_properties['robot_state']
        robot_tools = self.robot_config['robot_tool']
        carrying_information = CARRYING_INFORMATION.format(carrying_objects=robot_all_properties['carrying_objects'])
        user_prompt = USER_PROMPT.format(
            task=task,
            previous_tasks=previous_tasks,
            robot_name=robot_name,
            robot_type=robot_type,
            current_position=current_position,
            robot_state=robot_state,
            robot_tools=robot_tools,
            carrying_information=carrying_information
        )
        response = self.model.forward(user_prompt)
        logger.debug("[Robot Agent] [%s] Robot properties: %s", robot_name, robot_all_properties)
        return response


if __name__ == "__main__":
    """
    Main execution block to initialize and run the RobotAgent.
    """
    robot_agent = RobotAgent("./config/robot_agent_config.yaml")
    robot_agent.register_robot()
    while True:
        time.sleep(1)
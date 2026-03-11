from utils.model import PlannerModel
from utils.utils import Config, parse_response
from utils.redis_client import RedisClient
from utils.planner_prompt import MASTER_PLANNING_PLANNING, ROBOT_POSITION_INFO_TEMPLATE, ROBOT_TOOLS_INFO_TEMPLATE, SCENE_OBJECTS_INFO_TEMPLATE
from master_memory import MasterMemory
from utils.logger import get_logger

logger = get_logger(__name__)

class PlannerAgent():
    """
    Planner agent responsible for generating task plans based on the current scene state,
    robot capabilities, and previous experiences.
    """
    
    def __init__(self, config, redis_client: RedisClient):
        """
        Initialize the PlannerAgent with model configuration and Redis client.
        
        Args:
            config: Configuration dictionary containing model settings
            redis_client: Redis client instance for accessing robot and scene data
        """
        self.model = PlannerModel(
            config['model']['Planner']['MODEL_NAME'], 
            config['model']['Planner']['CLOUD_API_KEY'], 
            config['model']['Planner']['CLOUD_SERVER']
            )
        self.redis_client = redis_client
        self.master_memory = MasterMemory(self.redis_client, config['milvus']['BASE_URL'])
        logger.info("[Planner] PlannerAgent initialized successfully")

    def init_items(self, config_path: str):
        """
        Initialize items in the scene based on configuration file.
        
        Args:
            config_path: Path to the configuration file containing scene items
        """
        self.master_memory.init_items(config_path)
        
    def get_robot_properties(self, robot_name: str):
        """
        Get all properties of a specific robot.
        
        Args:
            robot_name: Name of the robot to retrieve properties for
            
        Returns:
            Dictionary containing all properties of the specified robot
        """
        return self.redis_client.get_robot_all_properties(robot_name)
    
    def get_idle_robots(self):
        """
        Get list of currently idle robots.
        
        Returns:
            List of names of idle robots
        """
        return self.master_memory.get_idle_robots()
    
    def save_items(self, config_path: str):
        """
        Save scene items from configuration file to Redis.
        
        Args:
            config_path: Path to the configuration file containing scene items
        """
        config = Config.load_config(config_path)
        items = config['scene']
        for i in range(len(items)):
            self.redis_client.add_item(items[i]['recep_name'], items[i])
    
    def generate_prompt(self, task):
        """
        Generate a prompt for the planning model based on current scene state.
        
        Args:
            task: The task description to be planned
            
        Returns:
            Formatted prompt string for the planning model
        """
        robot_name_list = self.master_memory.get_idle_robots()
        robot_description = [
            self.master_memory.get_robot_property(robot_name, 'robot_type')
            for robot_name in robot_name_list
        ]
        robot_position_info = [
            ROBOT_POSITION_INFO_TEMPLATE.format(
                robot_name=robot_name,
                initial_pos=self.master_memory.get_robot_properties(robot_name)['current_position'],
                target_pos=self.master_memory.get_robot_properties(robot_name)['navigate_position']
            )
            for robot_name in robot_name_list
        ]
        robot_tools_info = [
            ROBOT_TOOLS_INFO_TEMPLATE.format(
                robot_name=robot_name,
                tool_list=self.master_memory.get_robot_properties(robot_name)['robot_tool']
            )
            for robot_name in robot_name_list
        ]
        recep_name_list = self.master_memory.get_online_items()
        scene_object_info = [
            SCENE_OBJECTS_INFO_TEMPLATE.format(
                recep_name=recep_name,
                object_list=self.master_memory.get_item_property(recep_name, "recep_object")
            )
            for recep_name in recep_name_list
        ]
        # previous_experience = self.master_memory.search_experience(task)['data']['description']
        previous_experience = self.master_memory.search_experience(task)['data']
        if previous_experience != None:
            previous_experience = previous_experience['description']
        else:
            previous_experience = "None"
        print("-------------------------------------------------------------")
        print(previous_experience)
        return MASTER_PLANNING_PLANNING.format(
            task=task,
            robot_name_list=robot_name_list,
            robot_description=robot_description,
            robot_position_info=robot_position_info,
            robot_tools_info=robot_tools_info,
            recep_name_list=recep_name_list,
            scene_object_info=scene_object_info,
            previous_experience=previous_experience,
        )
    
    def make_plan(self, task: str):
        """
        Generate a plan for the given task using the planning model.
        
        Args:
            task: The task description to be planned
            
        Returns:
            Parsed response from the planning model, or None if an error occurred
        """
        prompt = self.generate_prompt(task)
        logger.debug("[Planner] Generated prompt: %s", prompt)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        logger.info("[Planner] Sending request to model, waiting for response...")
        ret, response = self.model.forward(messages)
        logger.info("[Planner] Received response from model")
        if ret != 0:
            logger.error("[Planner] Error occurred while getting response from model: %s", response)
            return None
        logger.info("[Planner] The whole plan: %s", response)
        response = parse_response(response)
        return response


if __name__ == '__main__':
    """
    Main execution block for testing the PlannerAgent functionality.
    """
    # Load configuration and initialize Redis client
    config = Config.load_config("./config/planner_agent_config.yaml")
    redis_client = RedisClient(
        host=config['redis']['HOST'], 
        port=config['redis']['PORT'], 
        db=config['redis']['DB'], 
        password=config['redis']['PASSWORD'],
        robot_agent=False
        )
    
    # Initialize PlannerAgent
    planner = PlannerAgent(config, redis_client)
    
    # Log information about idle robots and their properties
    logger.info("[Planner] Idle robots: %s", planner.get_idle_robots())
    logger.info("[Planner] Robot 1 properties: %s", planner.get_robot_properties('robot_1'))
    logger.info("[Planner] Robot 2 properties: %s", planner.get_robot_properties('robot_2'))
    logger.info("[Planner] Online items: %s", planner.redis_client.get_online_items())
    
    # Example task planning (commented out)
    # print(planner.make_plan("Take basket to kitchenTable, and put apple and knife into basket, and then take them back to customTable")['subtask_list'])
    
    # Plan a sample task and log the result
    logger.info("[Planner] Plan result: %s", planner.make_plan('Please transfer Cargo 1 to the unloading area.'))

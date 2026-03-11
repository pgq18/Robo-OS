from utils.utils import Config, parse_response
from utils.redis_client import RedisClient
from master_memory import MasterMemory
from planner import PlannerAgent
from task_allocater import TaskAllocater
from utils.model import SupervisorModel
from utils.supervisor_prompt import TASK_ANALYSIS, EXCEPTION_ANALYSIS_AND_SUMMARY, ROBOT_POSITION_INFO_TEMPLATE, ROBOT_TOOLS_INFO_TEMPLATE, SCENE_OBJECTS_INFO_TEMPLATE
from utils.logger import get_logger
import threading
import time
import queue

# Get logger instance for the Supervisor module
logger = get_logger(__name__)

class Supervisor:
    """
    Global supervisor module.
    Responsible for monitoring system health, handling exceptions, and interacting with users.
    """
    
    def __init__(self, config, redis_client: RedisClient, planner: PlannerAgent):
        """
        Initialize the Supervisor with configuration, Redis client, and Planner agent.
        
        Args:
            config: Configuration dictionary containing model settings and other configurations
            redis_client: Redis client instance for accessing robot and scene data
            planner: PlannerAgent instance for generating task plans
        """
        # Directly use the passed configuration dictionary instead of reloading
        self.model = SupervisorModel(
            config['model']['Supervisor']['MODEL_NAME'], 
            config['model']['Supervisor']['CLOUD_API_KEY'], 
            config['model']['Supervisor']['CLOUD_SERVER']
            )
        self.redis_client = redis_client
        self.master_memory = MasterMemory(self.redis_client, config['milvus']['BASE_URL'])
        self.planner = planner
        self.exception_queue = queue.Queue()
        self.is_running = True
        self.task_analyzed = None

        # Start exception registration thread to listen for exceptions from other modules
        exception_register_thread = threading.Thread(target=self.redis_client.subscribe_exception, args=(self.register_exception,))
        exception_register_thread.daemon = True
        exception_register_thread.start()
        
        # Start exception handler thread to process exceptions in the main loop
        exception_handler_thread = threading.Thread(target=self.main_loop)
        exception_handler_thread.daemon = True
        exception_handler_thread.start()
        
        # Start success handler thread to listen for task completion messages
        success_handler_thread = threading.Thread(target=self.redis_client.subscribe_all_tasks_completed, args=(self._success_handler,))
        success_handler_thread.daemon = True
        success_handler_thread.start()
        
        logger.info("Supervisor initialized.")

    def _success_handler(self, msg):
        """
        Handle task completion messages.
        
        Args:
            msg: Message containing task completion status information
        """
        logger.info(f"[Supervisor] Received task completion message: {msg}")
        status = self.all_tasks_end(msg)

    def register_exception(self, msg):
        """
        Register an exception or failure reported by any module.
        
        Args:
            msg: Exception message to be registered
        """
        logger.critical(f"[Supervisor] Received an exception report: {msg}")
        self.exception_queue.put(msg)

    def all_tasks_end(self, msg):
        """
        Handle the completion of all tasks, whether successful or failed.
        
        Args:
            msg: Message containing task completion status information
            
        Returns:
            bool: True if tasks completed successfully, False otherwise
        """
        data = msg['data']
        logger.info(f"[Supervisor] All tasks ended with status: {data['status']}")
        if data['status'] == 'success':
            logger.info("[Supervisor] Task completed successfully, reporting to user")
            self.report_to_user(self.master_memory.get_all_summaries())
            return True
        else:
            logger.info("[Supervisor] Task failed, concluding experience and reporting to user")
            response_json = self.conclude_experience(self.master_memory.get_all_summaries())
            print("-------------------------------------------------------------")
            print(response_json['improvement_suggestions'])
            self.master_memory.insert_experience(response_json['improvement_suggestions'])
            self.report_to_user(response_json['overall_summary'])
            return False

    def conclude_experience(self, record):
        """
        Analyze task execution experience and generate improvement suggestions.
        
        Args:
            record: Task execution record/history
            
        Returns:
            dict: Parsed response containing improvement suggestions and overall summary
        """
        logger.debug(f"[Supervisor] Concluding experience based on record: {record}")
        task_history = record
        if len(record) > 1:
            exception_description = record[:-1]
        else:
            exception_description = record
        # exception_description = record[-1]
        prompt = EXCEPTION_ANALYSIS_AND_SUMMARY.format(
            task_history = task_history,
            exception_description = exception_description
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        ret, response = self.model.forward(messages)
        if not ret:
            logger.error(f"[Supervisor] Failed to parse response: {response}")
            return None
        response_json = parse_response(response)
        logger.debug(f"[Supervisor] Experience conclusion result: {response_json}")
        return response_json

    def analyze_task(self, request):
        """
        Analyze a task request to determine its feasibility and execution requirements.
        
        Args:
            request: Task request to be analyzed
            
        Returns:
            dict: Parsed response containing task analysis results
        """
        logger.info(f"[Supervisor] Analyzing task request: {request}")
        robot_name_list = self.master_memory.get_idle_robots()
        logger.debug(f"[Supervisor] Found idle robots: {robot_name_list}")
        
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
        logger.debug(f"[Supervisor] Found online items: {recep_name_list}")
        
        scene_object_info = [
            SCENE_OBJECTS_INFO_TEMPLATE.format(
                recep_name=recep_name,
                object_list=self.master_memory.get_item_property(recep_name, "recep_object")
            )
            for recep_name in recep_name_list
        ]
        prompt = TASK_ANALYSIS.format(
            task = request,
            robot_name_list=robot_name_list,
            robot_description = robot_description,
            robot_position_info = robot_position_info,
            robot_tools_info = robot_tools_info,
            scene_object_info = scene_object_info
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        logger.debug("[Supervisor] Sending task analysis request to model")
        ret, response = self.model.forward(messages)
        if not ret:
            logger.error(f"[Supervisor] Model forward failed with return code: {ret}, response: {response}")
            raise Exception(f"Model forward failed with return code: {ret}, response: {response}")
        response_json = parse_response(response)
        logger.debug(f"[Supervisor] Task analysis result: {response_json}")
        return response_json

    def main_loop(self):
        """
        Main loop of the supervisor to process exceptions.
        Continuously monitors the exception queue and handles different types of exceptions.
        """
        logger.info("[Supervisor] Monitor loop started.")
        while self.is_running:
            if not self.exception_queue.empty():
                msg = self.exception_queue.get()
                role = msg['role']
                data = msg['data']
                logger.info(f"[Supervisor] Processing exception from {role}: {data}")
                if role == 'planner':
                    logger.info("[Supervisor] Handling planner exception, requesting replan")
                    self.report_to_user(f"Planner failed to make a plan: {data['message']}. Now, trying to re-plan.")
                    self._request_replanning(f"{data['message']}")
                elif role == 'task_allocater':
                    logger.info("[Supervisor] Handling task allocator exception")
                    self.all_tasks_end(msg)
                    self.report_to_user(f"Exception occurred when executing task: {data['message']}. Now, trying to execute the task again.")
                    self._request_replanning(f"{data['message']}")
                else:
                    # Other unknown errors
                    logger.warning(f"[Supervisor] Unhandled exception type. Reason: {msg}. For now, logging only.")

    def user_interface(self, request: str):
        """
        Handle user requests and coordinate task execution.
        
        Args:
            request: User task request
            
        Returns:
            tuple: (response_json, subtask_list) - Analysis results and list of subtasks
        """
        logger.info(f"[Supervisor] Received user request: {request}")
        response_json = self.analyze_task(request)
        feasible = response_json['feasible']
        need_execution = response_json['needs_execution']
        self.task_analyzed = response_json['task_analysis']
        logger.info(f"[Supervisor] Task analysis - Feasible: {feasible}, Needs execution: {need_execution}")
        
        if feasible and need_execution:
            logger.info("[Supervisor] Task is feasible and needs execution, creating plan")
            subtask_list = self.planner.make_plan(self.task_analyzed)['subtask_list']
            logger.info(f"[Supervisor] Publishing subtask list with {len(subtask_list)} tasks")
            self.redis_client.publish_subtask_list(subtask_list)
            self.report_to_user(self.task_analyzed)
            return response_json, subtask_list
        else:
            logger.info("[Supervisor] Task does not need execution or is not feasible")
            self.report_to_user(self.task_analyzed)
            return response_json, []

    def report_to_user(self, message):
        """
        Report final results or critical errors to the user.
        
        Args:
            message: Message to be reported to the user
        """
        print("\n" + "=" * 20 + " MESSAGE TO USER " + "=" * 20)
        print(message)
        print("=" * 57 + "\n")

    def _request_replanning(self, reason):
        """
        Request replanning from the Planner agent.
        
        Args:
            reason: Reason for requesting replanning
        """
        logger.info(f"[Supervisor] Requesting a replan from Planner. Reason: {reason}")
        subtask_list = self.planner.make_plan(self.task_analyzed)['subtask_list']
        logger.info(f"[Supervisor] Publishing subtask list with {len(subtask_list)} tasks")
        self.redis_client.publish_subtask_list(subtask_list)
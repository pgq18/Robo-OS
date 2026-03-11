from flask import Flask, request, jsonify
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger
from utils.utils import Config
from utils.redis_client import RedisClient
from planner import PlannerAgent
from task_allocater import TaskAllocater
from supervisor import Supervisor
from multiprocessing import Process

app = Flask(__name__)
logger = get_logger(__name__)

# 全局变量存储planner_agent实例
planner_agent:PlannerAgent = None
task_allocater:TaskAllocater = None
supervisor:Supervisor = None

def initialize_system():
    """
    初始化系统组件
    """
    global planner_agent
    global task_allocater
    global supervisor
    
    try:
        # 加载配置
        config = Config.load_config("./config/main_config.yaml")
        
        # 初始化Redis客户端
        redis_client = RedisClient(
            host=config['redis']['HOST'], 
            port=config['redis']['PORT'], 
            db=config['redis']['DB'], 
            password=config['redis']['PASSWORD'],
            robot_agent=False
        )
        
        # 初始化PlannerAgent
        planner_agent = PlannerAgent(config, redis_client)
        planner_agent.init_items("./config/scene_profile.yaml")
        # 初始化TaskAllocater
        task_allocater = TaskAllocater("./config/main_config.yaml")
        # 初始化Supervisor
        supervisor = Supervisor(config, redis_client, planner_agent)
        
        logger.info("[Flask Server] System initialized successfully")
        return True
    except Exception as e:
        logger.error("[Flask Server] Failed to initialize system: %s", str(e))
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """
    健康检查端点
    """
    return jsonify({
        "status": "healthy",
        "message": "Flask server is running"
    })

@app.route('/execute_task', methods=['POST'])
def execute_task():
    """
    执行任务端点
    接收任务指令并处理
    """
    global planner_agent
    global task_allocater
    global supervisor
    
    if not planner_agent:
        return jsonify({
            "status": "error",
            "message": "System not initialized"
        }), 500
    
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data provided"
            }), 400
            
        task = data.get('task')
        if not task:
            return jsonify({
                "status": "error",
                "message": "No task provided"
            }), 400
        
        logger.info("[Flask Server] Received task: %s", task)
        
        # 使用PlannerAgent处理任务
        response_json, subtask_list = supervisor.user_interface(task)
        
        if subtask_list != []:
            logger.info("[Flask Server] Task processed successfully")
            return jsonify({
                "status": "success",
                "message": "Task processed successfully",
                "result": response_json['task_analysis']
            })
        elif subtask_list == []:
            logger.info("[Flask Server] Task processed successfully")
            return jsonify({
                "status": "success",
                "message": "Task processed successfully",
                "result": response_json['task_analysis']
            })
        else:
            logger.error("[Flask Server] Failed to process task")
            return jsonify({
                "status": "error",
                "message": "Failed to process task"
            }), 500
            
    except Exception as e:
        logger.error("[Flask Server] Error processing task: %s", str(e))
        return jsonify({
            "status": "error",
            "message": f"Error processing task: {str(e)}"
        }), 500

@app.route('/robots/status', methods=['GET'])
def get_robots_status():
    """
    获取机器人状态端点
    """
    global planner_agent
    global task_allocater
    global supervisor
    
    if not planner_agent:
        return jsonify({
            "status": "error",
            "message": "System not initialized"
        }), 500
    
    try:
        # 获取空闲机器人列表
        idle_robots = planner_agent.get_idle_robots()
        
        # 获取每个机器人的属性
        robots_info = {}
        for robot_name in idle_robots:
            robots_info[robot_name] = planner_agent.get_robot_properties(robot_name)
        
        logger.info("[Flask Server] Retrieved robots status")
        return jsonify({
            "status": "success",
            "idle_robots": idle_robots,
            "robots_info": robots_info
        })
        
    except Exception as e:
        logger.error("[Flask Server] Error getting robots status: %s", str(e))
        return jsonify({
            "status": "error",
            "message": f"Error getting robots status: {str(e)}"
        }), 500

@app.route('/robots/<robot_name>/properties', methods=['GET'])
def get_robot_properties(robot_name):
    """
    获取特定机器人属性端点
    """
    global planner_agent
    global task_allocater
    global supervisor
    
    if not planner_agent:
        return jsonify({
            "status": "error",
            "message": "System not initialized"
        }), 500
    
    try:
        properties = planner_agent.get_robot_properties(robot_name)
        
        if properties:
            logger.info("[Flask Server] Retrieved properties for robot: %s", robot_name)
            return jsonify({
                "status": "success",
                "robot_name": robot_name,
                "properties": properties
            })
        else:
            logger.warning("[Flask Server] Robot not found: %s", robot_name)
            return jsonify({
                "status": "error",
                "message": f"Robot {robot_name} not found"
            }), 404
            
    except Exception as e:
        logger.error("[Flask Server] Error getting robot properties: %s", str(e))
        return jsonify({
            "status": "error",
            "message": f"Error getting robot properties: {str(e)}"
        }), 500

@app.route('/items', methods=['GET'])
def get_all_items():
    """
    获取所有物品信息端点
    """
    global planner_agent
    global task_allocater
    global supervisor
    
    if not planner_agent:
        return jsonify({
            "status": "error",
            "message": "System not initialized"
        }), 500
    
    try:
        # 获取在线物品列表
        online_items = planner_agent.master_memory.get_online_items()
        
        # 获取每个物品的属性
        items_info = {}
        for item_name in online_items:
            items_info[item_name] = planner_agent.master_memory.get_item_property(item_name, "recep_object")
        
        logger.info("[Flask Server] Retrieved all items information")
        return jsonify({
            "status": "success",
            "items": items_info
        })
        
    except Exception as e:
        logger.error("[Flask Server] Error getting items information: %s", str(e))
        return jsonify({
            "status": "error",
            "message": f"Error getting items information: {str(e)}"
        }), 500

if __name__ == '__main__':
    # 初始化系统
    if not initialize_system():
        logger.error("[Flask Server] Failed to start server due to initialization error")
        sys.exit(1)
    
    # 启动Flask服务
    app.run(host='0.0.0.0', port=5000, debug=False)
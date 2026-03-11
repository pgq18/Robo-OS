message = {
    'type': 'message', 
    'pattern': None, 
    'channel': 'robot_registration', 
    'data': '{"robot_name": "robot_1", "robot_type": "realman_single", "robot_tool": [{"function": {"name": "navigate_to_target", "description": "Navigate to target\\n    Args:\\n        target: String, Represents the navigation destination.\\n    "}, "input_schema": {"properties": {"target": {"title": "Target", "type": "string"}}, "required": ["target"], "title": "navigate_to_targetArguments", "type": "object"}, "output_type": "any"}, {"function": {"name": "grasp_object", "description": "Grasp the object for bring\\n    Args:\\n        object: String, Represents which to grasp.\\n    "}, "input_schema": {"properties": {"object": {"title": "Object", "type": "string"}}, "required": ["object"], "title": "grasp_objectArguments", "type": "object"}, "output_type": "any"}, {"function": {"name": "place_to_affordance", "description": "Place the grasped object in affordance\\n    Args:\\n        affordance: String, Represents where the object to place.\\n    "}, "input_schema": {"properties": {"affordance": {"title": "Affordance", "type": "string"}}, "required": ["affordance"], "title": "place_to_affordanceArguments", "type": "object"}, "output_type": "any"}], "current_position": "initialPosition", "navigate_position": ["initialPosition", "customTable", "kitchenTable", "servingTable"], "robot_state": "idle", "timestamp": 1755590646}'}
message = {
    "robot_name": "robot_1", 
    "robot_type": "realman_single", 
    "robot_tool": [
        {
            "function": {
                "name": "navigate_to_target", 
                "description": "Navigate to target"
                "Args: target: String, Represents the navigation destination."
                }, 
            "input_schema": {
                "properties": {
                    "target": {
                        "title": "Target", 
                        "type": "string"
                        }
                    }, 
                "required": [
                    "target"
                    ], 
                "title": "navigate_to_targetArguments", 
                "type": "object"
                }, 
            "output_type": "any"
            }, 
        {
            "function": {
                "name": "grasp_object", 
                "description": "Grasp the object for bring"
                "Args: object: String, Represents which to grasp."
                }, 
            "input_schema": {
                "properties": {
                    "object": {
                        "title": "Object", 
                        "type": "string"
                        }
                    }, 
                "required": [
                    "object"
                    ], 
                "title": "grasp_objectArguments", 
                "type": "object"
                }, 
            "output_type": "any"
            }, 
        {
            "function": {
                "name": "place_to_affordance", 
                "description": "Place the grasped object in affordance"
                "Args: affordance: String, Represents where the object to place."
                }, 
            "input_schema": {
                "properties": {
                    "affordance": {
                        "title": "Affordance", 
                        "type": "string"
                        }
                    }, 
                "required": [
                    "affordance"
                    ], 
                "title": "place_to_affordanceArguments", 
                "type": "object"
                }, 
            "output_type": "any"
            }
        ], 
        "current_position": "initialPosition", 
        "navigate_position": [
            "initialPosition", 
            "customTable", 
            "kitchenTable", 
            "servingTable"
            ], 
        "robot_state": "idle", 
        "timestamp": 1755590646
    }
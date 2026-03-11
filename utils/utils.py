import yaml
import json

def convert_yaml_to_json(yaml_path: str):
    """
        Read the YAML file and return the data as a Dictionary.

    Args:
        robot_profile_path (str): Path to the robot profile YAML file.

    Returns:
        Dict: Data from the YAML files.

    """
    with open(yaml_path, "r", encoding="utf-8") as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)

    if "robot_tool" in yaml_data and isinstance(yaml_data["robot_tool"], dict):
        yaml_data["robot_tool"] = [
            {"tool_name": name, "class": f"tools.robotic_tools.{cfg['class']}"}
            for name, cfg in yaml_data["robot_tool"].items()
        ]
    return yaml_data

class Config:
    @classmethod
    def load_config(cls, config_path):
        """Initialize configuration"""
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    
def parse_response(response: str):
    response = response.split("```json")[-1]
    response = response.split("```")[0]
    return json.loads(response)
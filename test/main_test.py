from planner import PlannerAgent

def main():
    planner = PlannerAgent("./config/planner_agent_config.yaml")
    print(planner.get_online_robots())
    print(planner.get_robot_properties("robot_1"))
    print(planner.get_robot_properties("robot_2"))
    print(planner.redis_client.get_online_items())
    # print(planner.make_plan("Take basket to kitchenTable, and put apple and knife into basket, and then take them back to customTable")['subtask_list'])
    print(planner.make_plan("Please transfer Cargo 1 to the unloading area."))
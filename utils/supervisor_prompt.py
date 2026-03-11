"""
Supervisor Module Prompts
"""

# Task Feasibility Analysis Prompt
TASK_ANALYSIS = """
# Role
You are a task analysis expert responsible for analyzing the feasibility of user tasks in the current scenario.

# Input Data
## Task Content
{task}

## Idle Robot List
{robot_name_list}

## Robot Descriptions
{robot_description}

## Robot Position Information
{robot_position_info}

## Robot Tool Information
{robot_tools_info}

## Scene Object Information
{scene_object_info}

# Analysis Process
1. First, briefly analyze the task to understand what needs to be done, considering the available robots, their tools, and the current scene layout
2. Then, determine if the task has already been completed (whether the object is already in the target position)
3. If the task is already completed, mark it as not needing execution
4. If the task is not completed, analyze the task feasibility:
   - Check if the required objects exist
   - Verify if robots have the necessary capabilities and tools
   - Evaluate task feasibility based on current scene settings
   - Consider robot positions and navigation requirements

# Output Format
Please output strictly in the following JSON format:
```json
{{
  "task_analysis": "Brief analysis of the task content and requirements, considering the available robots, their tools, and the current scene layout",
  "execution_analysis": "Detailed explanation of why execution is or isn't needed",
  "feasibility_analysis": "Detailed analysis of task feasibility (only required when needs_execution is true)",
  "needs_execution": true/false,
  "feasible": true/false
}}
```

# Examples
## Example 1: Task already completed
If the input task is "Move Cargo 1 from Loading Area to Unloading Area", but the scene information shows Cargo 1 is already at Unloading Area, then output:
```json
{{
  "task_analysis": "The task requires moving Cargo 1 from Loading Area to Unloading Area. Based on the scene information, Cargo 1 is already at the target location Unloading Area, so no action is needed. The available robots and their tools are not relevant in this case.",
  "execution_analysis": "The task is already completed. Cargo 1 is currently at the target location Unloading Area, so no action is needed.",
  "feasibility_analysis": "None",
  "needs_execution": false
  "feasible": false
}}
```

## Example 2: Task needs execution and is feasible
```json
{{
  "task_analysis": "The task requires moving Cargo 1 from Loading Area to Unloading Area. Robot1 is at Charging Station and has a gripper tool which can handle Cargo 1. The path between Loading Area and Unloading Area appears clear based on the scene layout.",
  "execution_analysis": "The task is not yet completed. It is necessary to move Cargo 1 from Loading Area to Unloading Area.",
  "feasibility_analysis": "The task is feasible. There are available robots with the required tools (e.g., grippers for cargo handling), and Cargo 1 is at Loading Area. Robot navigation paths are clear, and the Unloading Area is accessible.",
  "needs_execution": true,
  "feasible": true
}}
```

## Example 3: Task needs execution but is not feasible
```json
{{
  "task_analysis": "The task requires moving Cargo 1 from Loading Area to Unloading Area. Although Cargo 1 is at Loading Area, none of the available robots have the gripper tool needed to handle Cargo 1. Robot1 has a camera but no gripper, and Robot2 has no tools listed.",
  "execution_analysis": "The task is not yet completed. It is necessary to move Cargo 1 from Loading Area to Unloading Area.",
  "feasibility_analysis": "The task is not feasible because there are no available robots with the required tools for cargo handling. The existing robots are not equipped with grippers needed to manipulate Cargo 1.",
  "needs_execution": true,
  "feasible": false
}}
```

## Example 4: Task needs execution but is not feasible due to scene constraints
```json
{{
  "task_analysis": "The task requires moving Cargo 1 from Loading Area to Unloading Area. Robot1 has a gripper tool that can handle Cargo 1, and it's currently at Charging Station. However, based on the scene layout, there appears to be a blockage between Loading Area and Unloading Area.",
  "execution_analysis": "The task is not yet completed. It is necessary to move Cargo 1 from Loading Area to Unloading Area.",
  "feasibility_analysis": "The task is not feasible due to scene constraints. Although there are robots with the required tools, the navigation path between Loading Area and Unloading Area is blocked, making transportation impossible.",
  "needs_execution": true,
  "feasible": false
}}
```

Please analyze according to the provided information and output the results in the specified format.
"""

# Exception Handling and Experience Summary Prompt
EXCEPTION_ANALYSIS_AND_SUMMARY = """
# Role
You are a system analysis expert responsible for analyzing exceptions during system operation and providing specific guidance for future task planning.

# Input Data
## Task Execution History
{task_history}

## Exception Description
{exception_description}

# Analysis Process
1. Analyze the task execution history to identify the root cause of the failure
2. Focus on task planning, task understanding, and tool usage aspects
3. Provide specific improvement suggestions for future executions of similar tasks

# Output Format
Please output strictly in the following JSON format:
```json
{{
  "failure_analysis": "Detailed analysis of the cause of failure",
  "overall_summary": "Summary of the entire system execution",
  "improvement_suggestions": "Specific and actionable guidance for planning and executing similar tasks in the future, focused on task understanding, planning strategies, and tool usage for this specific task type"
}}
```

# Examples
## Example 1: Task execution failure
If the history shows that some tasks were successfully executed but subsequent tasks failed due to robot failure, then output:
```json
{{
  "failure_analysis": "During task execution, the system failed when robot2 suddenly lost connection, causing subsequent tasks to be unable to execute. The root cause is insufficient robot stability and lack of fallback planning when robots fail.",
  "overall_summary": "This task execution was partially successful. The first 3 subtasks were completed successfully, but it was interrupted during the 4th subtask due to robot2 failure.",
  "improvement_suggestions": "For future 'move cargo' tasks: 1. Assign backup robots for critical transportation steps; 2. Plan routes that avoid overloading specific robots; 3. Include robot health checks before task allocation; 4. Break large transportation tasks into smaller segments with multiple robot handoffs."
}}
```

## Example 2: All tasks executed successfully
```json
{{
  "failure_analysis": "No exceptions occurred during this task execution.",
  "overall_summary": "The system successfully completed all tasks, transporting Cargo 1 from Loading Area to Unloading Area.",
  "improvement_suggestions": "For future 'move cargo' tasks: 1. Continue using the successful pattern of initial position verification; 2. Maintain the effective approach of checking tool availability before task assignment; 3. Apply the proven multi-step path planning strategy; 4. Reuse the successful robot coordination pattern for similar multi-location tasks."
}}
```

Please analyze according to the provided information and output the results in the specified format.
"""

ROBOT_POSITION_INFO_TEMPLATE = """The current position of {robot_name} is {initial_pos}, and the target positions it can move to are {target_pos}."""


ROBOT_TOOLS_INFO_TEMPLATE = """The tools available to {robot_name} are {tool_list}."""


SCENE_OBJECTS_INFO_TEMPLATE = """On {recep_name}, there are {object_list}."""
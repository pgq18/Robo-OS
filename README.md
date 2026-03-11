# Robo-OS

A multi-robot collaborative operating system powered by Large Language Models (LLMs), enabling intelligent task planning and coordinated multi-robot operations in port logistics scenarios.

## Features

- **Intelligent Task Planning**: Automatically decomposes complex tasks into executable subtask sequences using LLM
- **Multi-Robot Collaboration**: Supports coordination between robot arms (loading) and robot dogs (transporting)
- **Memory System**: Integrates Redis (real-time state) and Milvus (long-term experience) for experience learning and retrieval
- **Exception Handling**: Automatic re-planning when task execution fails
- **Visual Simulation**: Pygame-based port logistics scenario simulator
- **RESTful API**: Standardized task execution interface via Flask

## System Architecture

```
User Request
    ↓
Flask Server (API Interface)
    ↓
Supervisor (Task Analysis) ←→ MasterMemory (Read State)
    ↓ Feasible & Needs Execution
Planner (Task Planning) ←→ MasterMemory (Retrieve Experience)
    ↓ Subtask List
TaskAllocater (Task Allocation)
    ↓ Publish Tasks
    ├──→ robot_arm (Load Cargo)
    └──→ robot_dog (Navigate + Unload)
         ↓ Return Results
TaskAllocater (Collect Results)
    ↓ All Tasks Completed
Supervisor (Experience Summary)
    ↓
MasterMemory (Store Experience)
```

## Directory Structure

```
Robo-OS/
├── config/                          # Configuration files
│   ├── main_config.yaml            # Main config (Model, Redis, Milvus)
│   ├── scene_profile.yaml          # Scene config (Docks, Cargo locations)
│   └── mem_config.yaml             # Memory config
├── robot_arm/                       # Robot arm module
│   ├── robot_agent.py              # Robot arm Agent implementation
│   └── robot_agent_config.yaml     # Robot arm configuration
├── robot_dog/                       # Robot dog module
│   ├── robot_agent.py              # Robot dog Agent implementation
│   └── robot_agent_config.yaml     # Robot dog configuration
├── utils/                           # Utility modules
│   ├── logger.py                   # Logger manager
│   ├── model.py                    # LLM model wrapper
│   ├── milvus_client.py           # Milvus vector DB client
│   ├── milvus_server.py           # Milvus server
│   ├── redis_client.py            # Redis client
│   ├── utils.py                   # Utility functions
│   ├── planner_prompt.py          # Planner prompt templates
│   ├── supervisor_prompt.py       # Supervisor prompt templates
│   └── robot_prompt.py            # Robot prompt templates
├── test/                            # Test files
├── flask_server.py                  # Flask web server
├── supervisor.py                    # Global supervisor module
├── planner.py                       # Task planner module
├── task_allocater.py                # Task allocator
├── master_memory.py                 # Master memory module
├── port_move_demo_simulator.py      # Pygame port logistics simulator
├── test_flask_server.py             # Flask API test client
├── requirements.txt                 # Python dependencies
└── README.md
```

## Requirements

- Python 3.10+
- Redis
- Milvus (or use the built-in simple server)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/Robo-OS.git
cd Robo-OS

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### 1. Model Configuration (`config/main_config.yaml`)

Configure your Qwen API key and server URL:

```yaml
model:
  Planner:
    MODEL_NAME: "qwen-plus"
    CLOUD_API_KEY: "your-api-key"
    CLOUD_SERVER: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  Supervisor:
    MODEL_NAME: "qwen-plus"
    CLOUD_API_KEY: "your-api-key"
    CLOUD_SERVER: "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

### 2. Scene Configuration (`config/scene_profile.yaml`)

Configure dock and exit locations for the port scenario:

```yaml
scene:
  - recep_name: "Exit Bay A"
    location: [633, 63]
    recep_object: []
  - recep_name: "Dock1"
    location: [169, 213]
    ...
```

### 3. Robot Configuration (`robot_dog/robot_agent_config.yaml`, `robot_arm/robot_agent_config.yaml`)

Configure robot types, tools, and capabilities.

## Quick Start

Start the services in the following order:

```bash
# 1. Start Redis server
redis-server --port 5555

# 2. Start Milvus server (vector database)
python utils/milvus_server.py

# 3. Start Flask server (main service)
python flask_server.py

# 4. Start simulator (optional, for visualization)
python port_move_demo_simulator.py

# 5. Run test client
python test_flask_server.py
```

## API Reference

### Health Check

```
GET /health
```

### Execute Task

```
POST /execute_task
Content-Type: application/json

{
    "task": "Move all cargos to the corresponding Exit Bay"
}
```

### Get Robot Status

```
GET /robots/status
```

### Get Robot Properties

```
GET /robots/<robot_name>/properties
```

### Get Scene Items

```
GET /items
```

## Robot Types

| Type | Function | Tools |
|------|----------|-------|
| robot_dog | Mobile transport | `navigate_to_where`, `unload_object` |
| robot_arm | Stationary loading | `load` |

## Workflow Example

1. User sends task: "Move all cargos to the corresponding Exit Bay"
2. Supervisor analyzes task feasibility, checks robot and item status
3. Planner decomposes task into subtask sequences
4. TaskAllocater distributes tasks to robots in order
5. robot_arm loads cargo onto robot_dog
6. robot_dog navigates to exit and unloads
7. Supervisor summarizes experience and stores to Milvus

## Simulator Controls

| Key | Function |
|-----|----------|
| Arrow keys | Move selected vehicle |
| Tab | Switch selected object |
| 1-4 | Select specific vehicle |
| Space/A/B | Load cargo |
| D | Unload cargo |
| Right mouse click | Set auto-navigation target |

## Tech Stack

- **LLM**: Qwen (qwen-plus, qwen3-235b)
- **Message Queue**: Redis Pub/Sub
- **Vector Database**: Milvus
- **Web Framework**: Flask
- **Simulation**: Pygame

## License

MIT License

import ray
import time
from agent_manager import AgentManager

ray.init(address="auto")

IMAGE = "your-agent-image"
BASE_PORT = 5000
THRESHOLD = 30.0
CHECK_INTERVAL = 10  # seconds

# Deploy one AgentManager per VM with resource labels
managers = {
    "vm1": AgentManager.options(resources={"vm1": 1}).remote(IMAGE, "vm1"),
    "vm2": AgentManager.options(resources={"vm2": 1}).remote(IMAGE, "vm2"),
    "vm3": AgentManager.options(resources={"vm3": 1}).remote(IMAGE, "vm3"),
}

# Track used ports per VM
ports = {"vm1": [BASE_PORT], "vm2": [BASE_PORT], "vm3": [BASE_PORT]}

# Start one agent on each VM
for vm, manager in managers.items():
    ray.get(manager.start_agent.remote(BASE_PORT))

# Autoscale loop
while True:
    time.sleep(CHECK_INTERVAL)
    for vm, manager in managers.items():
        agent_names = ray.get(manager.get_agents.remote())
        should_scale = False

        for name in agent_names:
            cpu = ray.get(manager.get_container_cpu_usage.remote(name))
            print(f"{vm} → {name} CPU: {cpu:.2f}%")
            if cpu > THRESHOLD:
                should_scale = True

        if should_scale:
            new_port = max(ports[vm]) + 1
            ray.get(manager.start_agent.remote(new_port))
            ports[vm].append(new_port)
            print(f"🆕 New agent deployed on {vm} port {new_port}")

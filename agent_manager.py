import ray
import subprocess

@ray.remote
class AgentManager:
    def __init__(self, image_name, node_label):
        self.image_name = image_name
        self.node_label = node_label
        self.agent_count = 0
        self.agent_names = []

    def start_agent(self, port):
        name = f"{self.node_label}_agent{self.agent_count}"
        cmd = f"docker run -d --name {name} -p {port}:{port} {self.image_name}"
        subprocess.run(cmd, shell=True)
        self.agent_names.append(name)
        self.agent_count += 1
        return f"Started {name} on {self.node_label} at port {port}"

    def get_container_cpu_usage(self, name):
        cmd = f"docker stats {name} --no-stream --format '{{{{.CPUPerc}}}}'"
        result = subprocess.check_output(cmd, shell=True).decode().strip()
        if "%" in result:
            return float(result.replace("%", "").strip())
        return 0.0

    def get_agents(self):
        return self.agent_names

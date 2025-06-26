import requests

def generate_actions(expected_state, actual_state):
    actions = []

    for machine, expected_agents in expected_state.items():
        actual_agents = actual_state.get(machine, {})

        # Check for agents to deploy
        for agent, expected_count in expected_agents.items():
            actual_count = actual_agents.get(f"{agent}_instances", 0)
            if expected_count > actual_count:
                for _ in range(expected_count - actual_count):
                    actions.append(f"Deploy {agent} on {machine}")

        # Check for agents to remove
        for agent_key, actual_count in actual_agents.items():
            agent_name = agent_key.replace('_instances', '')
            expected_count = expected_agents.get(agent_name, 0)
            if actual_count > expected_count:
                for _ in range(actual_count - expected_count):
                    actions.append(f"Remove {agent_name} from {machine}")

    return actions

# Example usage
if __name__ == "__main__":
    expected_state = {
        '192.168.122.203': {'agent1': 1},
        '192.168.122.45': {'agent1': 1}
    }

    actual_state = {
        '192.168.122.45': {'agent1_instances': 1, 'agent2_instances': 0}
    }

    actions = generate_actions(expected_state, actual_state)
    print(actions)

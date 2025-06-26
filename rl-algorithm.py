from flask import Flask, request, jsonify
import random
import json
import pickle
import os
import time
import requests
from itertools import permutations

app = Flask(__name__)

# === Q-Learning Parameters ===
ALPHA = 0.1   # Learning rate
GAMMA = 0.9   # Discount factor
EPSILON = 0.1 # Exploration rate

# === Prometheus Configuration ===
PROMETHEUS_URL = "http://localhost:9090"  # Update this to your Prometheus host

# === Q-table Persistence ===
Q_TABLE_PATH = "q_table.pkl"

if os.path.exists(Q_TABLE_PATH):
    with open(Q_TABLE_PATH, 'rb') as f:
        q_table = pickle.load(f)
else:
    q_table = {}

# === Encode current state ===
def encode_state(agent_counts):
    return (agent_counts.get('agent1', 0), agent_counts.get('agent2', 0))

# === Generate all possible agent placement actions ===
def generate_possible_actions(agent_counts, vm_names):
    agents = [agent for agent, count in agent_counts.items() for _ in range(count)]
    possible_actions = []

    for assignment in permutations(vm_names * len(agents), len(agents)):
        strategy = {vm: [] for vm in vm_names}
        for agent, vm in zip(agents, assignment):
            strategy[vm].append(agent)
        possible_actions.append(strategy)

    return possible_actions

# === Choose best action using epsilon-greedy policy ===
def choose_best_action(state, actions, epsilon=EPSILON):
    if state not in q_table:
        q_table[state] = {}

    for action in actions:
        key = json.dumps(action, sort_keys=True)
        if key not in q_table[state]:
            q_table[state][key] = 0.0

    if random.random() < epsilon:
        return random.choice(actions)

    best_key = max(q_table[state], key=lambda k: q_table[state][k])
    return json.loads(best_key)

# === Update Q-table using Q-learning rule ===
def update_q_table(state, action, reward, alpha=ALPHA, gamma=GAMMA):
    action_key = json.dumps(action, sort_keys=True)

    if state not in q_table:
        q_table[state] = {}

    current_q = q_table[state].get(action_key, 0.0)
    max_future_q = max(q_table[state].values(), default=0.0)

    new_q = current_q + alpha * (reward + gamma * max_future_q - current_q)
    q_table[state][action_key] = new_q

    # Save Q-table to file
    with open(Q_TABLE_PATH, 'wb') as f:
        pickle.dump(q_table, f)

# === Fetch energy metrics from Prometheus ===
def fetch_energy_from_prometheus(vm_names):
    energy_data = {}
    for vm in vm_names:
        query = f'sum(rate(scaph_energy_consumption_joules{{host="{vm}"}}[1m]))'
        try:
            response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
            result = response.json()['data']['result']
            if result:
                energy = float(result[0]['value'][1])
            else:
                energy = 0.0
        except Exception:
            energy = 0.0
        energy_data[vm] = energy
    return energy_data

# === Flask API Endpoint ===
@app.route('/placement_strategy', methods=['GET'])
def placement_strategy():
    state_json = request.args.get('state')
    vms_json = request.args.get('available_vms')

    try:
        agent_counts = json.loads(state_json)
        vm_names = json.loads(vms_json)
    except (json.JSONDecodeError, TypeError) as e:
        return jsonify({'error': 'Invalid input JSON', 'details': str(e)}), 400

    state = encode_state(agent_counts)
    actions = generate_possible_actions(agent_counts, vm_names)
    chosen_action = choose_best_action(state, actions)

    # TODO: Deploy the chosen_action here using your system (Docker, Ray, etc.)
    print("Deploying agents to VMs:", chosen_action)

    # Wait to let Prometheus gather post-deployment energy usage
    time.sleep(10)

    energy_data = fetch_energy_from_prometheus(vm_names)
    total_energy = sum(energy_data.get(vm, 0.0) for vm in vm_names)
    reward = -total_energy  # lower energy => higher reward

    update_q_table(state, chosen_action, reward)

    return jsonify(chosen_action)

# === Run the App ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)

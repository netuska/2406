import pickle
import json
import random
import time
from flask import Flask, request, jsonify
import requests
import os
from itertools import permutations

ALPHA = 0.1
GAMMA = 0.9
EPSILON = 0.1
PROMETHEUS_URL = "http://localhost:9090"
Q_TABLE_PATH = 'q_table.pkl'

app = Flask(__name__)

# Load Q-table
if os.path.exists(Q_TABLE_PATH):
    with open(Q_TABLE_PATH, 'rb') as f:
        q_table = pickle.load(f)
else:
    q_table = {}

last_state = None
last_energy = None

def encode_state(agent_counts):
    return tuple(agent_counts.get(agent, 0) for agent in sorted(agent_counts.keys()))

def generate_possible_actions(agent_counts, vm_names):
    agents = []
    for agent, count in agent_counts.items():
        agents.extend([agent] * count)
    return list(permutations(vm_names * len(agents), len(agents)))

def choose_best_action(state, actions, epsilon=EPSILON):
    if random.random() < epsilon:
        return random.choice(actions)
    q_values = [q_table.get((state, action), 0.0) for action in actions]
    max_q = max(q_values)
    best_actions = [action for action, q in zip(actions, q_values) if q == max_q]
    return random.choice(best_actions)

def update_q_table(state, action, reward):
    current_q = q_table.get((state, action), 0.0)
    future_q = max([q_table.get((state, a), 0.0) for a in q_table if a[0] == state], default=0.0)
    new_q = current_q + ALPHA * (reward + GAMMA * future_q - current_q)
    q_table[(state, action)] = new_q
    with open(Q_TABLE_PATH, 'wb') as f:
        pickle.dump(q_table, f)

def fetch_energy_from_prometheus():
    query = 'scaph_host_energy_microjoules{job="scaphandre-qemu"}'
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
        result = response.json().get('data', {}).get('result', [])
        if result:
            return float(result[0]['value'][1])
    except Exception as e:
        print(f"Error fetching energy data: {e}")
    return 0.0

@app.route('/placement_strategy', methods=['GET'])
def placement_strategy():
    global last_state, last_energy

    try:
        agent_counts = json.loads(request.args.get('state'))
        vm_names = json.loads(request.args.get('available_vms'))
    except (json.JSONDecodeError, TypeError) as e:
        return jsonify({'error': 'Invalid input JSON', 'details': str(e)}), 400

    # Step 1: Encode state and generate actions
    state = encode_state(agent_counts)
    actions = generate_possible_actions(agent_counts, vm_names)
    chosen_action = choose_best_action(state, actions)
    current_energy = fetch_energy_from_prometheus()

    # Step 2: Build nested dictionary from action
    agent_list = []
    for agent, count in agent_counts.items():
        agent_list.extend([agent] * count)

    result = {}
    for agent, vm in zip(agent_list, chosen_action):
        if vm not in result:
            result[vm] = {}
        if agent not in result[vm]:
            result[vm][agent] = 0
        result[vm][agent] += 1

    # Step 3: Reward + Q-learning update
    if last_state is not None and last_energy is not None:
        energy_used = current_energy - last_energy
        reward = -energy_used
        update_q_table(last_state, chosen_action, reward)
        print(f"[Q-LEARNING] Updated Q-table with reward: {reward:.2f}")

    last_state = state
    last_energy = current_energy

    return jsonify(result)

@app.route('/q_table', methods=['GET'])
def get_q_table():
    readable_q = {
        f"{state} -> {action}": q for (state, action), q in q_table.items()
    }
    return jsonify(readable_q)

@app.route('/reset', methods=['POST'])
def reset_state():
    global last_state, last_energy
    last_state = None
    last_energy = None
    return jsonify({"message": "Last state and energy reset."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)

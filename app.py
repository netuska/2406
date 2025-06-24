from flask import Flask, render_template
import requests

app = Flask(__name__)
PROMETHEUS_URL = "http://localhost:9090"

@app.route('/')
def index():
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "agent_vm_info"}
        )
        data = response.json()
    except Exception as e:
        return f"Error fetching from Prometheus: {e}"

    vm_map = {}
    if data['status'] == 'success':
        for result in data['data']['result']:
            vm = result['metric'].get('vm', 'unknown')
            agent = result['metric'].get('agent', 'unknown')
            vm_map.setdefault(vm, []).append(agent)

    vm_map = dict(sorted(vm_map.items()))  # Sort by VM name
    return render_template('index.html', vm_map=vm_map)

# 🟢 This part is essential to start the Flask server!
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

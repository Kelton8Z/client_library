from flask import Flask, jsonify
import time
from threading import Lock

app = Flask(__name__)

class JobManager:
    def __init__(self, completion_time=5):
        self.start_time = time.time()
        self.completion_time = completion_time
        self.error_triggered = False
        self.lock = Lock()
    
    def get_status(self):
        with self.lock:
            elapsed_time = time.time() - self.start_time
            if self.error_triggered:
                return "error"
            elif elapsed_time >= self.completion_time:
                return "completed"
            return "pending"
    
    def trigger_error(self):
        with self.lock:
            self.error_triggered = True

job_manager = JobManager()

@app.route('/status')
def get_status():
    return jsonify({"result": job_manager.get_status()})

@app.route('/trigger_error')
def trigger_error():
    job_manager.trigger_error()
    return jsonify({"message": "Error triggered"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
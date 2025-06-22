import subprocess
from flask import Flask, jsonify
from flask_cors import CORS
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - API Server - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MOCK_DATA_SCRIPT = os.path.join(PROJECT_ROOT, 'mock_data.py')
KAFKA_PRODUCER_SCRIPT = os.path.join(PROJECT_ROOT, 'kafka_producer.py')
STORE_CODES_SCRIPT = os.path.join(PROJECT_ROOT, 'store_codes.py')

@app.route('/start-pipeline', methods=['GET'])
def start_pipeline():
    """
    Endpoint to trigger the data pipeline (mock data generation, Kafka production, SQLite storage).
    NOTE: ai_agents.py (Kafka consumer) should be running continuously in a separate terminal.
    """
    logger.info("Received request to start pipeline.")
    results = []

    try:
        # 1. Run mock_data.py
        logger.info(f"Running {MOCK_DATA_SCRIPT}...")
        mock_data_process = subprocess.run(
            ['python', MOCK_DATA_SCRIPT],
            capture_output=True, text=True, check=True, cwd=PROJECT_ROOT
        )
        results.append({"step": "mock_data", "status": "success", "output": mock_data_process.stdout.strip()})
        logger.info(f"mock_data.py output: {mock_data_process.stdout.strip()}")

        # 2. Run kafka_producer.py
        logger.info(f"Running {KAFKA_PRODUCER_SCRIPT}...")
        kafka_producer_process = subprocess.run(
            ['python', KAFKA_PRODUCER_SCRIPT],
            capture_output=True, text=True, check=True, cwd=PROJECT_ROOT
        )
        results.append({"step": "kafka_producer", "status": "success", "output": kafka_producer_process.stdout.strip()})
        logger.info(f"kafka_producer.py output: {kafka_producer_process.stdout.strip()}")

        # Give ai_agents.py (running separately) time to process and upload to S3
        logger.info("Waiting 10 seconds for AI agents to process data and upload to S3...")
        time.sleep(10)

        # 3. Run store_codes.py
        logger.info(f"Running {STORE_CODES_SCRIPT}...")
        store_codes_process = subprocess.run(
            ['python', STORE_CODES_SCRIPT],
            capture_output=True, text=True, check=True, cwd=PROJECT_ROOT
        )
        results.append({"step": "store_codes", "status": "success", "output": store_codes_process.stdout.strip()})
        logger.info(f"store_codes.py output: {store_codes_process.stdout.strip()}")

        return jsonify({"status": "success", "message": "Pipeline triggered successfully!", "details": results}), 200

    except subprocess.CalledProcessError as e:
        logger.error(f"Pipeline script failed: {e.cmd}. Error: {e.stderr}")
        results.append({"step": e.cmd[0], "status": "failed", "error": e.stderr.strip()})
        return jsonify({"status": "error", "message": "Pipeline execution failed.", "details": results}), 500
    except Exception as e:
        logger.error(f"An unexpected error occurred in pipeline trigger: {e}")
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}", "details": results}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "API server is running"}), 200

if __name__ == '__main__':
    logger.info("Starting Flask API server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)

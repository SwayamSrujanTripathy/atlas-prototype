ATLAS  - Product Authenticity System
ATLAS  is an advanced system designed to enhance product authenticity, monitor supply chain integrity, and analyze seller behavior in real-time. It leverages a modern, distributed architecture featuring Kafka for messaging, LocalStack for AWS service simulation, Python-based AI agents for analysis, and a React frontend for visualization.

🌟 Features
Mock Data Generation: Generates synthetic product data (including product details, images, reviews, pricing, and return counts).

Kafka-based Messaging: Utilizes Apache Kafka for robust and scalable asynchronous communication between system components.

AI-Powered Analysis Agents: Python agents consume product data from Kafka, perform various authenticity checks using AI models (e.g., product vision, pricing anomaly, return anomaly, review authenticity, seller behavior analysis).

LocalStack Integration: Simulates AWS S3 for storing processed analysis results, allowing for local development without actual AWS cloud costs.

Interactive React Frontend: A responsive web interface displays analyzed product data in real-time, highlighting potential fake products or suspicious activities.

Search engine optimizer: Implements hybrid search using Elasticsearch and sentence embeddings via FAISS. Recommends contextually relevant ads based on user intent and category similarity.

🚀 Architecture Overview
The system consists of several interconnected components:

docker-compose.yaml: Orchestrates the core infrastructure services:

Zookeeper: Manages Kafka cluster state.

Kafka: The messaging queue for data ingestion and processed results.

LocalStack: Provides local AWS S3 emulation for storing analysis outputs.

api-backend (Flask App): A simple Flask API that can trigger the data generation pipeline (though in your current setup, you'll run producer scripts manually).

Python Scripts (.py):

mock_data.py: Generates synthetic product data and saves it to a CSV file.

kafka_producer.py: Reads data from mock_data.csv and publishes it to the atlas-ingestion Kafka topic.

ai_agents.py: The core AI processing unit. It consumes raw product data from atlas-ingestion, performs various analyses (using models like Ollama for review analysis, OpenCV for image analysis, custom logic for anomalies), and publishes the processed results to the atlas-processed-data Kafka topic and stores JSON summaries in LocalStack S3.

store_codes.py: Retrieves the processed JSON data from LocalStack S3 and potentially stores it locally or forwards it (currently, its primary role is to ensure data is fetched from S3).

React Frontend (atlas-interface):

A web application built with React and Tailwind CSS.

Periodically polls the LocalStack S3 bucket (atlas-results-local/analyzed/) to fetch the latest analyzed product JSONs.

Displays the product authenticity status and detailed analysis results in an intuitive dashboard.

🔧 Prerequisites
Before you begin, ensure you have the following installed on your machine:

Git: https://git-scm.com/downloads

Docker Desktop: https://www.docker.com/products/docker-desktop/ (Ensure it's running before starting the project)

Python 3.8+: https://www.python.org/downloads/ (Python 3.9-3.11 are generally good for AI libraries)

pip (Python Package Installer): Usually comes with Python.

npm (Node Package Manager): Comes with Node.js.

Node.js LTS (Long Term Support): https://nodejs.org/en/download/ (Recommended for React development)

Ollama: https://ollama.com/download

Important: After installing Ollama, you need to pull the llama3.2:1b model. Open your command prompt/terminal and run:

ollama run llama3.2:1b

Let it download completely. You can then Ctrl+C to exit the chat session. This model is used by ai_agents.py for review authenticity.

⚙️ Setup and Running the System
Follow these steps carefully to get the entire ATLAS system up and running. Use Git Bash for all terminal commands on Windows.

1. Clone the Repository
First, clone the project from GitHub to your local machine:

git clone https://github.com/<your-username>/atlas-prototype-project-new.git
cd atlas-prototype-project-new # or whatever your repo name is

(Replace <your-username> with your actual GitHub username.)

2. Backend Docker Services Setup
This sets up Kafka, Zookeeper, and LocalStack in Docker containers.

Open Terminal 1 (Git Bash) and navigate to the project root:

cd /d/atlas-prototype # Or wherever you cloned the repo

Clean up any old Docker resources (crucial for a fresh start):

docker-compose down --rmi all
docker volume prune -f

Build and start all Docker services in detached mode:

docker-compose up -d --build

Wait for all services to show Started. This might take a few minutes for the initial build.

Verify Docker containers are running:

docker ps

Ensure atlas-api-backend, atlas-prototype-kafka-1, atlas-prototype-zookeeper-1, and atlas-prototype-localstack-1 are all Up.

3. Python Environment & AI Agents Setup
This prepares your Python virtual environment and starts the AI processing agents.

Open Terminal 2 (NEW Git Bash Window) and navigate to the project root:

cd /d/atlas-prototype

Create and activate a Python virtual environment:

python -m venv venv
source venv/Scripts/activate

Your prompt should change to (venv) ...

Install Python dependencies:

pip install -r requirements.txt
pip install awscli-local localstack-client # Ensure these are also installed

Start the AI Agents script (Kafka Consumer):

python ai_agents.py

Keep this terminal open. You should see AI Agent: Waiting for messages... after initial connection logs.

4. Frontend React Application Setup
This sets up the React environment and starts the web interface.

Open Terminal 3 (NEW Git Bash Window) and navigate to the React app directory:

cd /d/atlas-prototype/atlas-interface

Install Node.js dependencies:

npm install
npm install aws-sdk lucide-react # Ensure these are installed

Start the React development server:

npm start

This should open your web browser to http://localhost:3000 with the ATLAS 2.0 frontend.

5. Manually Trigger Data Generation
Since the frontend button to trigger the pipeline has been removed, you will manually run the data generation and Kafka producer scripts.

Open Terminal 4 (NEW Git Bash Window) and navigate to the project root:

cd /d/atlas-prototype

Activate your Python virtual environment:

source venv/Scripts/activate

Generate mock data:

python mock_data.py

Produce data to Kafka:

python kafka_producer.py

Allow a few seconds (e.g., 10-15) for ai_agents.py to process the messages.

Store codes (retrieve from S3 - frontend uses this):

python store_codes.py

6. Observe Results
Frontend (Browser): Your React app at http://localhost:3000 should start displaying the analyzed product data. It polls S3 every 10 seconds, so new data will appear automatically after ai_agents.py uploads it.

Terminal 2 (ai_agents.py): You'll see logs of messages being consumed and processed, and results being published/uploaded.

Kafka Console Consumer (Optional for debugging): To view raw messages in Kafka, open yet another terminal, docker exec -it atlas-prototype-kafka-1 bash, then run /usr/bin/kafka-console-consumer --bootstrap-server localhost:9092 --topic atlas-processed-data --from-beginning.

📂 Project Structure
atlas-prototype/
├── .gitignore             # Specifies files/folders to ignore (venv, node_modules, etc.)
├── docker-compose.yaml    # Docker setup for Kafka, Zookeeper, LocalStack, Flask API
├── Dockerfile_api         # Dockerfile for the Flask API backend
├── requirements.txt       # Python dependencies for backend scripts and AI agents
├── venv/                  # Python Virtual Environment (ignored by Git)
├── ai_agents.py           # Python script for AI-powered data analysis
├── mock_data.py           # Python script to generate synthetic product data
├── kafka_producer.py      # Python script to send mock data to Kafka
├── store_codes.py         # Python script to retrieve analyzed data from S3 (for local viewing/further processing)
├── atlas-interface/       # React Frontend Application
│   ├── public/            # Public assets for React app
│   ├── src/               # React source code (e.g., App.js)
│   ├── node_modules/      # Node.js dependencies (ignored by Git)
│   ├── package.json       # React project dependencies
│   └── ...
└── README.md              # This file

🔎 Search Engine Optimizer

An advanced search engine and ad recommendation system with semantic filtering, intent classification, and responsive UI that:
* Implements hybrid search using Elasticsearch and sentence embeddings via FAISS
* Recommends contextually relevant ads based on user intent and category similarity

🤝 Contributing
Contributions are welcome! If you find issues or have suggestions, please open an issue or submit a pull request on the GitHub repository.

📄 License
This project is open-source and available under the MIT License.


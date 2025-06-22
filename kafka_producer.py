import pandas as pd
from kafka import KafkaProducer
import json
import time
import os

# Configuration for Kafka and data files
KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'atlas-ingestion'
CSV_FILE = 'mock_training_data.csv'

def send_data_to_kafka():
    """
    Reads mock product data from a CSV file and sends it as JSON messages
    to a Kafka topic.
    """
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file '{CSV_FILE}' not found. Please run mock_data.py first to generate it.")
        return

    try:
        # Initialize Kafka Producer
        # value_serializer: converts the Python dictionary message to a JSON string
        # and then encodes it to bytes (utf-8) before sending.
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            # Optional: Add error handling for connection issues
            api_version=(0, 10, 1) # Specify Kafka API version if needed for compatibility
        )
        print(f"Producer connected to Kafka broker at {KAFKA_BROKER}.")
        print(f"Will send data from '{CSV_FILE}' to topic: '{KAFKA_TOPIC}'")

        # Read data from the generated CSV file
        df = pd.read_csv(CSV_FILE)
        print(f"Read {len(df)} rows from {CSV_FILE}.")

        # Iterate through each row of the DataFrame and send it as a Kafka message
        for index, row in df.iterrows():
            message = row.to_dict() # Convert DataFrame row to a Python dictionary
            producer.send(KAFKA_TOPIC, message) # Send the message to the specified topic
            print(f"Sent message {index+1}/{len(df)} (Product ID: {message.get('product_id', 'N/A')})")
            time.sleep(0.1) # Small delay to simulate a continuous stream and avoid overwhelming Kafka

        producer.flush() # Ensures all buffered messages are sent to Kafka
        print("All messages sent successfully!")

    except Exception as e:
        print(f"An error occurred while sending data to Kafka: {e}")
    finally:
        # Ensure the producer connection is closed cleanly
        if 'producer' in locals() and producer is not None:
            producer.close()
            print("Producer closed.")

if __name__ == "__main__":
    send_data_to_kafka()

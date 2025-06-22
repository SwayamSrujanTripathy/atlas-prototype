from confluent_kafka import Producer
import json
import time
import yaml
import os

def load_config():
    # Define default configuration
    default_config = {
        'environment': 'local',
        'kafka_bootstrap_servers': 'localhost:9092',
        's3_endpoint_url': 'http://localhost:4566', # Corrected LocalStack S3 endpoint
        's3_bucket': 'atlas-results-local',
        'aws_access_key_id': 'test',
        'aws_secret_access_key': 'test',
        'aws_region': 'ap-south-1',
        'upload_dir': 'uploads'
    }

    # Check if config.yaml exists and load it
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as f:
            user_config = yaml.safe_load(f)
            # Warn and fallback if s3_endpoint_url is incorrectly parsed as a list
            if isinstance(user_config.get('s3_endpoint_url'), list):
                print("Warning: 's3_endpoint_url' in config.yaml is parsed as a list. Please quote the value in config.yaml (e.g., 'http://localhost:4566'). Using default.")
                user_config['s3_endpoint_url'] = default_config['s3_endpoint_url'] # Fallback to default
            
            default_config.update(user_config) # Override defaults with user config
    
    return default_config

config = load_config()

conf = {'bootstrap.servers': config['kafka_bootstrap_servers'], 'client.id': 'atlas-producer'}
producer = Producer(conf)

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

for i in range(1, 101):
    product = {
        'product_id': f'P{i}',
        'seller_id': f'S{(i % 50) + 1}',
        'price': 50 + i,
        'review': f'Great product {i}!',
        'image_url': f"{config['upload_dir']}/product{i}.jpg",
        'category': 'electronics',
        'return_count': i % 10,
        'rating': (i % 5) + 1 # Added a dummy rating for seller behavior analysis
    }
    producer.produce('atlas-ingestion', value=json.dumps(product), callback=delivery_report)
    producer.poll(0)
    time.sleep(0.1)

producer.flush()

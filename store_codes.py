import sqlite3
import json
import boto3
import yaml
import os

def load_config():
    """Loads configuration from config.yaml or provides defaults."""
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    # Default configuration if config.yaml is not found
    return {
        'environment': 'local',
        'kafka_bootstrap_servers': 'localhost:9092',
        # --- IMPORTANT FIX HERE: Ensure s3_endpoint_url is a string, not a list ---
        's3_endpoint_url': 'http://localhost:4566', # Corrected to a valid string URL
        's3_bucket': 'atlas-results-local',
        'aws_access_key_id': 'test',
        'aws_secret_access_key': 'test',
        'aws_region': 'ap-south-1',
        'upload_dir': 'Uploads'
    }

# Load configuration
config = load_config()

# Initialize S3 client using configuration details
# Note: s3_endpoint_url should be a string. If you still get a warning about a list
# when using a config.yaml, ensure the value is quoted in config.yaml like this:
# s3_endpoint_url: 'http://localhost:4566'
s3_client = boto3.client(
    's3',
    endpoint_url=config['s3_endpoint_url'],
    aws_access_key_id=config['aws_access_key_id'],
    aws_secret_access_key=config['aws_secret_access_key'],
    region_name=config['aws_region']
)
bucket = config['s3_bucket']

# Connect to SQLite database
conn = sqlite3.connect('transparency_codes.db')
cursor = conn.cursor()

# Create transparency_codes table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS transparency_codes (
    product_id TEXT PRIMARY KEY,
    code TEXT,
    verified BOOLEAN
)
''')
print("Database table 'transparency_codes' ensured to exist.")

# Iterate only for the actual number of products (P1 to P8)
# This assumes your mock_data.py generates product IDs from P1 to P8.
num_products_to_process = 8

print(f"Attempting to retrieve and store data for {num_products_to_process} products from S3...")

for i in range(1, num_products_to_process + 1): # Loop from 1 to 8 (inclusive)
    product_id_str = f'P{i}'
    s3_key = f'analyzed/{product_id_str}.json'
    try:
        # Fetch the analyzed JSON object from S3
        obj = s3_client.get_object(Bucket=bucket, Key=s3_key)
        product_data = json.loads(obj['Body'].read().decode('utf-8'))

        # Extract relevant information
        product_id = product_data.get('product_id') # Use .get() for safety
        transparency_code = f'CODE{product_id}'
        verified = product_data.get('supply_verified')

        # Insert or replace data into the SQLite table
        cursor.execute('INSERT OR REPLACE INTO transparency_codes VALUES (?, ?, ?)', (product_id, transparency_code, verified))
        conn.commit()
        print(f"Successfully stored transparency code for {product_id}.")

    except s3_client.exceptions.NoSuchKey:
        print(f"Warning: S3 object '{s3_key}' not found. Skipping {product_id_str}. This is expected if ai_agents.py hasn't processed it yet or if the product ID is out of range.")
    except Exception as e:
        print(f"Error processing {s3_key}: {e}")

# Close the database connection
conn.close()
print("Database connection closed.")
print("Transparency codes storage process completed.")

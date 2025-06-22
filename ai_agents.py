import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from kafka import KafkaConsumer, KafkaProducer
import boto3
import yaml
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from PIL import Image
import cv2
from io import BytesIO
import base64
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Loading ---
def load_config():
    """Loads configuration from config.yaml or provides defaults."""
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            # Ensure s3_endpoint_url is a string, not a list
            if isinstance(config.get('s3_endpoint_url'), list):
                config['s3_endpoint_url'] = config['s3_endpoint_url'][0] # Take the first element if it's a list
            return config
    return {
        'environment': 'local',
        'kafka_bootstrap_servers': 'localhost:9092',
        's3_endpoint_url': 'http://localhost:4566',
        's3_bucket': 'atlas-results-local',
        'aws_access_key_id': 'test',
        'aws_secret_access_key': 'test',
        'aws_region': 'ap-south-1',
        'upload_dir': 'uploads' # Directory where logo files are expected
    }

config = load_config()

# --- S3 Client Initialization ---
s3_client = boto3.client(
    's3',
    endpoint_url=config['s3_endpoint_url'],
    aws_access_key_id=config['aws_access_key_id'],
    aws_secret_access_key=config['aws_secret_access_key'],
    region_name=config['aws_region']
)
s3_bucket = config['s3_bucket']

# Ensure S3 bucket exists
try:
    s3_client.create_bucket(Bucket=s3_bucket)
    logger.info(f"S3 bucket '{s3_bucket}' ensured to exist.")
except s3_client.exceptions.BucketAlreadyOwnedByYou:
    logger.info(f"S3 bucket '{s3_bucket}' already exists and is owned by you.")
except Exception as e:
    logger.error(f"Error ensuring S3 bucket '{s3_bucket}' exists: {e}")

# --- Helper for JSON Serialization (to handle NumPy types) ---
def convert_numpy_types(obj):
    """
    Recursively converts NumPy data types (like np.bool_) and other complex
    types within a dictionary or list to standard Python types for JSON serialization.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_): # Explicitly handle numpy boolean type
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(elem) for elem in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat() # Convert datetime objects to ISO 8601 string
    return obj


# --- AI Agents Setup ---

# 1. Review Authenticity Checker (LLM-based)
class ReviewAnalysis(BaseModel):
    is_fake: bool = Field(description="true if the review is likely fake, false otherwise")
    reason: str = Field(description="explanation for the decision")

class ReviewAuthenticityChecker:
    def __init__(self, llm_model="llama3.2:1b", base_url="http://localhost:11434"):
        self.llm = Ollama(model=llm_model, base_url=base_url)
        self.parser = JsonOutputParser(pydantic_object=ReviewAnalysis)
        self.prompt = PromptTemplate(
            template="Analyze the following product review and determine if it's fake. Respond in JSON format with 'is_fake' (boolean) and 'reason' (string).\nReview: {review}\n",
            input_variables=["review"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        logger.info(f"Initialized Ollama LLM with model: {llm_model}, base_url: {base_url}")

    def check_authenticity(self, review: str) -> dict:
        try:
            chain = self.prompt | self.llm | self.parser
            response = chain.invoke({"review": review})
            return response
        except Exception as e:
            logger.error(f"Error calling LLM for review authenticity: {e}. Assuming not fake.")
            return {"is_fake": False, "reason": "LLM call failed or out of memory."}

# 2. Product Vision Analyzer (Image-based - Simplified)
class ProductVisionAnalyzer:
    def __init__(self, upload_dir='uploads'):
        self.upload_dir = upload_dir
        # FIX: Initialize ORB detector and BFMatcher BEFORE loading templates
        self.orb = cv2.ORB_create()
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        # Pre-load template images for comparison.
        # Note: Paths here should match the actual filenames and extensions in your 'uploads' directory.
        self.templates = {
            'Adidas': self._load_logo_features(os.path.join(upload_dir, 'adidas fake shoes lgoo.jpg')),
            'Gucci': self._load_logo_features(os.path.join(upload_dir, 'gucci fake.jpg')),
            'Levis': self._load_logo_features(os.path.join(upload_dir, 'levis fake.jpg')),
            'Adidas_Fake': self._load_logo_features(os.path.join(upload_dir, 'adidas fake.jpg')),
            'Brand1_Logo': self._load_logo_features(os.path.join(upload_dir, 'brand1_logo.png')),
            'Brand2_Logo': self._load_logo_features(os.path.join(upload_dir, 'brand2_logo.jpg')),
            'Brand3_Logo': self._load_logo_features(os.path.join(upload_dir, 'brand3_logo.jpg')),
            'Brand4_Logo': self._load_logo_features(os.path.join(upload_dir, 'brand4_logo.jpg')),
            # Add other templates as needed based on your images
        }

    def _load_logo_features(self, image_path):
        """Loads an image, converts to grayscale, and detects ORB keypoints and descriptors."""
        if not os.path.exists(image_path):
            logger.warning(f"Warning: Logo file not found at {image_path}. Returning None for features.")
            return None
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                logger.warning(f"Warning: Could not read image file at {image_path}. Returning None for features.")
                return None
            kp, des = self.orb.detectAndCompute(img, None)
            return (kp, des)
        except Exception as e:
            logger.error(f"Error processing logo image {image_path}: {e}")
            return None

    def analyze_image(self, image_url: str) -> dict:
        """Analyzes a product image for logo matching and other visual cues."""
        if not image_url.startswith('uploads/'):
            logger.warning(f"Image URL {image_url} is not a local upload path. Skipping visual analysis.")
            return {"logo_match": "N/A", "visual_cues": []}

        local_image_path = os.path.join(self.upload_dir, os.path.basename(image_url))

        if not os.path.exists(local_image_path):
            logger.warning(f"Product image file not found at {local_image_path}. Cannot perform visual analysis.")
            return {"logo_match": "N/A", "visual_cues": ["image_file_missing"]}

        try:
            img_product = cv2.imread(local_image_path, cv2.IMREAD_GRAYSCALE)
            if img_product is None:
                logger.warning(f"Could not read product image file at {local_image_path}. Cannot perform visual analysis.")
                return {"logo_match": "N/A", "visual_cues": ["image_read_error"]}

            kp_product, des_product = self.orb.detectAndCompute(img_product, None)

            best_match = {"brand": "None", "good_matches": 0}

            if des_product is not None:
                for brand, (kp_template, des_template) in self.templates.items():
                    if des_template is None:
                        logger.info(f" Skipping matching with {brand}: No valid logo features for template.")
                        continue
                    if len(kp_product) < 2 or len(kp_template) < 2: # Need at least 2 keypoints for matching
                        logger.info(f" Skipping matching with {brand}: Not enough keypoints for matching.")
                        continue

                    matches = self.bf.match(des_product, des_template)
                    # Sort them in the order of their distance.
                    matches = sorted(matches, key=lambda x: x.distance)

                    # Consider only good matches (e.g., distance less than a threshold or top N matches)
                    good_matches = [m for m in matches if m.distance < 50] # Example threshold
                    logger.info(f" Compared with {brand} template: Found {len(good_matches)} good matches.")

                    if len(good_matches) > best_match["good_matches"]:
                        best_match["good_matches"] = len(good_matches)
                        best_match["brand"] = brand
            else:
                logger.warning(f"No descriptors found for product image {local_image_path}. Cannot perform logo matching.")

            visual_cues = []
            if best_match["good_matches"] > 5: # Arbitrary threshold for a "match"
                visual_cues.append(f"logo_matched_with_{best_match['brand']}")
            else:
                visual_cues.append("no_significant_logo_match")

            # Simple visual cues (placeholder for more advanced analysis)
            if img_product.shape[0] < 100 or img_product.shape[1] < 100:
                visual_cues.append("low_resolution_image")

            return {
                "logo_match": best_match["brand"] if best_match["good_matches"] > 5 else "None",
                "visual_cues": visual_cues
            }
        except Exception as e:
            logger.error(f"Error analyzing image {local_image_path}: {e}. Returning default analysis.")
            return {"logo_match": "Error", "visual_cues": ["analysis_error"]}


# 3. Pricing Anomaly Detector (Isolation Forest)
class PricingAnomalyDetector:
    def __init__(self):
        # Initialize Isolation Forest model
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.scaler = StandardScaler()
        self.data_fitted = False # To track if scaler has been fitted

    def train(self, historical_prices: pd.Series):
        """Trains the Isolation Forest model on historical price data."""
        prices_df = historical_prices.to_frame(name='price')
        # Fit scaler first
        self.scaler.fit(prices_df)
        scaled_prices = self.scaler.transform(prices_df)
        self.model.fit(scaled_prices)
        self.data_fitted = True
        logger.info("IsolationForest trained successfully.")

    def detect_anomaly(self, current_price: float) -> bool:
        """Detects if a current price is an anomaly."""
        if not self.data_fitted:
            logger.warning("PricingAnomalyDetector not trained yet. Cannot detect anomalies. Assuming not anomaly.")
            return False

        # Prepare current price for prediction (needs to be 2D array and scaled)
        current_price_scaled = self.scaler.transform(np.array([[current_price]]))
        # Predict returns -1 for outliers, 1 for inliers
        prediction = self.model.predict(current_price_scaled)
        return prediction[0] == -1

# 4. Return Anomaly Detector (Simple Threshold)
class ReturnAnomalyDetector:
    def __init__(self, threshold_percentage=0.1):
        self.threshold_percentage = threshold_percentage

    def detect_anomaly(self, return_count: int, total_sales: int = 100) -> bool: # total_sales is an assumption here
        """Detects if return count is anomalously high."""
        if total_sales == 0:
            return False # Avoid division by zero
        return (return_count / total_sales) > self.threshold_percentage

# 5. Seller Behavior Analyzer (Simple Burst Detection)
class SellerBehaviorAnalyzer:
    def __init__(self, review_burst_threshold=5, rating_drop_threshold=-1.0):
        self.review_burst_threshold = review_burst_threshold # Number of reviews in a short period
        self.rating_drop_threshold = rating_drop_threshold # Average rating drop (e.g., from 4.5 to 3.0 = -1.5)
        self.seller_history = {} # Stores historical data for sellers

    def analyze_behavior(self, seller_id: str, product_id: str, timestamp: datetime, rating: int) -> dict:
        """
        Analyzes seller behavior for suspicious patterns like review bursts or sudden rating drops.
        """
        if seller_id not in self.seller_history:
            self.seller_history[seller_id] = []

        # Add current transaction to history
        self.seller_history[seller_id].append({'timestamp': timestamp, 'rating': rating, 'product_id': product_id})

        # Sort history by timestamp
        self.seller_history[seller_id].sort(key=lambda x: x['timestamp'])

        is_suspicious = False
        reasons = []

        # Check for review bursts (simplified: many transactions in last hour/day)
        recent_transactions = [
            t for t in self.seller_history[seller_id]
            if t['timestamp'] > datetime.now() - timedelta(hours=24)
        ]
        if len(recent_transactions) > self.review_burst_threshold:
            is_suspicious = True
            reasons.append(f"Review burst detected ({len(recent_transactions)} transactions in 24 hours)")

        # Check for sudden rating drops (simplified: compare last few ratings to overall average)
        if len(self.seller_history[seller_id]) > 5: # Need enough data points
            recent_ratings = [t['rating'] for t in self.seller_history[seller_id][-5:]]
            overall_avg_rating = np.mean([t['rating'] for t in self.seller_history[seller_id][:-5]]) # Average before recent
            if overall_avg_rating > 0 and (np.mean(recent_ratings) - overall_avg_rating) < self.rating_drop_threshold:
                is_suspicious = True
                reasons.append(f"Sudden rating drop detected (from avg {overall_avg_rating:.1f} to {np.mean(recent_ratings):.1f})")

        return {
            "is_suspicious": is_suspicious,
            "reasons": reasons if is_suspicious else ["No suspicious behavior detected"]
        }


# --- Main AI Agents Orchestrator ---
class AIAgentsOrchestrator:
    def __init__(self, kafka_broker, input_topic, output_topic, upload_dir):
        self.consumer = KafkaConsumer(
            input_topic,
            bootstrap_servers=[kafka_broker],
            auto_offset_reset='earliest', # Start consuming from the beginning of the topic
            enable_auto_commit=True,
            group_id='ai-agents-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_broker],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        self.upload_dir = upload_dir

        # Initialize agents
        self.review_authenticity_checker = ReviewAuthenticityChecker(llm_model="llama3.2:1b", base_url="http://localhost:11434")
        self.product_vision_analyzer = ProductVisionAnalyzer(upload_dir=upload_dir)

        dummy_historical_prices = pd.Series(np.random.normal(50, 10, 100))
        self.pricing_anomaly_detector = PricingAnomalyDetector()
        self.pricing_anomaly_detector.train(dummy_historical_prices)

        self.return_anomaly_detector = ReturnAnomalyDetector()
        self.seller_behavior_analyzer = SellerBehaviorAnalyzer()

        logger.info(f"AI Agent: Connected to Kafka broker at {kafka_broker}. Consuming from topic: {input_topic}")
        logger.info(f"AI Agent: Will produce processed data to topic: {output_topic}")

    def process_message(self, message):
        raw_data = message.value
        logger.info(f"AI Agent: Received raw data for product {raw_data.get('product_id', 'N/A')}")

        product_id = raw_data.get('product_id')
        image_url = raw_data.get('image_url')
        category = raw_data.get('category')
        price = raw_data.get('price')
        seller_id = raw_data.get('seller_id')
        return_count = raw_data.get('return_count')
        review = raw_data.get('review')
        # Store original string timestamp for JSON serialization
        original_timestamp_str = raw_data.get('timestamp')
        # Convert to datetime object for internal calculations/agents that need it
        # Ensure timestamp_dt is not None before passing to seller_behavior_analyzer
        timestamp_dt = datetime.fromisoformat(original_timestamp_str.replace('Z', '+00:00')) if isinstance(original_timestamp_str, str) else None
        rating = raw_data.get('rating')


        processed_data = {
            'product_id': product_id,
            'timestamp': original_timestamp_str, # Store original string timestamp
            'raw_data': raw_data,
            'analysis_results': {}
        }

        # --- Execute tasks for each agent ---

        # Product Vision Analyzer
        logger.info(f"Executing task for Product Vision Analyzer with inputs: {raw_data}")
        vision_analysis = self.product_vision_analyzer.analyze_image(image_url)
        processed_data['analysis_results']['product_vision_analysis'] = vision_analysis

        # Pricing Anomaly Detector
        logger.info(f"Executing task for Pricing Anomaly Detector with inputs: {raw_data}")
        is_price_anomaly = self.pricing_anomaly_detector.detect_anomaly(price)
        processed_data['analysis_results']['pricing_anomaly'] = {"is_anomaly": is_price_anomaly}

        # Return Anomaly Detector
        logger.info(f"Executing task for Return Anomaly Detector with inputs: {raw_data}")
        is_return_anomaly = self.return_anomaly_detector.detect_anomaly(return_count)
        processed_data['analysis_results']['return_anomaly'] = {"is_anomaly": is_return_anomaly}

        # Review Authenticity Checker
        logger.info(f"Executing task for Review Authenticity Checker with inputs: {raw_data}")
        review_authenticity = self.review_authenticity_checker.check_authenticity(review)
        processed_data['analysis_results']['review_authenticity'] = review_authenticity

        # Seller Behavior Analyzer
        logger.info(f"Executing task for Seller Behavior Analyzer with inputs: {raw_data}")
        try:
            seller_behavior = self.seller_behavior_analyzer.analyze_behavior(
                seller_id=seller_id,
                product_id=product_id,
                timestamp=timestamp_dt, # Use datetime object here
                rating=rating
            )
            processed_data['analysis_results']['seller_behavior_analysis'] = seller_behavior
        except Exception as e:
            logger.error(f"Error executing task Analyze the behavior of seller {seller_id}, including checking for review and rating bursts.: {e}")
            processed_data['analysis_results']['seller_behavior_analysis'] = {"error": str(e), "is_suspicious": False, "reasons": ["Analysis failed"]}


        # --- Determine 'is_fake' status ---
        is_fake_status = False
        fake_reasons = []

        if processed_data['analysis_results']['review_authenticity'].get('is_fake'):
            is_fake_status = True
            fake_reasons.append("suspicious_review")
        if processed_data['analysis_results']['pricing_anomaly'].get('is_anomaly'):
            is_fake_status = True
            fake_reasons.append("pricing_anomaly")
        if processed_data['analysis_results']['return_anomaly'].get('is_anomaly'):
            is_fake_status = True
            fake_reasons.append("return_anomaly")
        if processed_data['analysis_results']['seller_behavior_analysis'].get('is_suspicious'):
            is_fake_status = True
            fake_reasons.append("suspicious_seller_behavior")

        initial_is_fake = raw_data.get('is_fake', 0)
        if initial_is_fake == 1:
            is_fake_status = True
            fake_reasons.append("image_based_detection")

        processed_data['is_fake'] = is_fake_status
        processed_data['fake_reasons'] = list(set(fake_reasons))

        # --- Determine 'supply_verified' (Placeholder) ---
        processed_data['supply_verified'] = not is_fake_status

        # --- Upload processed data to S3 ---
        s3_key = f'analyzed/{product_id}.json'
        try:
            # FIX: Convert processed_data types before JSON serialization
            json_serializable_data = convert_numpy_types(processed_data)
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=json.dumps(json_serializable_data, indent=4)
            )
            logger.info(f"Uploaded processed data for {product_id} to s3://{s3_bucket}/{s3_key}")
        except Exception as e:
            logger.error(f"Error uploading processed data for {product_id} to S3: {e}")

        # --- Publish processed data to Kafka output topic ---
        try:
            # FIX: Convert processed_data types before JSON serialization
            json_serializable_data = convert_numpy_types(processed_data)
            self.producer.send('atlas-processed-data', json_serializable_data)
            self.producer.flush()
            logger.info(f"AI Agent: Published processed result for {product_id} to Kafka topic 'atlas-processed-data'.")
        except Exception as e:
            logger.error(f"Error publishing processed data for {product_id} to Kafka: {e}")

    def consume_and_process(self):
        logger.info("AI Agent: Waiting for messages...")
        for message in self.consumer:
            self.process_message(message)

if __name__ == "__main__":
    logger.info("AI Agents: Starting consumption and processing...")
    orchestrator = AIAgentsOrchestrator(
        kafka_broker=config['kafka_bootstrap_servers'],
        input_topic='atlas-ingestion',
        output_topic='atlas-processed-data',
        upload_dir=config['upload_dir']
    )
    orchestrator.consume_and_process()

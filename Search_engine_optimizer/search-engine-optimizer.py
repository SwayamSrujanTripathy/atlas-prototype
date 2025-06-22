# Advanced Engine Optimizer - Core Components
# ------------------------------------------------
# Prerequisites:
# pip install elasticsearch transformers sentence-transformers fastapi uvicorn faiss-cpu

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs except errors
import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
from elasticsearch import Elasticsearch
import faiss
import numpy as np

# -------------------
# Initialize Services
# -------------------
app = FastAPI()
es = Elasticsearch("http://localhost:9200")  # Elasticsearch instance
model = SentenceTransformer("all-MiniLM-L6-v2")  # For semantic search
intent_classifier = pipeline("text-classification", model="roberta-large-mnli")

# -------------------
# Data Models
# -------------------
class SearchQuery(BaseModel):
    query: str
    filters: Optional[List[str]] = None
    save_filter_name: Optional[str] = None

class Ad(BaseModel):
    id: str
    title: str
    category: str
    vector: Optional[List[float]] = None

# -------------------
# Utility Functions
# -------------------
def parse_query(query: str) -> dict:
    """Parse boolean and exact match queries."""
    query = query.replace('AND', 'and').replace('OR', 'or').replace('NOT', 'not')
    return {"query": {"query_string": {"query": query}}}

def classify_intent(query: str) -> str:
    """Classify search intent using RoBERTa."""
    result = intent_classifier(query, top_k=1)[0]
    return result['label']

def embed_text(text: str) -> List[float]:
    return model.encode(text, convert_to_numpy=True).tolist()

# -------------------
# Search Endpoint
# -------------------
@app.post("/search")
def advanced_search(input: SearchQuery):
    parsed_query = parse_query(input.query)
    results = es.search(index="products", body=parsed_query)

    semantic_vector = embed_text(input.query)
    product_embeddings = np.load("product_embeddings.npy")
    index = faiss.IndexFlatL2(384)
    index.add(product_embeddings)

    D, I = index.search(np.array([semantic_vector]), 5)
    hybrid_results = [results['hits']['hits'][i] for i in I[0]]

    if input.save_filter_name:
        with open(f"filters/{input.save_filter_name}.txt", "w") as f:
            f.write(input.query)

    return {"results": hybrid_results}

# -------------------
# Ad Filtering Logic
# -------------------
@app.post("/ads/recommend")
def recommend_ads(query: str, viewed_categories: List[str]):
    intent = classify_intent(query)
    vector = embed_text(query)

    ads = load_ads()  # Mocked ad list
    relevant_ads = []

    for ad in ads:
        if ad.category in viewed_categories or ad.category == intent:
            ad_vec = np.array(ad.vector)
            sim = util.cos_sim(vector, ad_vec).item()
            if sim > 0.6:
                relevant_ads.append(ad)

    return {"intent": intent, "recommended_ads": relevant_ads}

# -------------------
# Mock Function
# -------------------
def load_ads():
    return [
        Ad(id="a1", title="Red Dress", category="Clothing", vector=embed_text("red dress")),
        Ad(id="a2", title="Suitcase", category="Luggage", vector=embed_text("suitcase")),
    ]

# Run with: uvicorn script:app --reload

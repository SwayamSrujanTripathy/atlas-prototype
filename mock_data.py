import pandas as pd
import numpy as np
from datetime import datetime, timedelta

product_image_mappings = {
    'P1': {'filename': 'adidas fake shoes lgoo.jpg', 'is_fake_status': 0}, # 0 for original, 1 for fake
    'P2': {'filename': 'brand1_logo.png', 'is_fake_status': 0},
    'P3': {'filename': 'adidas fake.jpg', 'is_fake_status': 1}, 
    'P4': {'filename': 'brand2_logo.jpg', 'is_fake_status': 0}, 
    'P5': {'filename': 'levis fake.jpg', 'is_fake_status': 1},
    'P6': {'filename': 'brand3_logo.jpg', 'is_fake_status': 0},
    'P7': {'filename': 'brand4_logo.jpg', 'is_fake_status': 0}, 
    'P8': {'filename': 'gucci fake.jpg', 'is_fake_status': 1},
}

product_ids_list = list(product_image_mappings.keys())
num_products = len(product_ids_list)

seller_ids_list = [f'S{(i % 50) + 1}' for i in range(num_products)]
prices_list = np.random.normal(50, 15, num_products).tolist()
categories_list = ['electronics' if i % 2 == 0 else 'clothing' for i in range(num_products)]
return_counts_list = np.random.randint(0, 20, num_products).tolist()
reviews_list = [f"Review {i} {'fake' if i % 10 == 0 else 'great'}" for i in range(num_products)]
timestamps_list = [datetime.now() - timedelta(days=np.random.randint(0, 30)) for _ in range(num_products)]
ratings_list = np.random.choice([1, 2, 3, 4, 5], size=num_products, p=[0.1, 0.1, 0.2, 0.3, 0.3]).tolist()

data_rows = []
for i, product_id in enumerate(product_ids_list):
    mapping = product_image_mappings[product_id]
    
    row = {
        'product_id': product_id,
        'seller_id': seller_ids_list[i],
        'price': prices_list[i],
        'category': categories_list[i],
        'return_count': return_counts_list[i],
        'review': reviews_list[i],
        'image_url': f"uploads/{mapping['filename']}", # Use specific filename
        'is_fake': mapping['is_fake_status'],         # Use specific fake status
        'timestamp': timestamps_list[i],
        'rating': ratings_list[i]
    }
    data_rows.append(row)

# Convert to DataFrame
df = pd.DataFrame(data_rows)

# Simulate a burst of reviews for product P1 (assuming P1 is a "real" product)
# Ensure P1 uses an image with brand1_logo.jpg
# We will append to the lists within the DataFrame directly for consistency
for i in range(10):
    new_row = {
        'product_id': 'P1',
        'seller_id': 'S1',
        'price': 50.0,
        'category': 'electronics',
        'return_count': 0,
        'review': f"Great product! {i}",
        'image_url': f"uploads/{product_image_mappings['P1']['filename']}", # Specific image for P1
        'is_fake': 0, # These are real reviews for a real product
        'timestamp': datetime.now() - timedelta(hours=i),
        'rating': 5
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)


df.to_csv('mock_training_data.csv', index=False)
print(f"Mock data generated: mock_training_data.csv with {len(df)} rows (based on {num_products} unique product images).")

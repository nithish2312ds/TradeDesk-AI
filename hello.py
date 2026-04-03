
import os, requests
from dotenv import load_dotenv
load_dotenv()
url = 'https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2'
headers = {'Authorization': f'Bearer {os.getenv(\"HF_TOKEN\")}'}
r = requests.post(url, headers=headers, json={'inputs': 'test', 'options': {'wait_for_model': True}})
result = r.json()
print(type(result))
print(type(result[0]) if isinstance(result, list) else 'not a list')
print(len(result[0]) if isinstance(result, list) and isinstance(result[0], list) else len(result))
"
import json
import os
import cohere
from datasets import load_dataset
from cohere.custom_model_dataset import JsonlDataset

cohere_key = os.getenv("CO_API_KEY")
co = cohere.Client(cohere_key)

# LOAD A DATASET
#dataset = load_dataset("Mindofmachine/paul_graham_and_sam_altman_articles")

data = dataset['train']

json_data = []

for item in data:
    json_data.append(item)

# Write the data to a JSON file
with open('dataset.json', 'w', encoding='utf-8') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=4)

with open('dataset.json', 'r') as file:
    data = json.load(file)

# Write to a JSONL file
with open('output_file.jsonl', 'w') as jsonl_file:
    for entry in data:
        jsonl_entry = {
            "query": "Read the post, learn, and reflect on how you can write like the author",
            "relevant_passages": [entry["prefix"] + " " + entry["content"]],
            "hard_negatives": []
        }
        jsonl_file.write(json.dumps(jsonl_entry) + '\n')

cohere_dataset = JsonlDataset(train_file="altman_passages_reduced.jsonl")
finetune = co.create_custom_model(name="altman-mode", dataset=cohere_dataset, model_type="GENERATIVE")
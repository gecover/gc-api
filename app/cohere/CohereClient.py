import cohere
import logging
import os
from typing import List

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# Class to wrap cohere api functionality for better modularity and reusability
class CohereClient:
    def __init__(self, api_key: str):
        self.co = cohere.Client(api_key)

    def chat(self, query: str, documents: List[dict]):
        return self.co.chat(query, documents=documents)

    def embed(self, responses: List[str], model: str = "embed-english-v3.0"):
        return self.co.embed(responses, input_type="search_document", model=model).embeddings

    def rerank(self, query: str, documents: List[str], top_n: int = 5, model: str = "rerank-multilingual-v2.0"):
        return self.co.rerank(query=query, documents=documents, top_n=top_n, model=model).results

    def summarize(self, text: str, format: str = "paragraph", temperature: float = 0.96, length: str = 'long', model: str = 'command-nightly', extractiveness: str = 'auto', additional_command: str = ''):
        return self.co.summarize(
            text=text,
            format=format,
            temperature=temperature,
            length=length,
            model=model,
            extractiveness=extractiveness,
            additional_command=additional_command
        )

    def generate(self, model: str, prompt: str, k: int = 25, temperature: float = 0.96, frequency_penalty: float = 0.2, num_generations: int = 1):
        return self.co.generate(model=model, prompt=prompt, k=k, temperature=temperature, frequency_penalty=frequency_penalty, num_generations=num_generations)
    
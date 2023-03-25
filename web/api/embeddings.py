# ---------------------------------- web code ----------------------------------

import json

from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    # post request = calculate factorial of passed number
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        results = {};

        for i, link in enumerate(embeddings(data['query'])):
            results[i] = json.dumps(link.__dict__)

        self.wfile.write(json.dumps(results).encode('utf-8'))


class Link:
    def __init__(self, url, title):
        self.url = url
        self.title = title


# -------------------------------- non-web-code --------------------------------
import time
import pickle
import os

import numpy as np

import openai
from openai.error import RateLimitError

from functools import wraps
from typing import Callable, List, Type, Union

# OpenAI API key
os.environ.get('OPENAI_API_KEY')
openai.api_key = os.environ.get('OPENAI_API_KEY') 

# OpenAI models
EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "text-davinci-003"

# OpenAI parameters
LEN_EMBEDDINGS = 1536
MAX_LEN_PROMPT = 4095 # This may be 8191, unsure.

# Paths
from pathlib import Path
project_path = Path(__file__).parent.parent.parent
PATH_TO_DATA = project_path / "src" / "data" / "alignment_texts.jsonl" # Path to the dataset .jsonl file.
PATH_TO_EMBEDDINGS = project_path / "src" / "data" / "embeddings.npy" # Path to the saved embeddings (.npy) file.
PATH_TO_DATASET = project_path / "src" / "data" / "dataset.pkl" # Path to the saved dataset (.pkl) file, containing the dataset class object.


def retry_on_exception_types(exception_types: List[Type[Exception]], stop_after_attempt: int, max_wait_time: int) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < stop_after_attempt:
                try:
                    return func(*args, **kwargs)
                except tuple(exception_types) as e:
                    if attempts + 1 == stop_after_attempt:
                        raise e
                    wait_time = min(max_wait_time, (2 ** attempts))  # Exponential backoff
                    time.sleep(wait_time)
                    attempts += 1
        return wrapper
    return decorator

@retry_on_exception_types(exception_types=[RateLimitError], stop_after_attempt=4, max_wait_time=10)
def get_embedding_batch(texts: List[str]) -> np.ndarray:
    result = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return result["data"][0]["embedding"]

@retry_on_exception_types(exception_types=[RateLimitError], stop_after_attempt=4, max_wait_time=10)
def get_embedding(text: str) -> np.ndarray:
    result = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return result["data"][0]["embedding"]

def get_top_k_blocks(user_query: str, k: int, HyDE: bool = False):
    """Get the top k blocks that are most semantically similar to the query, using the provided dataset. 

    Args:
        query (str): The query to be searched for.
        k (int): The number of blocks to return.
        HyDE (bool, optional): Whether to use HyDE or not. Defaults to False.

    Returns:
        List[str]: A list of the top k blocks that are most semantically similar to the query.
    """
    # Get the dataset
    with open(PATH_TO_DATASET, "rb") as f:
        metadataset = pickle.load(f)
    
    # Get the embedding for the query.
    query_embedding = get_embedding(user_query)
    
    # If HyDE is enabled, produce a no-context ChatCompletion to the query.
    if HyDE:
        messages = [
            {"role": "system", "content": "You are a knowledgeable AI Alignment assistant. Do your best to answer the user's question, even if you don't know the answer for sure."},
            {"role": "user", "content": user_query},
        ]
        HyDE_completion = openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=200
        )["choices"][0]["text"]
        HyDe_completion_embedding = get_embedding(f"Question: {user_query}\n\nAnswer: {HyDE_completion}")
        
        similarity_scores = np.dot(metadataset.embeddings, HyDe_completion_embedding)        
    else:
        similarity_scores = np.dot(metadataset.embeddings, query_embedding)
    
    ordered_blocks = np.argsort(similarity_scores)[::-1]  # Sort the blocks by similarity score
    top_k_indices = ordered_blocks[:k]  # Get the top k indices
    
    # Get associated strings
    top_k_strings = [metadataset.embedding_strings[i] for i in top_k_indices]  # Get the top k strings
    
    # Get associated links
    top_k_links = [metadataset.metadata[metadataset.embeddings_metadata_index[i]][3] for i in top_k_indices]  # Get the top k sources
    
    links = []
    for string, link in zip(top_k_strings, top_k_links):
        links.append(Link(link, string))
        
    return links

def embeddings(query):
    # write a function here that takes a query, returns a bunch of semantically similar links
    
    link_list = get_top_k_blocks(query, 4)
    
    return link_list


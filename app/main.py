from typing import Union, Annotated, List
import os
import numpy as np
import json
import re
import cohere
from fastapi import FastAPI, File, UploadFile, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from concurrent.futures import ThreadPoolExecutor
from supabase import create_client, Client
from dotenv import find_dotenv
from dotenv import load_dotenv
from pydantic import BaseModel
from app.scrape.ScrapeClient import ScrapingClient
from openai import OpenAI
import time


class URLPayload(BaseModel):
    url: str

class ModelPayload(BaseModel):
    model: str

env_file = find_dotenv(".env.dev")
load_dotenv(env_file)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
SCRAPE_CLIENT_API_KEY = os.environ.get("SCRAPE_API_KEY")

supabase: Client = create_client(url, key)
scrape_client = ScrapingClient(scrapeops_api_key=SCRAPE_CLIENT_API_KEY, num_concurrent_threads=5)
client = OpenAI()

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Specify your frontend origin here
origins = [
    "http://localhost:3000/*",  # The origin where your frontend is hosted
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows specified origins or ["*"] for all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def read_root():
    return {"Hello": "GeCover"}

@app.post("/extract_url/")
async def extract_url(payload: URLPayload, token: Annotated[str, Depends(oauth2_scheme)]): #, token: Annotated[str, Depends(oauth2_scheme)]
    # get user data from JWT
    data = supabase.auth.get_user(token)
    # assert that the user is authenticated.
    assert data.user.aud == 'authenticated', "402: not authenticated."

    response = scrape_client.send_request(payload.url)
    if response:
        #print(response)
        return response
    else:
        return {"error" : "Unable to extract job data from URL!"}

@app.post("/generate_paragraphs/")
def generate_paragraphs(file: Annotated[bytes, File()], requirements: str, token: Annotated[str, Depends(oauth2_scheme)]):#, token: Annotated[str, Depends(oauth2_scheme)]
    # get user data from JWT
    data = supabase.auth.get_user(token)
    # assert that the user is authenticated.
    assert data.user.aud == 'authenticated', "402: not authenticated."

    try:
        # content = client.detect_document_text(Document={'Bytes': file})
        file = client.files.create(
            file=file,
            purpose="assistants"
        )

    except Exception as err:
        print(err)
        return {"para_A" : 'bad error handling i apologize. TODO <==='}

    # input_credentials = ("\n - ").join(requirements)


    prompt = f"""
    - {requirements}

    Could you write me a couple paragraphs without an introduction/outro about why I am the right candidate for the job? The document you have access to is my CV.
    """

    print(prompt)

    thread = client.beta.threads.create(
        messages=[
            {
            "role": "user",
            "content": prompt,
            "file_ids": [file.id]
            }
        ]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id="asst_C0GRyfBLNOXtrxlOPpA4ouvr",
    )

    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run.status == 'completed':
            break

        time.sleep(3)

    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )

    delete_file = client.files.delete(file.id)
    delete_thread = client.beta.threads.delete(thread.id)

    # print(messages.data[0].content[0].text.value)
    # print(delete_thread)
    return {'para_A' : messages.data[0].content[0].text.value, 'para_B' : 'result.data[1]'}  
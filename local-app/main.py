from typing import Union, Annotated, List
import os
import numpy as np
import time
import json
import re
import cohere
from llmsherpa.readers import LayoutPDFReader
from fastapi import FastAPI, File, UploadFile, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from concurrent.futures import ThreadPoolExecutor
from supabase import create_client, Client
from dotenv import find_dotenv
from dotenv import load_dotenv
import bs4 as bs
import urllib.request
from pydantic import BaseModel
from openai import OpenAI
import logging

# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)

# requests_log = logging.getLogger("requests")
# requests_log.setLevel(logging.ERROR)
# requests_log.propagate = True

import boto3
import io

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")

session = boto3.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
client = session.client('textract', region_name='us-east-1')


class URLPayload(BaseModel):
    url: str

class ModelPayload(BaseModel):
    model: str

# llm sherpa for reading pdfs
llmsherpa_api_url = "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all"
pdf_reader = LayoutPDFReader(llmsherpa_api_url)


env_file = find_dotenv(".env.local")
load_dotenv(env_file)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

cohere_key = os.getenv("CO_API_KEY")
co = cohere.Client(cohere_key)

openai = OpenAI()

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
    return {"Hello": "World"}

@app.post("/extract_url/")
async def extract_url(payload: URLPayload): #, token: Annotated[str, Depends(oauth2_scheme)]
    # # get user data from JWT
    # data = supabase.auth.get_user(token)
    # # assert that the user is authenticated.
    # assert data.user.aud == 'authenticated', "402: not authenticated."
    
    source = urllib.request.urlopen(payload.url)
    soup = bs.BeautifulSoup(source,'lxml')
    div = soup.find("div", class_ = "show-more-less-html__markup show-more-less-html__markup--clamp-after-5 relative overflow-hidden" )
    if div:
        # summarize with cohere
        # tempurature zero for the time being.
        # keeping it at zero allows us to better experiment and tweak things, knowing the LLM is a control.
        prompt = f"Please extract the most important job requirements from the following job posting and list them in point form: {div.get_text()}."
        completion = openai.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        response = completion.choices[0].message.content
        
        # first element is always ""
        clean_response = response.split('- ')[1:]

        company = soup.find("a", class_="topcard__org-name-link topcard__flavor--black-link").get_text()
        pattern = r"(?<=\n)(.*?)(?=\n)"
        clean_company = re.findall(pattern, company)[0]
        job_title = soup.find("h1", class_="top-card-layout__title font-sans text-lg papabear:text-xl font-bold leading-open text-color-text mb-0 topcard__title").get_text()
        return {"contents" : clean_response, 'company': clean_company, 'job_title': job_title}
    else:
        return {"error" : "div not found"}



@app.post("/read_pdf/")
async def read_pdf(file: Annotated[bytes, File()]):
    
    # get user data from JWT
    # data = supabase.auth.get_user(token)

    # # assert that the user is authenticated.
    # assert data.user.aud == 'authenticated', "402: not authenticated."

    # the path_or_url is fake, ignored when contents is set.
    try:
        # content = client.detect_document_text(Document={'Bytes': file})
        response = openai.files.create(
            file=file,
            purpose="assistants"
        )
        return {"id" : response.id}
    except:
        # very mid error handling
        return {"id" : None}

@app.post("/generate_paragraphs/")
def generate_paragraphs(file: Annotated[bytes, File()], requirements: str):#, token: Annotated[str, Depends(oauth2_scheme)]
    # # get user data from JWT
    # data = supabase.auth.get_user(token)
    # # # assert that the user is authenticated.
    # assert data.user.aud == 'authenticated', "402: not authenticated."

    try:
        # content = client.detect_document_text(Document={'Bytes': file})
        file = openai.files.create(
            file=file,
            purpose="assistants"
        )
    except:
        return {"id" : None}

    # input_credentials = ("\n - ").join(requirements)


    prompt = f"""
    - {requirements}

    Could you write me a couple paragraphs without an introduction/outro about why I am the right candidate for the job? The document you have access to is my CV.
    """

    print(prompt)

    thread = openai.beta.threads.create(
        messages=[
            {
            "role": "user",
            "content": prompt,
            "file_ids": [file.id]
            }
        ]
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id="asst_C0GRyfBLNOXtrxlOPpA4ouvr",
    )

    while True:
        run = openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run.status == 'completed':
            break

        time.sleep(3)

    messages = openai.beta.threads.messages.list(
        thread_id=thread.id
    )

    delete_file = openai.files.delete(file.id)
    delete_thread = openai.beta.threads.delete(thread.id)

    # print(messages.data[0].content[0].text.value)
    # print(delete_thread)
    return {'para_A' : messages.data[0].content[0].text.value, 'para_B' : 'result.data[1]'}
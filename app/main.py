from typing import Union, Annotated, List
import os

import numpy as np
import json
import re

import cohere

from llmsherpa.readers import LayoutPDFReader

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware

from concurrent.futures import ThreadPoolExecutor

from dotenv import find_dotenv
from dotenv import load_dotenv

import bs4 as bs
import urllib.request

from pydantic import BaseModel

class URLPayload(BaseModel):
    url: str
    
# llm sherpa for reading pdfs
llmsherpa_api_url = "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all"
pdf_reader = LayoutPDFReader(llmsherpa_api_url)


env_file = find_dotenv(".env.dev")
load_dotenv(env_file)
cohere_key = os.getenv("CO_API_KEY")
co = cohere.Client(cohere_key)

app = FastAPI()

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
async def extract_url(payload: URLPayload):
    source = urllib.request.urlopen(payload.url)
    soup = bs.BeautifulSoup(source,'lxml')
    div = soup.find("div", class_ = "show-more-less-html__markup show-more-less-html__markup--clamp-after-5 relative overflow-hidden" )
    if div:
        # summarize with cohere
        # tempurature zero for the time being.
        # keeping it at zero allows us to better experiment and tweak things, knowing the LLM is a control.
        response = co.summarize( 
            text=div.get_text(),
            length='long',
            format='bullets',
            model='command',
            additional_command='ONLY EXTRACT REQUIRED QUALIFICATIONS.',
            extractiveness='high',
            temperature=0.0,
        ) 
        # first element is always ""
        clean_response = response.summary.split('- ')[1:]

        company = soup.find("a", class_="topcard__org-name-link topcard__flavor--black-link").get_text()
        pattern = r"(?<=\n)(.*?)(?=\n)"
        clean_company = re.findall(pattern, company)[0]
        job_title = soup.find("h1", class_="top-card-layout__title font-sans text-lg papabear:text-xl font-bold leading-open text-color-text mb-0 topcard__title").get_text()
        return {"contents" : clean_response, 'company': clean_company, 'job_title': job_title}
    else:
        return {"error" : "div not found"}



@app.post("/read_pdf/")
async def read_pdf(file: Annotated[bytes, File()]):
    # the path_or_url is fake, ignored when contents is set.
    content = pdf_reader.read_pdf(path_or_url="https://someexapmple.com/myfile.pdf", contents=file)
    docs = []
    for section in content.sections():
        docs.append(section.to_text(include_children=True, recurse=True))

    return {"contents": docs }

@app.post("/generate_paragraphs/")
def generate_paragraphs(requirements: List[str], resume_documents: List[str]):
    documents = []

    for doc in resume_documents:
        documents.append({"snippet" : doc})

    queries = []

    for i, req in enumerate(requirements):
        query = f""" 
        Explain in a couple sentences in first person about how I satisfy the following job requirement: 

        {req}

        My resume is in the documents supplied.
        """
        queries.append(query)

    with ThreadPoolExecutor(max_workers=len(requirements)) as executor:
        futures = [executor.submit(co.chat, query, documents=documents) for query in queries]
        responses = [future.result().text for future in futures]

    para_one_prompt = f"""
    Write professionally. Do not act as a chat bot.
    Summarize the following information into two paragraphs: 

    {(' ').join(responses)}

    Write in first person. Take a breath, and write like you are speaking to someone.

    Remember to format it as two paragraphs. Remember to not talk to the user as a chat bot.
    """

    # para_two_prompt = f"""
    # Condense the following information into the second paragraph of a cover letter: 
    # {(' ').join(responses[len(responses)//2:])}
    # Write in first person. Don't include information that has no evidence.
    # """

    # with ThreadPoolExecutor(max_workers=2) as executor:
    #     futures = [executor.submit(co.generate, para_one_prompt, temperature=0.0), executor.submit(co.generate, para_two_prompt, temperature=0.0)]
    #     responses = [future.result() for future in futures]


    # k value flattens the probability distribution 
    # frequency penalty decreases likelihood of repititon of specific tokens. (further decreasing ai content detection.)
    # frequency penalty also decreases the likelihood of formatting stuff like \n appearing. 
    # tempurature of 1.2 seems to be a sweet spot. I think anything [1.0, 1.5] is good for natural text generation.
    result = co.generate(para_one_prompt, k=25, temperature=1.2, frequency_penalty=0.1, num_generations=2) 

    return {'para_A' : result.data[0], 'para_B' : result.data[1]}

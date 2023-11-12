from typing import Union, Annotated, List
import os

import numpy as np

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
        return {"contents" : clean_response}
    else:
        return {"error" : "div not found"}



@app.post("/read_pdf/")
async def read_pdf(file: Annotated[bytes, File()]):
    # the path_or_url is fake, ignored when contents is set.
    content = pdf_reader.read_pdf(path_or_url="", contents=file)
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
    Condense the following information into the first paragraph of a cover letter: 
    {(' ').join(responses[:len(responses)//2])}
    Write in first person. Don't include information that has no evidence.
    """

    para_two_prompt = f"""
    Condense the following information into the second paragraph of a cover letter: 
    {(' ').join(responses[len(responses)//2:])}
    Write in first person. Don't include information that has no evidence.
    """

    first_para = co.generate(
        prompt=para_one_prompt
    )

    second_para = co.generate(
        prompt=para_two_prompt
    )

    
    # first_para = co.summarize( 
    #     text=(' ').join(responses[:len(responses)//2]),
    #     length='long',
    #     format='paragraph',
    #     model='command',
    #     extractiveness='high',
    #     additional_command='In first person for the first paragraph of a cover letter.',
    #     temperature=0.0,
    # ) 
    
    # second_para = co.summarize( 
    #     text=(' ').join(responses[len(responses)//2:]),
    #     length='long',
    #     format='paragraph',
    #     model='command-nightly',
    #     extractiveness='high',
    #     additional_command='In first person for the second paragraph of a cover letter.',
    #     temperature=0.0,
    # ) 

    return {'first_para' : first_para, 'second_para':second_para}

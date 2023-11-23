from typing import Union, Annotated, List
import os
import numpy as np
from llmsherpa.readers import LayoutPDFReader
from fastapi import FastAPI, File, UploadFile, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from concurrent.futures import ThreadPoolExecutor
from supabase import create_client, Client
from dotenv import find_dotenv
from dotenv import load_dotenv
from pydantic import BaseModel
from app.scrape.ScrapeClient import ScrapingClient
from app.cohere.CohereClient import CohereClient

env_file = find_dotenv(".env.dev")
load_dotenv(env_file)

COHERE_API_KEY = os.getenv("CO_API_KEY")
SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
SUPABASE_API_KEY: str = os.environ.get("SUPABASE_KEY")
SCRAPE_CLIENT_API_KEY = os.environ.get("SCRAPE_API_KEY")

co = CohereClient(COHERE_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)
scrape_client = ScrapingClient(scrapeops_api_key=SCRAPE_CLIENT_API_KEY, num_concurrent_threads=5)

# llm sherpa for reading pdfs
llmsherpa_api_url = "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all"
pdf_reader = LayoutPDFReader(llmsherpa_api_url)

class URLPayload(BaseModel):
    url: str

class ModelPayload(BaseModel):
    model: str
    
app = FastAPI()

#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
    # get user data from JWT
   # data = supabase.auth.get_user(token)
    # assert that the user is authenticated.
    #assert data.user.aud == 'authenticated', "402: not authenticated."

    response = scrape_client.send_request(payload.url)
    if response:
        #print(response)
        return response
    else:
        return {"error" : "Unable to extract job data from URL!"}

@app.post("/read_pdf/")
async def read_pdf(file: Annotated[bytes, File()]):
    
    # get user data from JWT
    #data = supabase.auth.get_user(token)

    # assert that the user is authenticated.
    #assert data.user.aud == 'authenticated', "402: not authenticated."

    # the path_or_url is fake, ignored when contents is set.
    try:
        content = pdf_reader.read_pdf(path_or_url="https://someexapmple.com/myfile.pdf", contents=file)
    except:
        # very mid error handling
        return {"contents" : []}

    docs = []
    for section in content.sections():
        docs.append(section.to_text(include_children=True, recurse=True))
    
    return {"contents": docs }

@app.post("/generate_paragraphs/")
def generate_paragraphs(requirements: List[str], resume_documents: List[str], model: ModelPayload):#, token: Annotated[str, Depends(oauth2_scheme)]
    # # get user data from JWT
   # data = supabase.auth.get_user(token)
    # # assert that the user is authenticated.
    #assert data.user.aud == 'authenticated', "402: not authenticated."

    documents = []

    for doc in resume_documents:
        documents.append({"snippet" : doc})

    queries = []

    for i, req in enumerate(requirements):
        query = f""" 
        You are acting as a personal professional writer.
        Explain in two sentences about how I satisfy the following job requirement written in the first person:
        note: Do not act as a chat bot. Do not preface the response with "sure, here is that summary:". 
        note: Do not finish the paragraph with anything like  "anything else I can help with?" or "is there anything else you would like to know?".
        note: If you don't have the information, do not output things like [Company name] or [first name] placeholders.
        Reference the documents provided that contain information about me. Be positive and enthusiastic!

        Job requirement:
        {req}

        Summary of why I satisfy the job requirement in 2-3 sentences:
        """
        queries.append(query)
    #print('QUERIES: ', queries)

    with ThreadPoolExecutor(max_workers=len(requirements)) as executor:
        futures = [executor.submit(co.chat, query, documents=documents) for query in queries]
        responses = [future.result().text for future in futures]

    #Encode your documents with input type 'search_document'
    doc_emb = co.embed(responses)
    doc_emb = np.asarray(doc_emb)

    query = """ The most important job requirement to satisfy."""

    rerank_hits = co.rerank(query=query, documents=responses, top_n=min(len(documents), 5))
    
    rerank_results = [x.document['text'] for x in rerank_hits]

    # reverse it, because LLMs have a recency bias
    rerank_results.reverse()

    # rerank_hits.reverse()
    input_credentials = ("\n - ").join(rerank_results)
    
    if model == 'altman':
        para_one_prompt = f"""
        You are acting as a personal professional writer.
        note: DO NOT prompt the user as a chat bot. Don't repeat skills once you have said them. 
        note: Make it a maximum of two paragraphs.  
        note:  Please only output the paragraph. Do not preface the paragraphs with "sure, here are those paragraphs:". Do not finish the paragraph with anything like  "anything else I can help with?".
        note: if you don't have the information, do not output tokens like "[Company name]" or "[first name]" as placeholders.
        Write in first person, and be positive and enthusiastic!
        
        The points to summarize:
        - {input_credentials}

        First person summary:   
        """
        result = co.generate(model='e1f1b8c8-f87a-4fd3-9346-99068e5b7036-ft', prompt=para_one_prompt, k=25, temperature=0.96, frequency_penalty=0.2, num_generations=1) 
        return {'para_A' : result.data[0], 'para_B' : 'result.data[1]'}    

    else:
        response  = co.summarize(
            text=input_credentials,
            format="paragraph",
            temperature=0.96,
            length='long',
            model='command-nightly',
            extractiveness='auto',
            additional_command='Generate a summary of the first person credentials being provided. The summary should maintain the first-person prose. Remove all open-ended questions and placeholder tokens like [company name] or [first name] as examples.'
        )
        return {'para_A' : response.summary, 'para_B' : 'result.data[1]'}

    return {'para_A' : "something broke", 'para_B' : 'result.data[1]'}    
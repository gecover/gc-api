from typing import Union, Annotated, List
import os

import numpy as np

import cohere

from llmsherpa.readers import LayoutPDFReader

from fastapi import FastAPI, File, UploadFile, Request

from dotenv import find_dotenv
from dotenv import load_dotenv

import bs4 as bs
import urllib.request

# llm sherpa for reading pdfs
llmsherpa_api_url = "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all"
pdf_reader = LayoutPDFReader(llmsherpa_api_url)


env_file = find_dotenv(".env.dev")
load_dotenv(env_file)
cohere_key = os.getenv("CO_API_KEY")
co = cohere.Client(cohere_key)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/extract_url/")
async def extract_url(url: str):
    source = urllib.request.urlopen(url)
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
            model='summarize-xlarge',
            additional_command='Extract job requirements for writing a cover letter.',
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
    content = pdf_reader.read_pdf(path_or_url="https://someexapmple.com/myfile.pdf", contents=file)
    docs = []
    for section in content.sections():
        docs.append(section.to_text(include_children=True, recurse=True))

    return {"contents": docs }

@app.post("/search_sentences/")
async def search(query: str, sentences: List[str]):
    doc_emb = co.embed(sentences, input_type="search_document", model="embed-english-v3.0").embeddings
    doc_emb = np.asarray(doc_emb)

    query = """The candidate should have a collaborative approach to stakeholder engagement and possess an understanding of A/B testing."""
    query_emb = co.embed([query], input_type="search_query", model="embed-english-v3.0").embeddings
    query_emb = np.asarray(query_emb)

    scores = np.dot(query_emb, doc_emb.T)[0]
    # max_idx = np.argsort(-scores)

    return {'scores' : scores}

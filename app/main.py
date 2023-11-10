from typing import Union, Annotated
import os
import pypdf

from llmsherpa.readers import LayoutPDFReader

from fastapi import FastAPI, File, UploadFile

# llm sherpa for reading pdfs
llmsherpa_api_url = "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all"
pdf_reader = LayoutPDFReader(llmsherpa_api_url)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/read_pdf/")
async def read_pdf(file: Annotated[bytes, File()]):
    # the path_or_url is fake, ignored when contents is set.
    content = pdf_reader.read_pdf(path_or_url="https://someexapmple.com/myfile.pdf", contents=file)
    docs = []
    for section in content.sections():
        docs.append(section.to_text(include_children=True, recurse=True))
    return {"content": docs }
    

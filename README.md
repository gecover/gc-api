# gc-api

## run locally

 uvicorn app.main:app --host 0.0.0.0 --port 5000

 ## run docker container for hosting

 docker compose up

 ## upload pdf example

  curl -X POST -F "file=@vaughan_love_resume.pdf" http://localhost:5000/uploadfile/
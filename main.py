import asyncio
import logging
import os
from fastapi import FastAPI, Path, Request, WebSocket, logger
from fastapi.concurrency import iterate_in_threadpool
from fastapi.templating import Jinja2Templates 
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from models.log_generator import LoggingMiddleware
from fastapi.middleware.cors import CORSMiddleware
from saltware import router as sapie_router
from dotenv import load_dotenv

app =FastAPI()
base_dir = Path(__file__).resolve().parent
log_file = "app.log"

templates = Jinja2Templates(directory=str(Path(base_dir, "templates")))
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)
app.add_middleware(LoggingMiddleware)
load_dotenv()

async def log_reader(n=5):
    log_lines = []
    with open(f"{base_dir}/{log_file}", "r") as file:
        for line in file.readlines()[-n:]:
            if line.__contains__("ERROR"):
                log_lines.append(f'<span class="text-red-400">{line}</span><br/>')
            elif line.__contains__("WARNING"):
                log_lines.append(f'<span class="text-orange-300">{line}</span><br/>')
            else:
                log_lines.append(f"{line}<br/>")
        return log_lines
    
@app.websocket("/ws/log")
async def websocket_endpoint_log(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(1)
            logs = await log_reader(30)
            await websocket.send_text(logs)
    except Exception as e:
        print(e)
    finally:
        await websocket.close()

@app.get("/logs")
async def get(request: Request):
    context = {"title": "FastAPI Streaming Log Viewer over WebSockets", "log_file": log_file, "ws_url": os.getenv('WS_URL')}
    return templates.TemplateResponse("index.html", {"request": request, "context": context})

@app.get('/')
async def home():
    return {"message":"main page"}

@app.get("/test")
async def test():
    return {"message": "Hello World"}

app.include_router(sapie_router)

# if __name__ == "__main__":        #.파일만 실행해도 서버가 실행되게
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000)

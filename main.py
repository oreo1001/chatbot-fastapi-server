import asyncio
import logging
import os
import sys
import traceback
from fastapi import FastAPI, Path, Request, WebSocket, logger
from fastapi.concurrency import iterate_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates 
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from models.log_generator import LoggingMiddleware
from fastapi.middleware.cors import CORSMiddleware
from saltware import router as sapie_router
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

app =FastAPI()
base_dir = Path(__file__).resolve().parent
log_file = "app.log"

templates = Jinja2Templates(directory=str(Path(base_dir, "templates")))
app.mount("/static", StaticFiles(directory="static"), name="static")

def log_config():
    #경로 설정
    real_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(real_path)
    parent_dir = os.path.dirname(dir_path)
    LOGFILE = os.path.join(parent_dir, 'app.log')

    #로그 형식 등 설정
    logger = logging.getLogger("log_app")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:  #이거 없으면 두번씩 출력됨 핸들러땜에
        file_handler = RotatingFileHandler(LOGFILE, maxBytes=10000000, backupCount=1)
        # file_handler = logging.FileHandler(LOGFILE)
        stream_handler = logging.StreamHandler() 
        #- %(name)s  log_app
        formatter = logging.Formatter("[%(asctime)s]  %(name)s %(levelname)s - %(message)s",datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    return logger

logger = log_config()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)
app.add_middleware(LoggingMiddleware,logger=logger)
load_dotenv()

#print(1/0) 오류 예시
# 전역 예외 처리기
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )

async def log_reader(n=5):
    log_lines = []
    LOGFILE = os.path.join(base_dir, log_file)
    with open(f"{LOGFILE}", "r") as file:
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
async def home(request:Request):
    try:
        data = await request.json()
        if data:
            return {"message": data}
    except Exception:
        pass

@app.get("/test")
async def test():
    return {"message": "Hello World"}

app.include_router(sapie_router)

# if __name__ == "__main__":        #.파일만 실행해도 서버가 실행되게
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000)

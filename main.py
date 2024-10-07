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
from models.logging_middleware import LoggingMiddleware
from fastapi.middleware.cors import CORSMiddleware
from saltware import router as saltware_router
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from starlette.websockets import WebSocketDisconnect
from kakaoBot import router as kakao_router
from logger_config import logger

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
    except WebSocketDisconnect:
        await websocket.close()
    # except Exception as e:
    #     print(e)
    # finally:
    #     await websocket.close()

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
@app.get("/test2")
async def test2():
    return {"message": "워크플로우 테스트"}

app.include_router(saltware_router)
app.include_router(kakao_router)

# if __name__ == "__main__":        #.파일만 실행해도 서버가 실행되게
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000)

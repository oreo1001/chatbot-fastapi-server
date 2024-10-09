from itertools import chain
import logging
import aiohttp
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
import httpx
import pytz
from pymongo import MongoClient
from models import connectionString
from models.kakao_model import KakaoService
from main import logger
from logger_config import logger

router = APIRouter(
    prefix="/kakao",
    tags=["kakao"],
    responses={404: {"description": "Not found"}}
)
korea_tz = pytz.timezone("Asia/Seoul")
dbClient = MongoClient(connectionString)
db = dbClient['kakao']
historyCollection = db["chat_histories"]

headers = {
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'text/event-stream'
}

def get_logger():
    return logger

@router.post("/callback")
async def get_request_async_callback(request: Request,background_tasks: BackgroundTasks, logger:logging.Logger=Depends(get_logger)):
    kakao_ai_request = await request.json()
    question = kakao_ai_request['userRequest']['utterance']
    session_id = kakao_ai_request['userRequest']['user']['id']
    callback_url = kakao_ai_request['userRequest']['callbackUrl']
    
    # if not session_id:
    #     return JSONResponse(content={"message": "잘못된 요청입니다."})
    # if not question:
    #     return JSONResponse(content={"message": "유효한 질문이 아닙니다."})
    background_tasks.add_task(get_message,
        question=question, session_id = session_id,callback_url=callback_url)
    return {"version": "2.0", "useCallback": True} 

async def get_message(question , session_id, callback_url):
    service = KakaoService()
    response_data = service.run_langchain_json(question=question, sessionId=session_id)
    #logger.info(response_data)
    
    # async with aiohttp.ClientSession() as session:
    #     async with session.post(callback_url, json=response_data) as response:
    #         if response.status == 200:
    #             print("Callback sent successfully")
    #         else:
    #             print("Failed to send callback:", response)

    async with httpx.AsyncClient() as client:
            request = client.build_request("POST", callback_url, json=response_data)
            # 기본 헤더 확인
            logger.info("Request Headers:", request.headers)
            response = await client.post(callback_url, json=response_data)
            if response.status_code == 200:
                print("Callback sent successfully")
            else:
                print(f"Failed to send callback: {response.status_code} - {response.text}")

@router.post("/test")
async def test(request: Request):
    kakao_ai_request = await request.json()
    question = kakao_ai_request['userRequest']['utterance']
    session_id = kakao_ai_request['userRequest']['user']['id']
    service = KakaoService()
    return service.run_langchain_test(question=question, sessionId=session_id)

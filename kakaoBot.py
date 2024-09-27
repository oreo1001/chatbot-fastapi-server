from itertools import chain
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import pytz
from pymongo import MongoClient
from models import connectionString
from models.saltware_model import SaltwareService

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

@router.post("/test")
async def test(request: Request):
    data = await request.json()
    return {"message":data}

@router.post("/getMessage")
async def get_message(request: Request):
    data = await request.json()
    question = data['userRequest']['utterance']
    session_id = data['userRequest']['user']['id']

    if not session_id:
        return JSONResponse(content={"message": "잘못된 요청입니다."})
    if not question:
        return JSONResponse(content={"message": "유효한 질문이 아닙니다."})
    service = SaltwareService()
    return service.run_langchain_json(question=question, sessionId=session_id)
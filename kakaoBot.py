from itertools import chain
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import pytz
from pymongo import MongoClient
from models import connectionString

router = APIRouter(
    prefix="/kakao",
    tags=["kakao"],
    responses={404: {"description": "Not found"}}
)
korea_tz = pytz.timezone("Asia/Seoul")
dbClient = MongoClient(connectionString)
db = dbClient['kakao']
historyCollection = db["chat_histories"]

@router.post("/test")
async def test(request: Request):
    data = await request.json()
    return {"message":data}
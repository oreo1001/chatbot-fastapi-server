from itertools import chain
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import pytz
from models.saltware_model import SaltwareService
from pymongo import MongoClient
from models import connectionString

router = APIRouter(
    prefix="/saltware",
    tags=["saltware"],
    responses={404: {"description": "Not found"}}
)
korea_tz = pytz.timezone("Asia/Seoul")
dbClient = MongoClient(connectionString)
db = dbClient['saltware']
historyCollection = db["chat_histories"]

headers = {
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'text/event-stream'
}

@router.get("/messages")
async def get_message(session_id: str, question: str):
    def error1():
            yield 'message: No session_id provided'
    def error2():
        yield 'Question not found'

    if not session_id:
        return StreamingResponse(error1(),headers = headers,media_type='text/event-stream')
    if not question:
        return StreamingResponse(error2(),headers = headers,media_type='text/event-stream')
    service = SaltwareService()
    return service.run_langchain_stream(question=question, sessionId=session_id)

@router.delete("/messages")
async def delete_message(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    chatHistory = historyCollection.find_one({"SessionId": session_id})
    historyCollection.delete_many({"SessionId":session_id})

    if chatHistory:
        message = "Session store and question list initialized"
    else:
        message = "Session not found"
    return JSONResponse(content={"message": message})

@router.post("/messageList")
async def post_message_list(request: Request):
    data = await request.json()
    sessionId = data.get("session_id")
    chatHistories = historyCollection.find(
            {"SessionId": sessionId},
            {"History": 1, "_id": 0}  # History 필드만 가져오고 _id 필드는 제외
        )
    messageList=[]
    all_histories = chain.from_iterable(chatHistory.get('History', []) for chatHistory in chatHistories)
    for history in all_histories:
        speaker = history['type']
        content = history['data']['content']
        url_list = history.get('data', {}).get('response_metadata', {}).get('url_list', []) #없으면 []
        message = {
            "speaker": speaker,
            "content": content,
            "url_list": url_list
        }
        messageList.append(message)
    return JSONResponse(content={"messageList": messageList})
######################################################################################

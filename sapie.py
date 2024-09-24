from itertools import chain
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import pytz
# from custom_mongo_chat import CustomMongoDBChatHistory
# from langchain_core.runnables.history import RunnableWithMessageHistory
from sapie_model import SapieService
# from langchain_core.runnables import RunnableLambda

router = APIRouter(
    prefix="/sapie",
    tags=["sapie"],
    responses={404: {"description": "Not found"}}
)
korea_tz = pytz.timezone("Asia/Seoul")
from pymongo import MongoClient

#connectionString = "mongodb://dba:20240731@localhost:11084/"
connectionString = "mongodb://localhost:27017/"
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
    service = SapieService()
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
    messageList.append(message)
    return JSONResponse(content={"msList": messageList})


@router.post("/urlList")
async def post_message_list(request: Request):
        sessionId = request.json.get("session_id")
        print(sessionId)
        historyDB = historyCollection.find_one(
                {"SessionId": sessionId},
                {"History": {"$slice": -1}}  # History 배열의 마지막 항목만 가져옴
            )
        print(historyDB) 
        if historyDB==None:
            return {"url_list":[]}
        return {"url_list":historyDB['History'][0]['data']['response_metadata']['url_list']} 
######################################################################################

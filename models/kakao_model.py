import json
import boto3
from fastapi.responses import JSONResponse, StreamingResponse
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain_community.vectorstores import FAISS
from langchain_aws import ChatBedrock
from langchain_community.embeddings import BedrockEmbeddings
from pymongo import MongoClient

from models.custom_mongo_chat import CustomMongoDBChatHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda
from dotenv import load_dotenv
from models import connectionString

dbClient = MongoClient(connectionString)
db = dbClient['kakao']
historyCollection = db["chat_histories"]

headers = {
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'text/event-stream'
}

class KakaoService:
    def __init__(self):
        load_dotenv()
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1",
        )

        model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        model_kwargs = {
            "temperature": 0.0,
            "top_k": 0,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman"],
        }

        self.llm = ChatBedrock(
            client=self.bedrock_runtime,
            model_id=model_id,
            model_kwargs=model_kwargs,
        )

        embeddings_model = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=self.bedrock_runtime)
        self.vectorstore = FAISS.load_local('./merged_db/faiss', embeddings_model, allow_dangerous_deserialization=True)
        self.retriever = self.vectorstore.as_retriever()

        qa_system_prompt = """You are an assistant for question-answering tasks. \
        Use the following pieces of retrieved html formed table context to answer the question. \
        If you don't know the answer, just say "문서에 없는 내용입니다. 다시 질문해주세요." \
        Answer correctly using given context.
        {context}"""

        self.qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}")
            ]
        )

        self.question_answer_chain = create_stuff_documents_chain(self.llm, self.qa_prompt)
        self.salt_rag_chain = create_retrieval_chain(self.retriever, self.question_answer_chain)
    def get_chain(self):
        return self.salt_rag_chain
        
    def run_langchain_json(self,question, sessionId):
        conversational_rag_chain = RunnableWithMessageHistory(
            self.get_chain(),
            lambda session_id: CustomMongoDBChatHistory(
                session_id=session_id,
                connection_string=connectionString,
                database_name="kakao",
                collection_name="chat_histories",
            ),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        try:
            chat_invoke = conversational_rag_chain.invoke(
                {"input": question},
                config={"configurable": {"session_id": sessionId}},
            )
            payload = {
                "answer": {
                    "status": "normal",
                    "sentence": chat_invoke['answer'],
                    "dialog":"reply"
                }
            }
            return JSONResponse(content=payload, headers={"Content-Type": "application/json"})
        except Exception as e:
            payload = {
                "answer": {
                    "status": "error",
                    "sentence": f"Error: {str(e)}",
                    "dialog":"finish"
                }
            }
            return JSONResponse(content=payload, headers={"Content-Type": "application/json"})
        
    def run_langchain_test(self,question, sessionId):
        conversational_rag_chain = RunnableWithMessageHistory(
            self.get_chain(),
            lambda session_id: CustomMongoDBChatHistory(
                session_id=session_id,
                connection_string=connectionString,
                database_name="kakao",
                collection_name="chat_histories",
            ),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        try:
            chat_invoke = conversational_rag_chain.invoke(
                {"input": question},
                config={"configurable": {"session_id": sessionId}},
            )
            payload = {
                "answer": {
                    "status": "normal",
                    "sentence": chat_invoke['answer'],
                    "dialog":"finish"
                }
            }
            return JSONResponse(content=payload, headers={"Content-Type": "application/json"})
        except Exception as e:
            payload = {
                "answer": {
                    "status": "error",
                    "sentence": f"Error: {str(e)}",
                    "dialog":"finish"
                }
            }
            return JSONResponse(content=payload, headers={"Content-Type": "application/json"})
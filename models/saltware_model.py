import json
import boto3
from fastapi.responses import StreamingResponse
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

connectionString = "mongodb://localhost:27017/"
dbClient = MongoClient(connectionString)
db = dbClient['saltware']
historyCollection = db["chat_histories"]

headers = {
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'text/event-stream'
}

class SaltwareService:
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
            streaming=True,  # 스트리밍으로 답변을 받기 위한 설정
            callbacks=[StreamingStdOutCallbackHandler()]  # 스트리밍으로 답변을 받기 위한 콜백
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
    
    def get_response(self,chain, prompt, config, sessionId):
        url_list = []
        
        # stream으로 데이터를 받아오면서 URL과 응답 처리 통합
        for chunk in chain.stream({"input": prompt}, config):
            # 문서가 포함된 context에서 URL을 추출
            if 'context' in chunk:
                for document in chunk['context']:
                    s3_url = document.metadata.get('s3_url')
                    source_file = document.metadata.get('source_file')
                    doc_info = {"s3_url": s3_url, "source_file": source_file}
                    if s3_url and not any(doc['s3_url'] == s3_url for doc in url_list):
                        url_list.append(doc_info)
            
            # 답변이 포함된 경우, 스트리밍 응답 전송
            if 'answer' in chunk:
                response_replaced = chunk['answer'].replace('\n', '🖐️')
                yield f"data: {response_replaced}\n\n"
                # time.sleep(0.001)  # 필요한 경우에만 사용
        history_db = historyCollection.find_one(
            {"SessionId": sessionId},
            {"History": {"$slice": -1}}  # History 배열의 마지막 항목만 가져옴
        )
        if  history_db and "History" in  history_db and len(history_db["History"]) > 0:
            recent_history = history_db["History"][0]
            historyCollection.update_one(
                {"SessionId": sessionId, "History": recent_history},
                {"$set": {"History.$.data.response_metadata": {"url_list":url_list}}}  # response_metadata 업데이트
            )
        final_data = {"url_list": url_list}
        yield f"event: data_event\ndata: {json.dumps(final_data)}\n\n"
        yield 'data: \u200C\n\n'
    
    def run_langchain_stream(self,question, sessionId):
        conversational_rag_chain = RunnableWithMessageHistory(
            self.get_chain(),
            lambda session_id: CustomMongoDBChatHistory(
                session_id=session_id,
                connection_string=connectionString,
                database_name="saltware",
                collection_name="chat_histories",
            ),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        try:
            config = {"configurable": {"session_id": sessionId}}
            # 스트리밍 응답을 직접 처리
            return StreamingResponse(self.get_response(conversational_rag_chain, question, config, sessionId),
                            headers=headers,
                            media_type='text/event-stream')
        except Exception as e:
            return StreamingResponse(f"data: Error: {str(e)}\n\n", media_type='text/event-stream')
        
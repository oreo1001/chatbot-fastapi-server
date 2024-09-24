import logging
from typing import List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    message_to_dict,
    messages_from_dict,
)
from pymongo import MongoClient, errors

logger = logging.getLogger(__name__)

DEFAULT_DBNAME = "chat_history"
DEFAULT_COLLECTION_NAME = "message_store"


class CustomMongoDBChatHistory(BaseChatMessageHistory):
    """Chat message history that stores history in MongoDB.

    Args:
        connection_string: connection string to connect to MongoDB
        session_id: arbitrary key that is used to store the messages
            of a single chat session.
        database_name: name of the database to use
        collection_name: name of the collection to use
    """

    def __init__(
        self,
        connection_string: str,
        session_id: str,
        database_name: str = DEFAULT_DBNAME,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ):
        self.connection_string = connection_string
        self.session_id = session_id
        self.database_name = database_name
        self.collection_name = collection_name

        try:
            self.client: MongoClient = MongoClient(connection_string)
        except errors.ConnectionFailure as error:
            logger.error(error)

        self.db = self.client[database_name]
        self.collection = self.db[collection_name]
        self.collection.create_index("SessionId")

    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve the messages from MongoDB"""
        try:
            cursor = self.collection.find({"SessionId": self.session_id})
        except errors.OperationFailure as error:
            logger.error(error)
            return []

        items = []
        if cursor:
            for document in cursor:
                history_list = document.get("History")  # History는 리스트 형태로 저장됨
                if history_list:
                    # History 리스트에서 각 메시지를 items에 추가
                    for history in history_list:
                        items.append(history)
    
        messages = messages_from_dict(items)
        return messages

    def add_message(self, message: BaseMessage,response_metadata: dict = None) -> None:
        """Append the message to the record in MongoDB"""
        try:
            message_dict = message_to_dict(message)
            
            self.collection.update_one(
                {"SessionId": self.session_id},  # 세션 ID로 문서 찾기
                {
                    "$push": {"History": message_dict}  # History 리스트에 새 메시지 추가
                },
                upsert=True  # 문서가 없으면 새로 생성
            )
        except errors.WriteError as err:
            logger.error(err)

    def clear(self) -> None:
        """Clear session memory from MongoDB"""
        try:
            self.collection.delete_many({"SessionId": self.session_id})
        except errors.WriteError as err:
            logger.error(err)
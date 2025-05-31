from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import os
from dotenv import load_dotenv

load_dotenv()

class MongoDB:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("DB_NAME")]
        self.users = self.db.users
        self.conversations = self.db.conversations
    
    def get_user(self, email: str) -> dict:
        """Retrieve user by email or create if doesn't exist"""
        try:
            user = self.users.find_one({"email": email})
            if not user:
                user = {"email": email, "created_at": datetime.utcnow()}
                self.users.insert_one(user)
            return user
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return None
    
    def create_conversation(self, email: str, title: str = "New Conversation") -> str:
        """Create a new conversation for user"""
        try:
            conversation = {
                "user_email": email,
                "title": title,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "messages": []
            }
            result = self.conversations.insert_one(conversation)
            return str(result.inserted_id)
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return None
    
    def add_message(self, conversation_id: str, role: str, content: str) -> bool:
        """Add a message to conversation"""
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow()
            }
            self.conversations.update_one(
                {"_id": conversation_id},
                {"$push": {"messages": message}, "$set": {"updated_at": datetime.utcnow()}}
            )
            return True
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return False
    
    def get_user_conversations(self, email: str) -> list:
        """Get all conversations for a user"""
        try:
            return list(self.conversations.find(
                {"user_email": email},
                {"title": 1, "created_at": 1, "updated_at": 1}
            ).sort("updated_at", -1))
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []
    
    def get_conversation_messages(self, conversation_id: str) -> list:
        """Get all messages for a conversation"""
        try:
            conv = self.conversations.find_one(
                {"_id": conversation_id},
                {"messages": 1}
            )
            return conv.get("messages", []) if conv else []
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []

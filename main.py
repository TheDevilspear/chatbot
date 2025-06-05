from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from ai21 import AI21Client
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
client = MongoClient(os.getenv("MONGO_URL"), tls=True, tlsAllowInvalidCertificates=False)
db = client["jamba_chatbot"]

# Models
class Message(BaseModel):
    role: str
    content: str

class Conversation(BaseModel):
    user_email: str
    title: str
    messages: List[Message]

@app.post("/conversations/")
def create_conversation(email: str):
    conversation = {
        "user_email": email,
        "title": "New Conversation",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "messages": []
    }
    result = db.conversations.insert_one(conversation)
    return {"conversation_id": str(result.inserted_id)}

@app.post("/conversations/{conversation_id}/messages")
def add_message(conversation_id: str, message: Message):
    message_data = {
        "role": message.role,
        "content": message.content,
        "timestamp": datetime.utcnow()
    }
    db.conversations.update_one(
        {"_id": conversation_id},
        {"$push": {"messages": message_data}, "$set": {"updated_at": datetime.utcnow()}}
    )
    return {"status": "success"}

@app.post("/chat")
def chat_with_jamba(email: str, conversation_id: str, message: str):
    # Your existing Jamba chat logic here
    ai21_client = AI21Client(api_key=os.getenv("AI21_API_KEY"))
    
    # Get conversation history
    conv = db.conversations.find_one({"_id": conversation_id})
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in conv["messages"]]
    
    # Add new user message
    messages.append({"role": "user", "content": message})
    
    # Get AI response
    response = ai21_client.chat.completions.create(
        model="jamba-mini",
        messages=messages,
        max_tokens=150,
        temperature=0.7
    )
    
    assistant_reply = response.choices[0].message.content
    
    # Save both messages to DB
    db.conversations.update_one(
        {"_id": conversation_id},
        {
            "$push": {
                "messages": [
                    {"role": "user", "content": message, "timestamp": datetime.utcnow()},
                    {"role": "assistant", "content": assistant_reply, "timestamp": datetime.utcnow()}
                ]
            },
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {"response": assistant_reply}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

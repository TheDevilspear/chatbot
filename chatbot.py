import os
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from ai21 import AI21Client
from ai21.models.chat import ChatMessage, SystemMessage, UserMessage, AssistantMessage
from db.mongo import MongoDB

load_dotenv()

class JambaChat:
    def __init__(self, email: str, conversation_id: Optional[str] = None):
        self.email = email
        self.db = MongoDB()
        self.client = AI21Client(api_key=os.getenv("AI21_API_KEY"))
        self.model = "jamba-instruct"
        
        # Initialize or load conversation
        if conversation_id:
            self.conversation_id = conversation_id
            self.messages = self._load_conversation()
        else:
            self.conversation_id = self.db.create_conversation(email)
            self.messages = [SystemMessage(content="You're a helpful assistant.")]
    
    def _load_conversation(self) -> List[ChatMessage]:
        """Load conversation messages from DB"""
        db_messages = self.db.get_conversation_messages(self.conversation_id)
        messages = []
        
        for msg in db_messages:
            if msg["role"] == "system":
                messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                messages.append(UserMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AssistantMessage(content=msg["content"]))
        
        return messages
    
    def chat(self, user_input: str, max_tokens: int = 150, temperature: float = 0.7) -> str:
        """Process user input and return AI response"""
        # Add user message to history
        user_msg = UserMessage(content=user_input)
        self.messages.append(user_msg)
        self.db.add_message(self.conversation_id, "user", user_input)
        
        # Get AI response
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Add AI response to history
        assistant_reply = response.choices[0].message.content
        assistant_msg = AssistantMessage(content=assistant_reply)
        self.messages.append(assistant_msg)
        self.db.add_message(self.conversation_id, "assistant", assistant_reply)
        
        return assistant_reply
    
    def get_conversation_title(self) -> str:
        """Get the title of current conversation"""
        conv = self.db.conversations.find_one(
            {"_id": self.conversation_id},
            {"title": 1}
        )
        return conv.get("title", "Untitled Conversation") if conv else "Untitled Conversation"
    
    def rename_conversation(self, new_title: str) -> bool:
        """Change conversation title"""
        try:
            self.db.conversations.update_one(
                {"_id": self.conversation_id},
                {"$set": {"title": new_title}}
            )
            return True
        except Exception as e:
            print(f"Error renaming conversation: {e}")
            return False

class ChatManager:
    def __init__(self):
        self.db = MongoDB()
    
    def start_new_chat(self, email: str) -> JambaChat:
        """Initialize a new chat session"""
        return JambaChat(email)
    
    def resume_chat(self, email: str, conversation_id: str) -> JambaChat:
        """Resume an existing conversation"""
        return JambaChat(email, conversation_id)
    
    def get_user_conversations(self, email: str) -> list:
        """Get list of user's conversations"""
        return self.db.get_user_conversations(email)

def main():
    print("Welcome to Jamba Chatbot!")
    email = input("Enter your email: ").strip().lower()
    
    manager = ChatManager()
    conversations = manager.get_user_conversations(email)
    
    if conversations:
        print("\nYour conversations:")
        for i, conv in enumerate(conversations, 1):
            print(f"{i}. {conv['title']} ({conv['created_at'].strftime('%Y-%m-%d')})")
        
        choice = input("\nEnter number to resume or 'n' for new: ")
        if choice.isdigit() and 0 < int(choice) <= len(conversations):
            chat = manager.resume_chat(email, conversations[int(choice)-1]["_id"])
        else:
            chat = manager.start_new_chat(email)
    else:
        chat = manager.start_new_chat(email)
    
    print(f"\nChat started (Conversation: {chat.get_conversation_title()})")
    print("Type 'quit' to end, 'rename' to change title\n")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            print("\nChat ended. Goodbye!")
            break
        elif user_input.lower().startswith('rename '):
            new_title = user_input[7:].strip()
            if chat.rename_conversation(new_title):
                print(f"Conversation renamed to: {new_title}")
            else:
                print("Failed to rename conversation")
        else:
            response = chat.chat(user_input)
            print(f"Assistant: {response}")

if __name__ == "__main__":
    main()

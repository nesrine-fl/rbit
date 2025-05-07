from sqlalchemy.orm import Session
from models.message import Message
from typing import List
from fastapi import UploadFile
import os
from datetime import datetime

def save_message_file(file: UploadFile, message_id: int) -> tuple[str, str]:
    # Create messages directory if it doesn't exist
    messages_dir = "uploads/messages"
    if not os.path.exists(messages_dir):
        os.makedirs(messages_dir)
    
    # Create message-specific directory
    message_dir = os.path.join(messages_dir, str(message_id))
    if not os.path.exists(message_dir):
        os.makedirs(message_dir)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(message_dir, unique_filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    return file_path, file.content_type

def create_message(
    db: Session,
    sender_id: int,
    receiver_id: int,
    content: str,
    file: UploadFile = None
) -> Message:
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # If file is provided, save it
    if file:
        file_path, file_type = save_message_file(file, message.id)
        message.file_path = file_path
        message.file_type = file_type
        db.commit()
        db.refresh(message)
    
    return message

def get_user_messages(
    db: Session,
    user_id: int,
    message_type: str = "received",  # "received" or "sent"
    skip: int = 0,
    limit: int = 100
) -> List[Message]:
    query = db.query(Message)
    
    if message_type == "received":
        query = query.filter(Message.receiver_id == user_id)
    else:  # sent
        query = query.filter(Message.sender_id == user_id)
    
    return query.order_by(Message.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_message(
    db: Session,
    message_id: int,
    user_id: int
) -> Message:
    message = db.query(Message)\
        .filter(
            Message.id == message_id,
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        )\
        .first()
    
    if message and message.receiver_id == user_id and not message.is_read:
        message.is_read = True
        db.commit()
        db.refresh(message)
    
    return message

def mark_message_as_read(
    db: Session,
    message_id: int,
    user_id: int
) -> Message:
    message = db.query(Message)\
        .filter(
            Message.id == message_id,
            Message.receiver_id == user_id
        )\
        .first()
    
    if message:
        message.is_read = True
        db.commit()
        db.refresh(message)
    
    return message

def delete_message(
    db: Session,
    message_id: int,
    user_id: int
) -> bool:
    message = db.query(Message)\
        .filter(
            Message.id == message_id,
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        )\
        .first()
    
    if message:
        # Delete associated file if exists
        if message.file_path and os.path.exists(message.file_path):
            os.remove(message.file_path)
            # Remove directory if empty
            message_dir = os.path.dirname(message.file_path)
            if not os.listdir(message_dir):
                os.rmdir(message_dir)
        
        db.delete(message)
        db.commit()
        return True
    
    return False 
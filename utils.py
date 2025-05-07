import os
import shutil
from fastapi import UploadFile
from datetime import datetime

UPLOAD_DIR = "uploads"

def ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def save_uploaded_file(file: UploadFile, course_id: int) -> str:
    ensure_upload_dir()
    
    # Create course-specific directory
    course_dir = os.path.join(UPLOAD_DIR, str(course_id))
    if not os.path.exists(course_dir):
        os.makedirs(course_dir)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(course_dir, unique_filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path 
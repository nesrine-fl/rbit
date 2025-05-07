from pydantic import BaseModel, EmailStr, constr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    nom: str
    prenom: str
    departement: Optional[str] = None
    role: str
    email: EmailStr
    telephone: str

class UserCreate(UserBase):
    password: str
    confirm_password: str

class User(UserBase):
    id: int
    is_active: bool
    is_approved: bool

    class Config:
        from_attributes = True

class UserApproval(BaseModel):
    is_approved: bool

class PendingUser(User):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Course schemas
class CourseBase(BaseModel):
    title: str
    description: str
    departement: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseMaterialBase(BaseModel):
    file_name: str
    file_type: str

class CourseMaterialCreate(CourseMaterialBase):
    pass

class CourseMaterial(CourseMaterialBase):
    id: int
    course_id: int
    file_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class Course(CourseBase):
    id: int
    instructor_id: int
    created_at: datetime
    updated_at: datetime
    materials: List[CourseMaterial] = []

    class Config:
        from_attributes = True

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    related_course_id: Optional[int] = None
    related_material_id: Optional[int] = None

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str
    receiver_id: int

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    sender_id: int
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class MessageInDB(Message):
    sender: User
    receiver: User

    class Config:
        from_attributes = True 
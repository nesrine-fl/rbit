from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(Text)
    type = Column(String)  # course_created, course_deleted, material_added, etc.
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    related_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    related_material_id = Column(Integer, ForeignKey("course_materials.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    course = relationship("Course", back_populates="notifications")
    material = relationship("CourseMaterial", back_populates="notifications") 
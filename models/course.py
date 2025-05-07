from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .user import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    instructor_id = Column(Integer, ForeignKey("users.id"))
    departement = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with User
    instructor = relationship("User", back_populates="courses")
    
    # Course materials will be stored as files in a directory
    # We'll store the file paths in the database
    materials = relationship("CourseMaterial", back_populates="course")
    progress_records = relationship("CourseProgress", back_populates="course")
    notifications = relationship("Notification", back_populates="course")

class CourseMaterial(Base):
    __tablename__ = "course_materials"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    file_name = Column(String)
    file_path = Column(String)
    file_type = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    course = relationship("Course", back_populates="materials")
    notifications = relationship("Notification", back_populates="material")

class CourseProgress(Base):
    __tablename__ = "course_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    progress = Column(Float, default=0)  # Progression en pourcentage (0-100)
    status = Column(String, default="En cours")  # En cours, Terminé, etc.
    start_date = Column(DateTime, default=datetime.utcnow)
    completion_date = Column(DateTime, nullable=True)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    is_completed = Column(Boolean, default=False)

    user = relationship("User", back_populates="course_progress")
    course = relationship("Course", back_populates="progress_records") 
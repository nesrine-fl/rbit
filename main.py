from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Annotated, List, Optional
import json
import os
from fastapi.responses import FileResponse

from database import get_db, engine
from models.user import User, Base
from models.course import Course, CourseMaterial, CourseProgress
from schemas import (
    UserCreate, User as UserSchema, Token,
    CourseCreate, Course as CourseSchema,
    CourseMaterial as CourseMaterialSchema,
    UserApproval, PendingUser, Notification,
    MessageCreate, MessageInDB
)
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM
)
from jose import JWTError, jwt
from utils import save_uploaded_file
from services.notification_service import (
    notify_course_created,
    notify_course_deleted,
    notify_material_added,
    notify_course_progress,
    get_user_notifications,
    mark_notification_as_read
)
from services.message_service import (
    create_message,
    get_user_messages,
    get_message,
    mark_message_as_read,
    delete_message
)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

# Middleware to check if user is a professor
def verify_professor(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.role != "prof":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only professors can perform this action"
        )
    return current_user

@app.post("/register", response_model=UserSchema)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if passwords match
    if user.password != user.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Check if email already exists
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        nom=user.nom,
        prenom=user.prenom,
        departement=user.departement,
        role=user.role,
        email=user.email,
        telephone=user.telephone,
        hashed_password=hashed_password,
        is_active=True,
        is_approved=False  # New users are not approved by default
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/admin/pending-users", response_model=List[PendingUser])
def get_pending_users(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can view pending users"
        )
    
    pending_users = db.query(User).filter(User.is_approved == False).all()
    return pending_users

@app.post("/admin/approve-user/{user_id}", response_model=UserSchema)
def approve_user(
    user_id: int,
    approval: UserApproval,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can approve users"
        )
    
    # Get the user to approve
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update approval status
    user.is_approved = approval.is_approved
    db.commit()
    db.refresh(user)
    return user


@app.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete users"
        )
    
    # Get the user to delete
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot delete their own account"
        )
    
    # Delete the user
    db.delete(user)
    db.commit()
    return None


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is approved
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not approved yet. Please wait for admin approval.",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Get user's course progress
    progress_records = db.query(CourseProgress).filter(
        CourseProgress.user_id == current_user.id
    ).all()
    
    # Calculate statistics
    total_courses = len(progress_records)
    completed_courses = sum(1 for p in progress_records if p.is_completed)
    average_progress = sum(p.progress for p in progress_records) / total_courses if total_courses > 0 else 0
    
    # Calculate average completion time for completed courses
    completion_times = [(p.completion_date - p.start_date).days 
                       for p in progress_records 
                       if p.is_completed and p.completion_date]
    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
    
    return {
        "profile": {
            "nom": current_user.nom,
            "prenom": current_user.prenom,
            "email": current_user.email,
            "telephone": current_user.telephone,
            "departement": current_user.departement,
            "fonction": current_user.role
        },
        "statistics": {
            "total_cours_suivis": total_courses,
            "cours_termines": completed_courses,
            "progression_moyenne": f"{average_progress:.1f}%",
            "temps_moyen_completion": f"{avg_completion_time:.1f} jours"
        },
        "courses": [
            {
                "nom_du_cours": progress.course.title,
                "progres": f"{progress.progress:.1f}%",
                "date_debut": progress.start_date.strftime("%d/%m/%Y"),
                "date_fin": progress.completion_date.strftime("%d/%m/%Y") if progress.completion_date else "En cours...",
                "dernier_acces": progress.last_accessed.strftime("%d/%m/%Y %H:%M"),
                "statut": progress.status,
                "duree": f"{(datetime.utcnow() - progress.start_date).days} jours"
            }
            for progress in progress_records
        ]
    }

# Course endpoints
@app.post("/courses/", response_model=CourseSchema)
def create_course(
    course: CourseCreate,
    current_user: Annotated[User, Depends(verify_professor)],
    db: Session = Depends(get_db)
):
    db_course = Course(
        title=course.title,
        description=course.description,
        instructor_id=current_user.id
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    
    # Notify admin about new course
    notify_course_created(db, db_course)
    
    return db_course

@app.get("/courses/", response_model=List[CourseSchema])
def get_courses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    courses = db.query(Course).offset(skip).limit(limit).all()
    return courses

@app.get("/courses/{course_id}", response_model=CourseSchema)
def get_course(
    course_id: int,
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.post("/courses/{course_id}/materials/", response_model=CourseMaterialSchema)
def upload_course_material(
    course_id: int,
    current_user: Annotated[User, Depends(verify_professor)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Verify course exists and user is the instructor
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload materials to your own courses"
        )
    
    # Save the file
    file_path = save_uploaded_file(file, course_id)
    
    # Create course material record
    db_material = CourseMaterial(
        course_id=course_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file.content_type
    )
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    
    # Notify admin and students about new material
    notify_material_added(db, course, db_material)
    
    return db_material

@app.get("/courses/{course_id}/materials/", response_model=List[CourseMaterialSchema])
def get_course_materials(
    course_id: int,
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course.materials

@app.post("/courses/{course_id}/enroll")
async def enroll_in_course(
    course_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if already enrolled
    existing_progress = db.query(CourseProgress).filter(
        CourseProgress.user_id == current_user.id,
        CourseProgress.course_id == course_id
    ).first()
    
    if existing_progress:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    
    # Create new progress record with enrollment date
    progress = CourseProgress(
        user_id=current_user.id,
        course_id=course_id,
        start_date=datetime.utcnow(),
        status="En cours",
        progress=0,
        is_completed=False
    )
    
    db.add(progress)
    db.commit()
    db.refresh(progress)
    
    return {
        "message": "Successfully enrolled in course",
        "enrollment_details": {
            "course_title": course.title,
            "enrollment_date": progress.start_date.strftime("%d/%m/%Y"),
            "status": progress.status
        }
    }

@app.put("/courses/{course_id}/complete")
async def mark_course_as_completed(
    course_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Get progress record
    progress = db.query(CourseProgress).filter(
        CourseProgress.user_id == current_user.id,
        CourseProgress.course_id == course_id
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")
    
    # Mark course as completed
    progress.is_completed = True
    progress.status = "Terminé"
    progress.completion_date = datetime.utcnow()
    progress.progress = 100
    
    db.commit()
    db.refresh(progress)
    
    return {
        "message": "Course marked as completed",
        "completion_details": {
            "course_title": progress.course.title,
            "completion_date": progress.completion_date.strftime("%d/%m/%Y"),
            "total_duration": f"{(progress.completion_date - progress.start_date).days} jours"
        }
    }

@app.get("/courses/{course_id}/progress")
async def get_course_progress(
    course_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    progress = db.query(CourseProgress).filter(
        CourseProgress.user_id == current_user.id,
        CourseProgress.course_id == course_id
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")
    
    return {
        "course_details": {
            "title": progress.course.title,
            "enrollment_date": progress.start_date.strftime("%d/%m/%Y"),
            "last_accessed": progress.last_accessed.strftime("%d/%m/%Y %H:%M"),
            "completion_date": progress.completion_date.strftime("%d/%m/%Y") if progress.completion_date else None,
            "progress": f"{progress.progress:.1f}%",
            "status": progress.status,
            "duration": f"{(datetime.utcnow() - progress.start_date).days} jours"
        }
    }

@app.put("/courses/{course_id}/progress")
async def update_course_progress(
    course_id: int,
    progress_value: float,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Get progress record
    progress = db.query(CourseProgress).filter(
        CourseProgress.user_id == current_user.id,
        CourseProgress.course_id == course_id
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")
    
    # Update progress
    progress.progress = min(100, max(0, progress_value))  # Ensure progress is between 0 and 100
    progress.last_accessed = datetime.utcnow()
    
    # Automatically mark as completed if progress reaches 100%
    if progress.progress >= 100 and not progress.is_completed:
        progress.is_completed = True
        progress.status = "Terminé"
        progress.completion_date = datetime.utcnow()
    
    db.commit()
    db.refresh(progress)
    
    # Notify student about progress update
    notify_course_progress(db, current_user.id, progress.course, progress.progress)
    
    return {
        "course_title": progress.course.title,
        "current_progress": f"{progress.progress:.1f}%",
        "status": progress.status,
        "last_updated": progress.last_accessed.strftime("%d/%m/%Y %H:%M")
    }

# Dashboard routes
@app.get("/dashboard/admin")
async def admin_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. admin role required."
        )
    
    # Get statistics for admin dashboard
    total_users = db.query(User).count()
    pending_users = db.query(User).filter(User.is_approved == False).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # Get pending users details
    pending_users_list = db.query(User).filter(User.is_approved == False).all()
    
    return {
        "statistics": {
            "total_users": total_users,
            "pending_users": pending_users,
            "active_users": active_users
        },
        "pending_users": [
            {
                "id": user.id,
                "nom": user.nom,
                "prenom": user.prenom,
                "email": user.email,
                "departement": user.departement,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in pending_users_list
        ]
    }

@app.get("/dashboard/prof")
async def prof_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    if current_user.role != "prof":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. professor role required."
        )
    
    # Get professor's courses and materials
    courses = db.query(Course).filter(Course.instructor_id == current_user.id).all()
    
    return {
        "user_info": {
            "nom": current_user.nom,
            "prenom": current_user.prenom,
            "email": current_user.email,
            "departement": current_user.departement
        },
        "courses": [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "created_at": course.created_at.isoformat() if course.created_at else None,
                "materials": [
                    {
                        "id": material.id,
                        "file_name": material.file_name,
                        "file_type": material.file_type,
                        "uploaded_at": material.uploaded_at.isoformat() if material.uploaded_at else None
                    }
                    for material in course.materials
                ]
            }
            for course in courses
        ]
    }

@app.get("/dashboard/employer")
async def employer_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. employer role required."
        )
    
    # Get all available courses
    courses = db.query(Course).all()
    
    return {
        "user_info": {
            "nom": current_user.nom,
            "prenom": current_user.prenom,
            "email": current_user.email,
            "departement": current_user.departement
        },
        "available_courses": [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "instructor": {
                    "nom": course.instructor.nom,
                    "prenom": course.instructor.prenom
                },
                "materials_count": len(course.materials)
            }
            for course in courses
        ]
    }

@app.put("/courses/{course_id}")
def update_course(
    course_id: int,
    course: CourseCreate,
    current_user: Annotated[User, Depends(verify_professor)],
    db: Session = Depends(get_db)
):
    # Get existing course
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Verify that the current user is the course instructor
    if db_course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own courses"
        )
    
    # Update course details
    db_course.title = course.title
    db_course.description = course.description
    db_course.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_course)
    return db_course

@app.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    current_user: Annotated[User, Depends(verify_professor)],
    db: Session = Depends(get_db)
):
    # Get existing course
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Verify that the current user is the course instructor
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own courses"
        )
    
    # Notify admin about course deletion
    notify_course_deleted(db, course)
    
    # Delete the course
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}

@app.delete("/courses/{course_id}/materials/{material_id}")
def delete_course_material(
    course_id: int,
    material_id: int,
    current_user: Annotated[User, Depends(verify_professor)],
    db: Session = Depends(get_db)
):
    # Get the material and verify it belongs to the specified course
    material = db.query(CourseMaterial).filter(
        CourseMaterial.id == material_id,
        CourseMaterial.course_id == course_id
    ).first()
    
    if material is None:
        raise HTTPException(status_code=404, detail="Course material not found")
    
    # Verify that the current user is the course instructor
    if material.course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete materials from your own courses"
        )
    
    # Delete the material
    db.delete(material)
    db.commit()
    return {"message": "Course material deleted successfully"}

@app.get("/notifications/", response_model=List[Notification])
def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    return get_user_notifications(db, current_user.id, skip, limit)

@app.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    notification = mark_notification_as_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@app.post("/messages/", response_model=MessageInDB)
async def send_message(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    content: str = Form(...),
    receiver_id: int = Form(...),
    file: Optional[UploadFile] = File(None)
):
    # Verify receiver exists
    receiver = db.query(User).filter(User.id == receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")
    
    return create_message(
        db=db,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content,
        file=file
    )

@app.get("/messages/", response_model=List[MessageInDB])
def get_messages(
    current_user: Annotated[User, Depends(get_current_user)],
    message_type: str = "received",
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    if message_type not in ["received", "sent"]:
        raise HTTPException(status_code=400, detail="Invalid message type")
    
    return get_user_messages(
        db=db,
        user_id=current_user.id,
        message_type=message_type,
        skip=skip,
        limit=limit
    )

@app.get("/messages/{message_id}", response_model=MessageInDB)
def read_message(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    message = get_message(db, message_id, current_user.id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

@app.put("/messages/{message_id}/read")
def mark_message_read(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    message = mark_message_as_read(db, message_id, current_user.id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message marked as read"}

@app.delete("/messages/{message_id}")
def remove_message(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    if not delete_message(db, message_id, current_user.id):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message deleted successfully"}

@app.get("/messages/file/{message_id}")
async def get_message_file(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    message = get_message(db, message_id, current_user.id)
    if not message or not message.file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(message.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        message.file_path,
        media_type=message.file_type,
        filename=os.path.basename(message.file_path)
    )

from sqlalchemy.orm import Session
from models.course import Course
from models.user import User
from typing import List, Optional

def get_courses(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 100
) -> List[Course]:
    query = db.query(Course)
    
    # Admin peut voir tous les cours
    if user.role == "admin":
        pass
    # Prof peut voir ses propres cours et ceux de son département
    elif user.role == "prof":
        query = query.filter(
            (Course.instructor_id == user.id) | 
            (Course.departement == user.departement)
        )
    # Employer ne peut voir que les cours de son département
    elif user.role == "employer":
        query = query.filter(Course.departement == user.departement)
    
    return query.order_by(Course.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_course(
    db: Session,
    course_id: int,
    user: User
) -> Optional[Course]:
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        return None
    
    # Vérifier les permissions
    if user.role == "admin":
        return course
    elif user.role == "prof" and (course.instructor_id == user.id or course.departement == user.departement):
        return course
    elif user.role == "employer" and course.departement == user.departement:
        return course
    
    return None

def create_course(
    db: Session,
    course_data: dict,
    instructor: User
) -> Course:
    course = Course(
        title=course_data["title"],
        description=course_data["description"],
        departement=instructor.departement,  # Le cours est créé dans le département du professeur
        instructor_id=instructor.id
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

def update_course(
    db: Session,
    course_id: int,
    course_data: dict,
    user: User
) -> Optional[Course]:
    course = get_course(db, course_id, user)
    if not course:
        return None
    
    # Seul le professeur qui a créé le cours peut le modifier
    if user.role != "admin" and course.instructor_id != user.id:
        return None
    
    for key, value in course_data.items():
        setattr(course, key, value)
    
    db.commit()
    db.refresh(course)
    return course

def delete_course(
    db: Session,
    course_id: int,
    user: User
) -> bool:
    course = get_course(db, course_id, user)
    if not course:
        return False
    
    # Seul l'admin ou le professeur qui a créé le cours peut le supprimer
    if user.role != "admin" and course.instructor_id != user.id:
        return False
    
    db.delete(course)
    db.commit()
    return True 
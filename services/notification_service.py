from sqlalchemy.orm import Session
from models.notification import Notification
from models.user import User
from models.course import Course
from typing import List

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str,
    course_id: int = None,
    material_id: int = None
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        related_course_id=course_id,
        related_material_id=material_id
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

def get_user_notifications(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Notification]:
    return db.query(Notification)\
        .filter(Notification.user_id == user_id)\
        .order_by(Notification.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

def mark_notification_as_read(
    db: Session,
    notification_id: int,
    user_id: int
) -> Notification:
    notification = db.query(Notification)\
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )\
        .first()
    
    if notification:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
    
    return notification

def notify_course_created(
    db: Session,
    course: Course
):
    # Notify admin
    admin = db.query(User).filter(User.role == "admin").first()
    if admin:
        create_notification(
            db=db,
            user_id=admin.id,
            title="Nouveau cours créé",
            message=f"Le cours '{course.title}' a été créé par {course.instructor.nom} {course.instructor.prenom}",
            type="course_created",
            course_id=course.id
        )

def notify_course_deleted(
    db: Session,
    course: Course
):
    # Notify admin
    admin = db.query(User).filter(User.role == "admin").first()
    if admin:
        create_notification(
            db=db,
            user_id=admin.id,
            title="Cours supprimé",
            message=f"Le cours '{course.title}' a été supprimé",
            type="course_deleted",
            course_id=course.id
        )

def notify_material_added(
    db: Session,
    course: Course,
    material
):
    # Notify admin
    admin = db.query(User).filter(User.role == "admin").first()
    if admin:
        create_notification(
            db=db,
            user_id=admin.id,
            title="Nouveau matériel ajouté",
            message=f"Un nouveau matériel a été ajouté au cours '{course.title}'",
            type="material_added",
            course_id=course.id,
            material_id=material.id
        )
    
    # Notify enrolled students
    for progress in course.progress_records:
        create_notification(
            db=db,
            user_id=progress.user_id,
            title="Nouveau matériel disponible",
            message=f"Un nouveau matériel est disponible dans le cours '{course.title}'",
            type="material_added",
            course_id=course.id,
            material_id=material.id
        )

def notify_course_progress(
    db: Session,
    user_id: int,
    course: Course,
    progress: float
):
    create_notification(
        db=db,
        user_id=user_id,
        title="Progression mise à jour",
        message=f"Votre progression dans le cours '{course.title}' est maintenant de {progress}%",
        type="progress_updated",
        course_id=course.id
    ) 
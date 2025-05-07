from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User
from auth import get_password_hash

# Create all tables
Base.metadata.create_all(bind=engine)

def create_admin_user():
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if admin:
            print("Admin user already exists")
            return

        # Create admin user
        admin_user = User(
            nom="Admin",
            prenom="System",
            departement="Administration",
            role="admin",
            email="admin@gig.dz",
            telephone="0000000000",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_approved=True
        )
        
        db.add(admin_user)
        db.commit()
        print("Admin user created successfully")
        
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user() 
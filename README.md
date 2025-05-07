# GIG Algeria E-Learning Platform

A comprehensive e-learning platform for GIG Algeria, designed to manage courses, training materials, and employee progress. Built with FastAPI, SQLAlchemy, and modern web technologies.

## Features

### User Management
- Role-based access control (Admin, Professor, Employer)
- User registration and approval system
- Secure authentication with JWT tokens
- Profile management

### Course Management
- Create, read, update, and delete training courses
- Role-based course access:
  - Admins: Full access to all courses
  - Professors: Access to their own courses and departmental courses
  - Employers: Access to departmental courses only
- Training materials upload and management
- Course progress tracking

### Communication
- Internal messaging system
- File attachments in messages
- Notification system for:
  - New course creation
  - Training material updates
  - Course progress updates
  - Course deletion

### Dashboard
- Role-specific dashboards:
  - Admin Dashboard: User management, system overview
  - Professor Dashboard: Course management, employee progress
  - Employer Dashboard: Course browsing, employee tracking

## API Endpoints

### Authentication
- `POST /register` - Register a new user
- `POST /token` - Login and get access token
- `GET /users/me` - Get current user profile

### Admin Endpoints
- `GET /admin/pending-users` - View pending user approvals
- `POST /admin/approve-user/{user_id}` - Approve/reject users
- `DELETE /admin/users/{user_id}` - Delete users

### Course Endpoints
- `GET /courses/` - List courses (filtered by role)
- `GET /courses/{course_id}` - Get course details
- `POST /courses/` - Create new course (professors only)
- `PUT /courses/{course_id}` - Update course
- `DELETE /courses/{course_id}` - Delete course
- `POST /courses/{course_id}/materials/` - Upload training material
- `GET /courses/{course_id}/materials/` - List course materials
- `POST /courses/{course_id}/enroll` - Enroll in a course
- `PUT /courses/{course_id}/complete` - Mark course as completed
- `GET /courses/{course_id}/progress` - Get course progress
- `PUT /courses/{course_id}/progress` - Update course progress

### Communication Endpoints
- `GET /notifications/` - Get user notifications
- `PUT /notifications/{notification_id}/read` - Mark notification as read
- `POST /messages/` - Send message
- `GET /messages/` - Get messages (received/sent)
- `GET /messages/{message_id}` - Get message details
- `PUT /messages/{message_id}/read` - Mark message as read
- `DELETE /messages/{message_id}` - Delete message
- `GET /messages/file/{message_id}` - Download message attachment

### Dashboard Endpoints
- `GET /dashboard/admin` - Admin dashboard
- `GET /dashboard/prof` - Professor dashboard
- `GET /dashboard/employer` - Employer dashboard

## Database Schema

### Users
- id (Primary Key)
- nom
- prenom
- departement
- role (admin/prof/employer)
- email
- telephone
- hashed_password
- is_active
- is_approved
- created_at

### Courses
- id (Primary Key)
- title
- description
- instructor_id (Foreign Key)
- departement
- created_at
- updated_at

### Course Materials
- id (Primary Key)
- course_id (Foreign Key)
- file_name
- file_path
- file_type
- uploaded_at

### Course Progress
- id (Primary Key)
- user_id (Foreign Key)
- course_id (Foreign Key)
- progress
- status
- start_date
- completion_date
- last_accessed
- is_completed

### Notifications
- id (Primary Key)
- user_id (Foreign Key)
- title
- message
- type
- is_read
- created_at
- related_course_id
- related_material_id

### Messages
- id (Primary Key)
- sender_id (Foreign Key)
- receiver_id (Foreign Key)
- content
- file_path
- file_type
- is_read
- created_at

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
5. Initialize the database:
   ```bash
   python init_db.py
   ```
6. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

## Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- File upload security
- Input validation
- SQL injection prevention
- XSS protection

## Error Handling

The application includes comprehensive error handling for:
- Authentication failures
- Authorization violations
- Invalid inputs
- Database errors
- File operations
- API rate limiting

## Testing

To run tests:
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
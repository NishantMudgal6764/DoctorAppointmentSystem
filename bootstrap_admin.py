
import os
from app import app
from models import db, User

with app.app_context():
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    name = os.environ.get("ADMIN_NAME", "Nishant Mudgal").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")

    if not email or not password:
        raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD are required.")

    if len(password) < 8:
        raise ValueError("Admin password must be at least 8 characters.")

    existing = User.query.filter_by(email=email).first()

    if existing:
        if existing.role != "admin":
            raise ValueError("This email already belongs to another role.")
        print("Admin account already exists.")
    else:
        admin = User(name=name, email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print("Online Admin account created successfully!")

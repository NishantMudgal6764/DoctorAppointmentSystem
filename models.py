from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ---------------- Doctor Table ---------------- #
class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    available_days = db.Column(db.String(100), nullable=False)
    available_time = db.Column(db.String(100), nullable=False)
    appointments = db.relationship("Appointment", backref="doctor", lazy=True)

# ---------------- Patient Table ---------------- #
class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(250), nullable=False)

    appointments = db.relationship("Appointment", backref="patient", lazy=True)

# ---------------- Appointment Table ---------------- #
class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id"),
        nullable=False
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False
    )

    appointment_date = db.Column(db.String(30), nullable=False)
    appointment_time = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), default="Pending")
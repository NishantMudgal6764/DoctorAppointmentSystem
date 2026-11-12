
import os
import secrets
from functools import wraps

import click
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from models import db, User, Doctor, Patient, Appointment


# ---------------- APPLICATION SETUP ---------------- #

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "doctor-appointment-development-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hospital.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ---------------- DATABASE AND ADMIN SETUP ---------------- #

def setup_database_and_admin():
    db.create_all()

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    admin_name = os.environ.get("ADMIN_NAME", "Administrator")

    if not admin_email or not admin_password:
        print("Admin environment variables are not configured.")
        return

    if len(admin_password) < 8:
        print("ADMIN_PASSWORD must contain at least 8 characters.")
        return

    existing_user = User.query.filter_by(email=admin_email).first()

    if existing_user:
        if existing_user.role != "admin":
            print("Admin setup stopped: email belongs to a non-admin account.")
            return

        existing_user.name = admin_name
        existing_user.set_password(admin_password)
        db.session.commit()

        print("Render Admin account password synchronized.")
        return

    admin = User(
        name=admin_name,
        email=admin_email,
        role="admin"
    )

    admin.set_password(admin_password)

    db.session.add(admin)
    db.session.commit()

    print("Render Admin account created successfully!")


with app.app_context():
    setup_database_and_admin()


# ---------------- LOGIN HELPERS ---------------- #

def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not get_current_user():
            flash("Please login first.", "warning")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            user = get_current_user()

            if not user:
                flash("Please login first.", "warning")
                return redirect(url_for("login"))

            if user.role not in roles:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("home"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


def redirect_by_role(user):
    if user.role == "admin":
        return redirect(url_for("dashboard"))

    if user.role == "doctor":
        return redirect(url_for("doctor_dashboard"))

    if user.role == "patient":
        return redirect(url_for("patient_dashboard"))

    return redirect(url_for("login"))


# ---------------- HOME PAGE ---------------- #

@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html")


# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "").strip().lower()

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            if selected_role and selected_role != user.role:
                flash("Please select the correct login role.", "danger")
                return redirect(url_for("login"))

            session.clear()
            session["user_id"] = user.id

            flash("Login successful!", "success")
            return redirect_by_role(user)

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# ---------------- PATIENT REGISTRATION ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        age = request.form.get("age", "")
        gender = request.form.get("gender", "")
        phone = request.form.get("phone", "")
        address = request.form.get("address", "")

        if not all([name, email, password, age, gender, phone, address]):
            flash("Please fill all the fields.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("This email is already registered.", "danger")
            return redirect(url_for("register"))

        try:
            age = int(age)
            if age < 1 or age > 120:
                raise ValueError
        except ValueError:
            flash("Please enter a valid age.", "danger")
            return redirect(url_for("register"))

        patient = Patient(
            name=name,
            age=age,
            gender=gender,
            phone=phone,
            address=address
        )

        db.session.add(patient)
        db.session.flush()

        user = User(
            name=name,
            email=email,
            role="patient",
            patient_id=patient.id
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------- ADMIN DASHBOARD ---------------- #

@app.route("/dashboard")
@role_required("admin")
def dashboard():

    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()

    pending_appointments = Appointment.query.filter_by(
        status="Pending"
    ).count()

    return render_template(
        "dashboard.html",
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        pending_appointments=pending_appointments
    )


# ---------------- DOCTOR MANAGEMENT ---------------- #

@app.route("/doctors")
@role_required("admin")
def doctors():

    all_doctors = Doctor.query.order_by(Doctor.id.desc()).all()

    return render_template("doctors.html", doctors=all_doctors)


@app.route("/add-doctor", methods=["GET", "POST"])
@role_required("admin")
def add_doctor():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        specialization = request.form.get("specialization", "").strip()
        qualification = request.form.get("qualification", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        available_days = request.form.get("available_days", "").strip()
        available_time = request.form.get("available_time", "").strip()

        if not all([
            name, department, specialization, qualification,
            phone, email, available_days, available_time
        ]):
            flash("Please fill all doctor details.", "danger")
            return redirect(url_for("add_doctor"))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("add_doctor"))

        doctor = Doctor(
            name=name,
            department=department,
            specialization=specialization,
            qualification=qualification,
            phone=phone,
            email=email,
            available_days=available_days,
            available_time=available_time
        )

        db.session.add(doctor)
        db.session.flush()

        temporary_password = secrets.token_urlsafe(10)

        doctor_user = User(
            name=name,
            email=email,
            role="doctor",
            doctor_id=doctor.id
        )

        doctor_user.set_password(temporary_password)

        db.session.add(doctor_user)
        db.session.commit()

        flash(
            "Doctor added successfully. Temporary login password: "
            + temporary_password,
            "success"
        )

        return redirect(url_for("doctors"))

    return render_template("add_doctor.html")


@app.route("/edit-doctor/<int:doctor_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_doctor(doctor_id):

    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == "POST":

        new_email = request.form.get("email", "").strip().lower()

        existing_user = User.query.filter_by(email=new_email).first()

        if existing_user and existing_user.doctor_id != doctor.id:
            flash("This email is already being used.", "danger")
            return redirect(url_for("edit_doctor", doctor_id=doctor.id))

        doctor.name = request.form.get("name", "").strip()
        doctor.department = request.form.get("department", "").strip()
        doctor.specialization = request.form.get("specialization", "").strip()
        doctor.qualification = request.form.get("qualification", "").strip()
        doctor.phone = request.form.get("phone", "").strip()
        doctor.email = new_email
        doctor.available_days = request.form.get("available_days", "").strip()
        doctor.available_time = request.form.get("available_time", "").strip()

        doctor_user = User.query.filter_by(doctor_id=doctor.id).first()

        if doctor_user:
            doctor_user.name = doctor.name
            doctor_user.email = doctor.email

        db.session.commit()

        flash("Doctor details updated successfully.", "success")
        return redirect(url_for("doctors"))

    return render_template("edit_doctor.html", doctor=doctor)


@app.route("/delete-doctor/<int:doctor_id>", methods=["GET", "POST"])
@role_required("admin")
def delete_doctor(doctor_id):

    doctor = Doctor.query.get_or_404(doctor_id)

    if Appointment.query.filter_by(doctor_id=doctor.id).first():
        flash("Cannot delete a doctor who has appointments.", "danger")
        return redirect(url_for("doctors"))

    doctor_user = User.query.filter_by(doctor_id=doctor.id).first()

    if doctor_user:
        db.session.delete(doctor_user)

    db.session.delete(doctor)
    db.session.commit()

    flash("Doctor deleted successfully.", "success")
    return redirect(url_for("doctors"))


# ---------------- PATIENT MANAGEMENT ---------------- #

@app.route("/patients")
@role_required("admin")
def patients():

    all_patients = Patient.query.order_by(Patient.id.desc()).all()

    return render_template("patients.html", patients=all_patients)


@app.route("/add-patient", methods=["GET", "POST"])
@role_required("admin")
def add_patient():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        age = request.form.get("age", "")
        gender = request.form.get("gender", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not all([name, age, gender, phone, address]):
            flash("Please fill all patient details.", "danger")
            return redirect(url_for("add_patient"))

        try:
            age = int(age)
            if age < 1 or age > 120:
                raise ValueError
        except ValueError:
            flash("Please enter a valid age.", "danger")
            return redirect(url_for("add_patient"))

        patient = Patient(
            name=name,
            age=age,
            gender=gender,
            phone=phone,
            address=address
        )

        db.session.add(patient)
        db.session.commit()

        flash("Patient added successfully.", "success")
        return redirect(url_for("patients"))

    return render_template("add_patient.html")


@app.route("/edit-patient/<int:patient_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_patient(patient_id):

    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":

        patient.name = request.form.get("name", "").strip()
        patient.age = int(request.form.get("age", patient.age))
        patient.gender = request.form.get("gender", "")
        patient.phone = request.form.get("phone", "").strip()
        patient.address = request.form.get("address", "").strip()

        patient_user = User.query.filter_by(patient_id=patient.id).first()

        if patient_user:
            patient_user.name = patient.name

        db.session.commit()

        flash("Patient details updated successfully.", "success")
        return redirect(url_for("patients"))

    return render_template("edit_patient.html", patient=patient)


@app.route("/delete-patient/<int:patient_id>", methods=["GET", "POST"])
@role_required("admin")
def delete_patient(patient_id):

    patient = Patient.query.get_or_404(patient_id)

    if Appointment.query.filter_by(patient_id=patient.id).first():
        flash("Cannot delete a patient who has appointments.", "danger")
        return redirect(url_for("patients"))

    patient_user = User.query.filter_by(patient_id=patient.id).first()

    if patient_user:
        db.session.delete(patient_user)

    db.session.delete(patient)
    db.session.commit()

    flash("Patient deleted successfully.", "success")
    return redirect(url_for("patients"))


# ---------------- PATIENT DASHBOARD ---------------- #

@app.route("/patient-dashboard")
@role_required("patient")
def patient_dashboard():

    all_doctors = Doctor.query.order_by(Doctor.name).all()

    return render_template(
        "patient_dashboard.html",
        doctors=all_doctors
    )


# ---------------- BOOK APPOINTMENT ---------------- #

@app.route("/book-appointment/<int:doctor_id>", methods=["GET", "POST"])
@role_required("patient")
def book_appointment(doctor_id):

    doctor = Doctor.query.get_or_404(doctor_id)
    user = get_current_user()

    if not user.patient_id:
        flash("Your patient profile is not linked to your account.", "danger")
        return redirect(url_for("patient_dashboard"))

    if request.method == "POST":

        appointment_date = request.form.get("appointment_date", "")
        appointment_time = request.form.get("appointment_time", "")

        if not appointment_date or not appointment_time:
            flash("Please select a date and time.", "danger")
            return redirect(url_for("book_appointment", doctor_id=doctor.id))

        existing = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status.notin_(["Rejected", "Cancelled"])
        ).first()

        if existing:
            flash(
                "This time slot is already booked. Please choose another.",
                "danger"
            )
            return redirect(url_for("book_appointment", doctor_id=doctor.id))

        appointment = Appointment(
            doctor_id=doctor.id,
            patient_id=user.patient_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status="Pending"
        )

        db.session.add(appointment)
        db.session.commit()

        flash("Appointment booked successfully!", "success")
        return redirect(url_for("my_appointments"))

    from datetime import date

    return render_template(
        "book_appointment.html",
        doctor=doctor,
        today=date.today().isoformat()
    )


# ---------------- ALL APPOINTMENTS (ADMIN) ---------------- #

@app.route("/appointments")
@role_required("admin")
def appointments():

    all_appointments = Appointment.query.order_by(
        Appointment.id.desc()
    ).all()

    return render_template("appointment.html", appointments=all_appointments)


# ---------------- DOCTOR DASHBOARD ---------------- #

@app.route("/doctor-dashboard")
@role_required("doctor")
def doctor_dashboard():

    user = get_current_user()

    if not user.doctor_id:
        flash("Your doctor profile is not linked to your account.", "danger")
        return redirect(url_for("logout"))

    doctor_appointments = Appointment.query.filter_by(
        doctor_id=user.doctor_id
    ).order_by(Appointment.id.desc()).all()

    return render_template(
        "doctor_appointments.html",
        appointments=doctor_appointments
    )


@app.route("/doctor-appointments")
@role_required("doctor")
def doctor_appointments():
    return redirect(url_for("doctor_dashboard"))


# ---------------- APPROVE APPOINTMENT ---------------- #

@app.route("/approve/<int:appointment_id>", methods=["GET", "POST"])
@role_required("admin", "doctor")
def approve_appointment(appointment_id):

    appointment = Appointment.query.get_or_404(appointment_id)
    user = get_current_user()

    if user.role == "doctor" and appointment.doctor_id != user.doctor_id:
        flash("You cannot approve another doctor's appointment.", "danger")
        return redirect(url_for("doctor_dashboard"))

    if appointment.status != "Pending":
        flash("This appointment is no longer pending.", "warning")
    else:
        appointment.status = "Approved"
        db.session.commit()
        flash("Appointment approved successfully.", "success")

    if user.role == "doctor":
        return redirect(url_for("doctor_dashboard"))

    return redirect(url_for("appointments"))


# ---------------- REJECT APPOINTMENT ---------------- #

@app.route("/reject/<int:appointment_id>", methods=["GET", "POST"])
@role_required("admin", "doctor")
def reject_appointment(appointment_id):

    appointment = Appointment.query.get_or_404(appointment_id)
    user = get_current_user()

    if user.role == "doctor" and appointment.doctor_id != user.doctor_id:
        flash("You cannot reject another doctor's appointment.", "danger")
        return redirect(url_for("doctor_dashboard"))

    if appointment.status != "Pending":
        flash("This appointment is no longer pending.", "warning")
    else:
        appointment.status = "Rejected"
        db.session.commit()
        flash("Appointment rejected.", "success")

    if user.role == "doctor":
        return redirect(url_for("doctor_dashboard"))

    return redirect(url_for("appointments"))


# ---------------- PATIENT APPOINTMENT HISTORY ---------------- #

@app.route("/my-appointments")
@app.route("/my-appointments/<int:patient_id>")
@role_required("patient")
def my_appointments(patient_id=None):

    user = get_current_user()

    if not user.patient_id:
        flash("Your patient profile is not linked.", "danger")
        return redirect(url_for("patient_dashboard"))

    my_records = Appointment.query.filter_by(
        patient_id=user.patient_id
    ).order_by(Appointment.id.desc()).all()

    return render_template("my_appointments.html", appointments=my_records)


# ---------------- CANCEL APPOINTMENT ---------------- #

@app.route("/cancel-appointment/<int:appointment_id>", methods=["GET", "POST"])
@role_required("patient")
def cancel_appointment(appointment_id):

    appointment = Appointment.query.get_or_404(appointment_id)
    user = get_current_user()

    if appointment.patient_id != user.patient_id:
        flash("You cannot cancel another patient's appointment.", "danger")
        return redirect(url_for("my_appointments"))

    if appointment.status in ["Rejected", "Cancelled"]:
        flash("This appointment cannot be cancelled.", "warning")
    else:
        appointment.status = "Cancelled"
        db.session.commit()
        flash("Appointment cancelled successfully.", "success")

    return redirect(url_for("my_appointments"))


# ---------------- CREATE ADMIN COMMAND ---------------- #

@app.cli.command("create-admin")
def create_admin():

    email = click.prompt("Admin email").strip().lower()
    name = click.prompt("Admin name").strip()
    password = click.prompt(
        "Admin password",
        hide_input=True,
        confirmation_prompt=True
    )

    if User.query.filter_by(email=email).first():
        click.echo("An account with this email already exists.")
        return

    if len(password) < 8:
        click.echo("Password must contain at least 8 characters.")
        return

    admin = User(name=name, email=email, role="admin")
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    click.echo("Admin account created successfully!")


# ---------------- LINK EXISTING DOCTOR COMMAND ---------------- #

@app.cli.command("link-doctor")
@click.argument("doctor_id", type=int)
@click.argument("email")
def link_doctor(doctor_id, email):

    doctor = db.session.get(Doctor, doctor_id)

    if not doctor:
        click.echo("Doctor not found.")
        return

    email = email.strip().lower()

    if User.query.filter_by(email=email).first():
        click.echo("This email already has an account.")
        return

    if User.query.filter_by(doctor_id=doctor.id).first():
        click.echo("This doctor already has a login account.")
        return

    password = click.prompt(
        "Temporary doctor password",
        hide_input=True,
        confirmation_prompt=True
    )

    if len(password) < 8:
        click.echo("Password must contain at least 8 characters.")
        return

    doctor_user = User(
        name=doctor.name,
        email=email,
        role="doctor",
        doctor_id=doctor.id
    )

    doctor_user.set_password(password)

    db.session.add(doctor_user)
    db.session.commit()

    click.echo("Doctor login account created successfully!")


# ---------------- RUN APPLICATION ---------------- #

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )

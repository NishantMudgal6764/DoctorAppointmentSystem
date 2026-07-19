from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Doctor, Patient, Appointment

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hospital.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "hospital123"

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():

    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()

    pending_appointments = Appointment.query.filter_by(
        status="Pending"
    ).count()

    return render_template(
        "dashboard.html",
        doctors=total_doctors,
        patients=total_patients,
        appointments=total_appointments,
        pending=pending_appointments
    )


# ------------------ DOCTOR MODULE ------------------ #

@app.route("/doctors")
def doctors():
    doctor_list = Doctor.query.all()
    return render_template("doctors.html", doctors=doctor_list)


@app.route("/add-doctor", methods=["GET", "POST"])
def add_doctor():
    if request.method == "POST":
        doctor = Doctor(
            name=request.form["name"],
            department=request.form["department"],
            specialization=request.form["specialization"],
            qualification=request.form["qualification"],
            phone=request.form["phone"],
            email=request.form["email"],
            available_days=request.form["available_days"],
            available_time=request.form["available_time"]
        )

        db.session.add(doctor)
        db.session.commit()
        flash("Doctor added successfully!", "success")

        return redirect(url_for("doctors"))

    return render_template("add_doctor.html")


@app.route("/edit-doctor/<int:id>", methods=["GET", "POST"])
def edit_doctor(id):
    doctor = Doctor.query.get_or_404(id)

    if request.method == "POST":
        doctor.name = request.form["name"]
        doctor.department = request.form["department"]
        doctor.specialization = request.form["specialization"]
        doctor.qualification = request.form["qualification"]
        doctor.phone = request.form["phone"]
        doctor.email = request.form["email"]
        doctor.available_days = request.form["available_days"]
        doctor.available_time = request.form["available_time"]

        db.session.commit()
        flash("Doctor updated successfully!", "success")
        return redirect(url_for("doctors"))

    return render_template("edit_doctor.html", doctor=doctor)

@app.route("/delete-doctor/<int:id>")
def delete_doctor(id):
    doctor = Doctor.query.get_or_404(id)

    db.session.delete(doctor)
    db.session.commit()
    flash("Doctor deleted successfully!", "danger")
    return redirect(url_for("doctors"))


# ------------------ PATIENT ------------------ #

@app.route("/patients")
def patients():
    patient_list = Patient.query.all()
    return render_template("patients.html", patients=patient_list)


@app.route("/add-patient", methods=["GET", "POST"])
def add_patient():

    if request.method == "POST":

        patient = Patient(
            name=request.form["name"],
            age=request.form["age"],
            gender=request.form["gender"],
            phone=request.form["phone"],
            address=request.form["address"]
        )

        db.session.add(patient)
        db.session.commit()
        flash("Patient added successfully!", "success")
        return redirect(url_for("patients"))

    return render_template("add_patient.html")


@app.route("/edit-patient/<int:id>", methods=["GET", "POST"])
def edit_patient(id):

    patient = Patient.query.get_or_404(id)

    if request.method == "POST":

        patient.name = request.form["name"]
        patient.age = request.form["age"]
        patient.gender = request.form["gender"]
        patient.phone = request.form["phone"]
        patient.address = request.form["address"]

        db.session.commit()
        flash("Patient updated successfully!", "success")
        return redirect(url_for("patients"))

    return render_template("edit_patient.html", patient=patient)


@app.route("/delete-patient/<int:id>")
def delete_patient(id):

    patient = Patient.query.get_or_404(id)

    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted successfully!", "danger")
    return redirect(url_for("patients"))


# -------- PATIENT DASHBOARD -------- #

@app.route("/patient-dashboard")
def patient_dashboard():

    doctor_list = Doctor.query.all()

    return render_template(
        "patient_dashboard.html",
        doctors=doctor_list
    )

@app.route("/book-appointment/<int:doctor_id>", methods=["GET", "POST"])
def book_appointment(doctor_id):

    doctor = Doctor.query.get_or_404(doctor_id)

    patient_list = Patient.query.all()

    if request.method == "POST":

        appointment = Appointment(
            doctor_id=doctor.id,
            patient_id=request.form["patient_id"],
            appointment_date=request.form["appointment_date"],
            appointment_time=request.form["appointment_time"]
        )

        db.session.add(appointment)
        db.session.commit()

        return redirect(url_for("appointments"))

    return render_template(
        "book_appointment.html",
        doctor=doctor,
        patients=patient_list
    )



# ------------------ APPOINTMENT ------------------ #

@app.route("/appointments")
def appointments():

    appointment_list = Appointment.query.all()

    return render_template(
        "appointment.html",
        appointments=appointment_list
    )

@app.route("/doctor-appointments")
def doctor_appointments():

    appointment_list = Appointment.query.all()

    return render_template(
        "doctor_appointments.html",
        appointments=appointment_list
    )

@app.route("/approve/<int:id>")
def approve(id):

    appointment = Appointment.query.get_or_404(id)

    appointment.status = "Approved"

    db.session.commit()
    flash("Appointment approved!", "success")
    return redirect(url_for("doctor_appointments"))



@app.route("/reject/<int:id>")
def reject(id):

    appointment = Appointment.query.get_or_404(id)

    appointment.status = "Rejected"

    db.session.commit()
    flash("Appointment rejected!", "danger")
    return redirect(url_for("doctor_appointments"))


# -------- PATIENT MY APPOINTMENTS -------- #


@app.route("/my-appointments/<int:patient_id>")
def my_appointments(patient_id):

    appointment_list = Appointment.query.filter_by(
        patient_id=patient_id
    ).all()

    return render_template(
        "my_appointments.html",
        appointments=appointment_list
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)


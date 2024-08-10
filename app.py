from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import csv
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/dbname'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploaded_docs'

db = SQLAlchemy(app)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    records = db.relationship('HealthRecord', backref='patient', lazy=True)

class HealthRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date = db.Column(db.Date)
    complaint = db.Column(db.Text)
    doctor = db.Column(db.String(100))
    investigation = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    medication = db.Column(db.Text)
    notes = db.Column(db.Text)
    follow_up = db.Column(db.Text)
    document_path = db.Column(db.String(255))

@app.route('/')
def index():
    patients = Patient.query.all()
    return render_template('index.html', patients=patients)

@app.route('/patient/<int:patient_id>')
def patient_records(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    records = HealthRecord.query.filter_by(patient_id=patient_id).all()
    return render_template('patient_records.html', patient=patient, records=records)

@app.route('/new_patient', methods=['POST'])
def new_patient():
    name = request.form.get('name')
    if name:
        patient = Patient(name=name)
        db.session.add(patient)
        db.session.commit()
    return jsonify(success=True)

@app.route('/new_record/<int:patient_id>', methods=['POST'])
def new_record(patient_id):
    data = request.form
    record = HealthRecord(
        patient_id=patient_id,
        date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
        complaint=data['complaint'],
        doctor=data['doctor'],
        investigation=data['investigation'],
        diagnosis=data['diagnosis'],
        medication=data['medication'],
        notes=data['notes'],
        follow_up=data['follow_up']
    )
    db.session.add(record)
    db.session.commit()
    return jsonify(success=True)

@app.route('/edit_record/<int:record_id>', methods=['POST'])
def edit_record(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    data = request.form
    record.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    record.complaint = data['complaint']
    record.doctor = data['doctor']
    record.investigation = data['investigation']
    record.diagnosis = data['diagnosis']
    record.medication = data['medication']
    record.notes = data['notes']
    record.follow_up = data['follow_up']
    db.session.commit()
    return jsonify(success=True)

@app.route('/delete_record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.document_path and os.path.exists(record.document_path):
        os.remove(record.document_path)
    db.session.delete(record)
    db.session.commit()
    return jsonify(success=True)

@app.route('/upload_document/<int:record_id>', methods=['POST'])
def upload_document(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if 'document' in request.files:
        file = request.files['document']
        if file.filename != '':
            filename = f"{record_id}_{file.filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            record.document_path = file_path
            db.session.commit()
    return jsonify(success=True)

@app.route('/download_document/<int:record_id>')
def download_document(record_id):
    record = HealthRecord.query.get_or_404(record_id)
    if record.document_path and os.path.exists(record.document_path):
        return send_file(record.document_path, as_attachment=True)
    return jsonify(error="Document not found"), 404

@app.route('/export_csv/<int:patient_id>')
def export_csv(patient_id):
    records = HealthRecord.query.filter_by(patient_id=patient_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Complaint', 'Doctor', 'Investigation', 'Diagnosis', 'Medication', 'Notes', 'Follow-up', 'Document Path'])
    for record in records:
        writer.writerow([record.id, record.date, record.complaint, record.doctor, record.investigation, record.diagnosis, record.medication, record.notes, record.follow_up, record.document_path])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, attachment_filename=f'patient_{patient_id}_records.csv')

@app.route('/import_csv/<int:patient_id>', methods=['POST'])
def import_csv(patient_id):
    if 'csv_file' not in request.files:
        return jsonify(error="No file part"), 400
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify(error="No selected file"), 400
    if file:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        next(csv_reader)  # Skip header row
        for row in csv_reader:
            record = HealthRecord(
                patient_id=patient_id,
                date=datetime.strptime(row[1], '%Y-%m-%d').date(),
                complaint=row[2],
                doctor=row[3],
                investigation=row[4],
                diagnosis=row[5],
                medication=row[6],
                notes=row[7],
                follow_up=row[8],
                document_path=row[9]
            )
            db.session.add(record)
        db.session.commit()
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)

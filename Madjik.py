import sys,webview,os
from threading import Thread
from flask import Flask, render_template, send_file, request, redirect, url_for, flash, jsonify
from datetime import datetime
import sqlite3

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

app = Flask(__name__,
    template_folder=resource_path('templates'),
    static_folder=resource_path('static'))
app.secret_key = 'secret_key_here'
DB = 'patients.db'

def get_db():
    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise

def get_patient_data(patient_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get patient info
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        patient = cursor.fetchone()
        
        if not patient:
            return None, None, None
            
        # Get medical records
        cursor.execute("""
            SELECT id, visit_date, notes
            FROM medical_records
            WHERE patient_id = ?
            ORDER BY visit_date DESC
        """, (patient_id,))
        records = cursor.fetchall()

        # Get medical history
        cursor.execute("""
            SELECT id, history_note
            FROM medical_history
            WHERE patient_id = ?
            ORDER BY id DESC
        """, (patient_id,))
        history = cursor.fetchall()
        
        conn.close()
        return patient, records, history
        
    except sqlite3.Error as e:
        print(f"Error fetching patient data: {e}")
        raise

def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            middle_initial TEXT,
            age INTEGER,
            sex TEXT,
            barangay TEXT,
            city TEXT,
            emergency_contact TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            visit_date DATE,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            history_note TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lic_no TEXT,
            ptr_no TEXT,
            tin_no TEXT,
            s2_no TEXT
        )
    ''')

    conn.commit()
    conn.close()

@app.template_filter('format_date')
def format_date(value):
    try:
        # Try ISO format first
        date_obj = datetime.strptime(value, '%Y-%m-%d')
        return date_obj.strftime('%m-%d-%Y')
    except ValueError:
        try:
            # Try custom format if ISO fails
            date_obj = datetime.strptime(value, '%m-%d-%Y')
            return date_obj.strftime('%m-%d-%Y')
        except ValueError:
            return value
    except TypeError:
        return value

@app.route('/')
def index():
    query = request.args.get('search', '')
    conn = get_db()
    cursor = conn.cursor()

    if query:
        cursor.execute("""
            SELECT p.*, MAX(m.visit_date) as last_visit
            FROM patients p
            LEFT JOIN medical_records m ON p.id = m.patient_id
            WHERE p.first_name LIKE ? OR p.last_name LIKE ?
            GROUP BY p.id
        """, (f'%{query}%', f'%{query}%'))
    else:
        cursor.execute("""
            SELECT p.*, MAX(m.visit_date) as last_visit
            FROM patients p
            LEFT JOIN medical_records m ON p.id = m.patient_id
            GROUP BY p.id
        """)




    patients = cursor.fetchall()

    # Load signature info (single-row)
    cursor.execute("SELECT * FROM signatures LIMIT 1")
    signature_info = cursor.fetchone()

    conn.close()
    return render_template('index.html', patients=patients, signature_info=signature_info)

@app.route('/add', methods=['POST'])
def add():
    try:
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        middle_initial = request.form.get('middle_initial', '')
        age = request.form.get('age', '')
        sex = request.form.get('sex', '')
        barangay = request.form.get('barangay', '')
        city = request.form.get('city', '')
        emergency_contact = request.form.get('emergency_contact', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO patients 
            (first_name, last_name, middle_initial, age, sex, barangay, city, emergency_contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, middle_initial, age, sex, barangay, city, emergency_contact))
        conn.commit()
        conn.close()
        return redirect('/')
    except Exception as e:
        print(f"Error adding patient: {e}")
        flash('Error adding patient. Please try again.')
        return redirect('/')

@app.route('/edit/<int:patient_id>', methods=['POST'])
def edit(patient_id):
    try:
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        middle_initial = request.form.get('middle_initial', '')
        age = request.form.get('age', '')
        sex = request.form.get('sex', '')
        barangay = request.form.get('barangay', '')
        city = request.form.get('city', '')
        emergency_contact = request.form.get('emergency_contact', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE patients 
            SET first_name = ?,
                last_name = ?,
                middle_initial = ?,
                age = ?,
                sex = ?,
                barangay = ?,
                city = ?,
                emergency_contact = ?
            WHERE id = ?
        """, (first_name, last_name, middle_initial, age, sex, barangay, city, emergency_contact, patient_id))
        conn.commit()
        conn.close()
        return redirect(f'/patient/{patient_id}')
    except Exception as e:
        print(f"Error editing patient: {e}")
        flash('Error editing patient. Please try again.')
        return redirect(f'/patient/{patient_id}')
    return redirect(url_for('view_patient', patient_id=patient_id))

@app.route('/edit_medical_history/<int:patient_id>', methods=['POST'])
def edit_medical_history(patient_id):
    medical_history = request.form.get('medical_history', '').strip()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE patients
            SET medical_history = ?
            WHERE id = ?
        """, (medical_history, patient_id))
        conn.commit()

    return redirect(url_for('view_patient', patient_id=patient_id))

@app.route('/delete/<int:patient_id>', methods=['POST'])
def delete(patient_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medical_records WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        conn.close()
        return redirect('/')
    except sqlite3.Error as e:
        print(f"Error deleting patient: {e}")
        flash('Error deleting patient', 'error')
        return redirect(url_for('view_patient', patient_id=patient_id))

@app.route('/patient/<int:patient_id>')
def view_patient(patient_id):
    try:
        patient, records, history = get_patient_data(patient_id)
        if not patient:
            flash('Patient not found', 'error')
            return redirect('/')

        patient = dict(patient)

        return render_template('patient_details.html',
                               patient=patient,
                               records=records,
                               history=history)

    except Exception as e:
        print(f"Error in view_patient: {e}")
        flash('Error viewing patient details', 'error')
        return redirect('/')

@app.route('/update_signatures', methods=['POST'])
def update_signatures():
    try:
        lic_no = request.form['lic_no']
        ptr_no = request.form['ptr_no']
        tin_no = request.form['tin_no']
        s2_no = request.form['s2_no']

        conn = get_db()
        cursor = conn.cursor()
        
        # First check if there's an existing record
        cursor.execute("SELECT COUNT(*) FROM signatures")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insert if no record exists
            cursor.execute("""
                INSERT INTO signatures (lic_no, ptr_no, tin_no, s2_no)
                VALUES (?, ?, ?, ?)
            """, (lic_no, ptr_no, tin_no, s2_no))
        else:
            # Update if record exists
            cursor.execute("""
                UPDATE signatures 
                SET lic_no=?, ptr_no=?, tin_no=?, s2_no=?
            """, (lic_no, ptr_no, tin_no, s2_no))
        
        conn.commit()
        conn.close()
        flash('Signature info updated successfully', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Error updating signatures: {e}")
        flash('Error updating signature info', 'error')
        return redirect(url_for('index'))

@app.route('/api/signature')
def api_signature():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT lic_no, ptr_no, tin_no, s2_no FROM signatures LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            signature_info = {
                "lic_no": row[0],
                "ptr_no": row[1],
                "tin_no": row[2],
                "s2_no": row[3]
            }
        else:
            signature_info = {
                "lic_no": "",
                "ptr_no": "",
                "tin_no": "",
                "s2_no": ""
            }
        return signature_info
    except Exception as e:
        print(f"Error fetching signature info: {e}")
        return {
            "lic_no": "",
            "ptr_no": "",
            "tin_no": "",
            "s2_no": ""
        }



@app.route('/add_record/<int:patient_id>', methods=['POST'])
def add_record(patient_id):
    try:
        visit_date = request.form['visit_date']
        notes = request.form['notes']
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO medical_records (patient_id, visit_date, notes)
                VALUES (?, ?, ?)
            """, (patient_id, visit_date, notes))
            conn.commit()
        
        flash('Visit record added successfully', 'success')
        return redirect(url_for('view_patient', patient_id=patient_id))
    
    except Exception as e:
        print(f"Error adding record: {e}")
        flash('Error adding visit record', 'error')
        return redirect(url_for('view_patient', patient_id=patient_id))

@app.route('/edit_record/<int:visit_id>', methods=['POST'])
def edit_record(visit_id):
    try:
        visit_date = request.form['visit_date']
        notes = request.form['notes']
        patient_id = request.form.get('patient_id')
        
        if not patient_id:
            return jsonify({'error': 'Patient ID is required'}), 400
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE medical_records 
                SET visit_date = ?, notes = ?
                WHERE id = ? AND patient_id = ?
            """, (visit_date, notes, visit_id, patient_id))
            conn.commit()
        
        flash('Visit record updated successfully', 'success')
        return redirect(url_for('view_patient', patient_id=patient_id))
    
    except Exception as e:
        print(f"Error updating record: {e}")
        flash('Error updating visit record', 'error')
        return redirect(url_for('view_patient', patient_id=request.form.get('patient_id', '')))

@app.route('/add_history/<int:patient_id>', methods=['POST'])
def add_history(patient_id):
    history_note = request.form['history_note']
    history_id = request.form.get('id')
    
    with get_db() as conn:
        cursor = conn.cursor()
        if history_id:
            cursor.execute('''
                UPDATE medical_history 
                SET history_note = ?
                WHERE id = ?
            ''', (history_note, history_id))
        else:
            cursor.execute('''
                INSERT INTO medical_history (patient_id, history_note)
                VALUES (?, ?)
            ''', (patient_id, history_note))
        conn.commit()
    return redirect(url_for('view_patient', patient_id=patient_id))

@app.route('/history/<int:history_id>')
def get_history(history_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM medical_history WHERE id = ?
        ''', (history_id,))
        history = cursor.fetchone()
    return jsonify({
        'id': history[0],
        'patient_id': history[1],
        'history_note': history[2]
    })

@app.route('/delete_record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM medical_records WHERE id = ?", (record_id,))
    result = cursor.fetchone()
    if result:
        patient_id = result[0]
        cursor.execute("DELETE FROM medical_records WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('view_patient', patient_id=patient_id))
    conn.close()
    return redirect('/')

def start_flask():
    app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == "__main__":
    init_db()
    Thread(target=start_flask, daemon=True).start()
    webview.create_window(
        "Madjik",
        "http://127.0.0.1:5000",
        width=1920,
        height=1080,
        resizable=True
    )
    webview.start(gui='edgechromium')

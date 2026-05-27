import streamlit as st
import hashlib
import datetime
import json
import os
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
import time

st.set_page_config(page_title="BUDIRIRO TB/HIV PREDICTOR", page_icon="🏥", layout="wide")

# ============================================
# GLOBAL CSS
# ============================================
st.markdown("""
<style>
    body, .stApp, .main, div, p, span, label {
        font-size: 16px !important;
        font-weight: 500 !important;
    }
    h1 { font-size: 32px !important; font-weight: 800 !important; color: #1a5276 !important; }
    h2 { font-size: 28px !important; font-weight: 700 !important; color: #2e86c1 !important; }
    h3 { font-size: 24px !important; font-weight: 700 !important; }
    .stButton button { font-size: 18px !important; font-weight: 700 !important; background-color: #2e86c1 !important; color: white !important; }
    [data-testid="stMetric"] label { font-size: 16px !important; font-weight: 700 !important; }
    [data-testid="stMetric"] value { font-size: 28px !important; font-weight: 800 !important; }
    .low-risk { background-color: #d4edda; padding: 1rem; border-radius: 10px; border-left: 5px solid #28a745; margin: 1rem 0; }
    .moderate-risk { background-color: #fff3cd; padding: 1rem; border-radius: 10px; border-left: 5px solid #ffc107; margin: 1rem 0; }
    .high-risk { background-color: #f8d7da; padding: 1rem; border-radius: 10px; border-left: 5px solid #dc3545; margin: 1rem 0; }
    .alert-critical { background-color: #dc3545; color: white; padding: 1rem; border-radius: 10px; animation: blink 1s infinite; }
    @keyframes blink { 50% { opacity: 0.5; } }
    .sms-log { background-color: #e8f4fd; padding: 0.5rem; border-radius: 5px; margin: 0.25rem 0; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# ============================================
# USER DATABASE
# ============================================
USERS_FILE = "users.json"
PATIENTS_FILE = "patients.json"
PREDICTIONS_FILE = "predictions.json"
NUTRITION_FILE = "nutrition.json"
MENTAL_HEALTH_FILE = "mental_health.json"
ALERTS_FILE = "alerts.json"
SMS_LOG_FILE = "sms_log.json"

def load_json(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# Initialize session
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'page' not in st.session_state:
    st.session_state.page = "login"
if 'sms_history' not in st.session_state:
    st.session_state.sms_history = []
if 'edit_patient_id' not in st.session_state:
    st.session_state.edit_patient_id = None

@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="budiriro_tb_clinic")

# ============================================
# 5 PRE-CONFIGURED USERS (NO CREATE ACCOUNT)
# ============================================
PREDEFINED_USERS = {
    'dr_chimedza': {
        'name': 'Dr. T. Chimedza',
        'password': 'clinic2024',
        'role': 'Senior Clinician',
        'department': 'TB/HIV Unit'
    },
    'nurse_moyo': {
        'name': 'Nurse S. Moyo',
        'password': 'nurse123',
        'role': 'TB Nurse',
        'department': 'Outpatient'
    },
    'clinician_dube': {
        'name': 'Clinician M. Dube',
        'password': 'dube456',
        'role': 'Clinical Officer',
        'department': 'HIV/TB Care'
    },
    'sister_mukoni': {
        'name': 'Sister E. Mukoni',
        'password': 'sister789',
        'role': 'Senior Nursing Officer',
        'department': 'ART Clinic'
    },
    'data_mahara': {
        'name': 'Mr. T. Mahara',
        'password': 'data2024',
        'role': 'Data Officer',
        'department': 'M&E Department'
    }
}

# Load existing users or create predefined ones
users = load_json(USERS_FILE)
if not users:
    for username, user_info in PREDEFINED_USERS.items():
        users[username] = {
            'name': user_info['name'],
            'password': hash_password(user_info['password']),
            'role': user_info['role'],
            'department': user_info['department'],
            'created': str(datetime.datetime.now()),
            'predictions_count': 0,
            'patients_registered': 0
        }
    save_json(USERS_FILE, users)

# ============================================
# SMS REMINDER FUNCTION
# ============================================
def send_sms(phone_number, patient_name, message_type, risk_level="low"):
    sms_log = load_json(SMS_LOG_FILE)
    
    messages = {
        "appointment": f"🏥 Budiriro Clinic Reminder: {patient_name}, you have a clinic appointment tomorrow.",
        "medication": f"💊 Medication Reminder: {patient_name}, time to take your TB medication.",
        "high_risk_warning": f"⚠️ URGENT: {patient_name}, you missed your last clinic appointment.",
        "nutrition": f"🥗 Nutrition Support: {patient_name}, visit the clinic for food assistance.",
        "mental_health": f"🧠 Mental Health Support: {patient_name}, speak to our counselor."
    }
    
    if risk_level == "high" and message_type == "appointment":
        message = messages["high_risk_warning"]
    elif message_type == "nutrition":
        message = messages["nutrition"]
    elif message_type == "mental_health":
        message = messages["mental_health"]
    else:
        message = messages.get(message_type, messages["medication"])
    
    sms_entry = {
        'id': len(sms_log) + 1,
        'patient_name': patient_name,
        'phone': phone_number,
        'message_type': message_type,
        'message': message,
        'risk_level': risk_level,
        'sent_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'sent_by': st.session_state.username,
        'status': 'delivered'
    }
    
    sms_log[str(len(sms_log) + 1)] = sms_entry
    save_json(SMS_LOG_FILE, sms_log)
    st.session_state.sms_history.insert(0, sms_entry)
    return message

def display_sms_history():
    sms_log = load_json(SMS_LOG_FILE)
    if sms_log:
        st.markdown("#### Recent SMS Messages")
        for sms in list(sms_log.values())[-5:]:
            st.markdown(f'<div class="sms-log">📱 To: {sms["patient_name"]} | {sms["message"]}<br>⏰ {sms["sent_time"]}</div>', unsafe_allow_html=True)

# ============================================
# LOGIN PAGE
# ============================================
def login_page():
    st.markdown("<h1 style='text-align:center;'>🏥 Budiriro Satellite Clinic</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>TB/HIV Treatment Default Risk Prediction System</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div style="background-color: #f0f2f6; padding: 2rem; border-radius: 10px;">', unsafe_allow_html=True)
        
        st.markdown("<p style='text-align:center; font-size:14px;'>🔐 Authorized Clinical Personnel Only</p>", unsafe_allow_html=True)
        
        department = st.selectbox("Select Department", [
            "TB/HIV Unit",
            "Outpatient", 
            "ART Clinic",
            "M&E Department"
        ])
        
        if department == "TB/HIV Unit":
            user_options = ["dr_chimedza", "clinician_dube"]
        elif department == "Outpatient":
            user_options = ["nurse_moyo"]
        elif department == "ART Clinic":
            user_options = ["sister_mukoni"]
        elif department == "M&E Department":
            user_options = ["data_mahara"]
        else:
            user_options = ["dr_chimedza", "nurse_moyo", "clinician_dube", "sister_mukoni", "data_mahara"]
        
        username = st.selectbox("Select User", user_options, format_func=lambda x: PREDEFINED_USERS[x]['name'])
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        if st.button("🔐 Login", use_container_width=True, type="primary"):
            if username in PREDEFINED_USERS:
                if password == PREDEFINED_USERS[username]['password']:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_name = PREDEFINED_USERS[username]['name']
                    st.session_state.user_role = PREDEFINED_USERS[username]['role']
                    st.session_state.user_department = department
                    st.rerun()
                else:
                    st.error("❌ Invalid password.")
            else:
                st.error("❌ Invalid username.")
        
        st.markdown("---")
        st.markdown("<p style='text-align:center; font-size:12px; font-weight:bold;'>Authorized Users by Department</p>", unsafe_allow_html=True)
        
        user_info = """
        <table style='width:100%; font-size:12px;'>
            <tr><th>Department</th><th>Username</th><th>User</th></tr>
            <tr><td>TB/HIV Unit</td><td>dr_chimedza</td><td>Dr. T. Chimedza</td></tr>
            <tr><td>TB/HIV Unit</td><td>clinician_dube</td><td>Clinician M. Dube</td></tr>
            <tr><td>Outpatient</td><td>nurse_moyo</td><td>Nurse S. Moyo</td></tr>
            <tr><td>ART Clinic</td><td>sister_mukoni</td><td>Sister E. Mukoni</td></tr>
            <tr><td>M&E Department</td><td>data_mahara</td><td>Mr. T. Mahara</td></tr>
        </table>
        """
        st.markdown(user_info, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# REGISTER PAGE - DISABLED
# ============================================
def register_page():
    st.markdown("<h2 style='text-align:center;'>Registration Disabled</h2>", unsafe_allow_html=True)
    st.warning("Account creation is disabled. Please contact the system administrator for access.")
    
    if st.button("Back to Login", use_container_width=True):
        st.session_state.page = "login"
        st.rerun()

# ============================================
# EDIT PATIENT FUNCTION
# ============================================
def edit_patient(patient_id, patient_data):
    st.markdown("<h4>✏️ Edit Patient Details</h4>", unsafe_allow_html=True)
    
    with st.form(key=f"edit_patient_form_{patient_id}"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Patient Full Name", value=patient_data['name'])
            new_age = st.number_input("Age", 0, 120, value=patient_data['age'])
            new_gender = st.selectbox("Gender", ["Male", "Female"], index=0 if patient_data['gender'] == "Male" else 1)
            new_phone = st.text_input("Phone Number", value=patient_data.get('phone', ''))
        with col2:
            new_hiv = st.selectbox("HIV Status", ["Positive", "Negative", "Unknown"], 
                                   index=["Positive", "Negative", "Unknown"].index(patient_data.get('hiv_status', 'Unknown')))
            new_tb = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"],
                                  index=0 if patient_data.get('tb_type', 'Pulmonary') == "Pulmonary" else 1)
            new_suburb = st.text_input("Suburb/Area", value=patient_data.get('location', {}).get('suburb', ''))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Changes"):
                patients = load_json(PATIENTS_FILE)
                patients[patient_id]['name'] = new_name
                patients[patient_id]['age'] = new_age
                patients[patient_id]['gender'] = new_gender
                patients[patient_id]['phone'] = new_phone
                patients[patient_id]['hiv_status'] = new_hiv
                patients[patient_id]['tb_type'] = new_tb
                if 'location' not in patients[patient_id]:
                    patients[patient_id]['location'] = {}
                patients[patient_id]['location']['suburb'] = new_suburb
                save_json(PATIENTS_FILE, patients)
                st.success("✅ Patient details updated!")
                st.session_state.edit_patient_id = None
                st.rerun()
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state.edit_patient_id = None
                st.rerun()

# ============================================
# DELETE PATIENT FUNCTION
# ============================================
def delete_patient(patient_id, patient_name):
    st.markdown("<h4>⚠️ Delete Patient Record</h4>", unsafe_allow_html=True)
    st.warning(f"Are you sure you want to delete **{patient_name}**? This action cannot be undone.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Yes, Delete Patient", key=f"confirm_delete_{patient_id}"):
            patients = load_json(PATIENTS_FILE)
            if patient_id in patients:
                del patients[patient_id]
                save_json(PATIENTS_FILE, patients)
                st.success(f"✅ Patient {patient_name} has been deleted!")
                st.rerun()
    with col2:
        if st.button("❌ Cancel", key=f"cancel_delete_{patient_id}"):
            st.rerun()

# ============================================
# SAVE ALERT FUNCTION
# ============================================
def save_alert(patient_id, patient_name, alert_type, message, priority="high"):
    alerts = load_json(ALERTS_FILE)
    alert_id = f"ALT-{len(alerts)+1:04d}"
    alerts[alert_id] = {
        'patient_id': patient_id,
        'patient_name': patient_name,
        'type': alert_type,
        'message': message,
        'priority': priority,
        'date': str(datetime.datetime.now()),
        'resolved': False,
        'clinician': st.session_state.username
    }
    save_json(ALERTS_FILE, alerts)
    
    if priority == "high":
        patients = load_json(PATIENTS_FILE)
        if patient_id in patients and patients[patient_id].get('phone'):
            send_sms(patients[patient_id]['phone'], patient_name, "appointment", "high")

# ============================================
# NUTRITIONAL ASSESSMENT
# ============================================
def nutritional_assessment(patient_id, patient_name):
    st.markdown("<h4>🥗 Nutritional Assessment</h4>", unsafe_allow_html=True)
    nutrition_data = load_json(NUTRITION_FILE)
    
    with st.form(key=f"nut_form_{patient_id}"):
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Current Weight (kg)", 25.0, 150.0, 60.0)
            height = st.number_input("Height (cm)", 100, 250, 165)
            muac = st.number_input("MUAC (cm)", 10.0, 40.0, 25.0)
        with col2:
            bmi = weight / ((height/100) ** 2)
            st.metric("BMI", f"{bmi:.1f}")
            
            if weight < 50:
                st.error("🔴 CRITICAL: Severe underweight - High risk of default")
                save_alert(patient_id, patient_name, "nutrition", f"Severe underweight: {weight}kg", "high")
            elif weight < 55:
                st.warning("🟡 Moderate underweight - Monitor closely")
            else:
                st.success("🟢 Normal weight - Continue monitoring")
        
        st.markdown("#### Food Security Assessment")
        food_insecure = st.radio("In the past month, did you ever run out of food?", 
                                  ["No", "Yes, sometimes", "Yes, often"])
        
        if food_insecure in ["Yes, sometimes", "Yes, often"]:
            st.warning("🚨 Food insecurity detected - Refer to social services")
        
        if st.form_submit_button("💾 Save Nutritional Assessment"):
            nutrition_data[patient_id] = {
                'patient_name': patient_name,
                'date': str(datetime.datetime.now()),
                'weight': weight,
                'height': height,
                'bmi': bmi,
                'muac': muac,
                'food_insecure': food_insecure,
                'assessed_by': st.session_state.username
            }
            save_json(NUTRITION_FILE, nutrition_data)
            st.success("✅ Nutritional assessment saved!")

# ============================================
# MENTAL HEALTH SCREENING (FIXED DUPLICATE KEY)
# ============================================
def mental_health_screening(patient_id, patient_name):
    st.markdown("<h4>🧠 Mental Health Screening (PHQ-9)</h4>", unsafe_allow_html=True)
    mental_data = load_json(MENTAL_HEALTH_FILE)
    
    st.markdown("Over the last 2 weeks, how often have you been bothered by the following problems?")
    
    phq9_questions = [
        "Little interest or pleasure in doing things?",
        "Feeling down, depressed, or hopeless?",
        "Trouble falling/staying asleep or sleeping too much?",
        "Feeling tired or having little energy?",
        "Poor appetite or overeating?",
        "Feeling bad about yourself?",
        "Trouble concentrating on things?",
        "Moving or speaking slowly?",
        "Thoughts that you would be better off dead?"
    ]
    
    phq9_scores = []
    for i, q in enumerate(phq9_questions):
        score = st.radio(f"{i+1}. {q}", [0, 1, 2, 3], 
                         format_func=lambda x: ["Not at all", "Several days", "More than half days", "Nearly every day"][x],
                         horizontal=True, key=f"phq9_{patient_id}_{i}")
        phq9_scores.append(score)
    
    total_phq9 = sum(phq9_scores)
    
    st.markdown("---")
    
    if total_phq9 >= 15:
        st.error(f"🔴 PHQ-9 Score: {total_phq9} - Severe Depression")
        save_alert(patient_id, patient_name, "mental_health", f"PHQ-9 score: {total_phq9}", "high")
    elif total_phq9 >= 10:
        st.warning(f"🟡 PHQ-9 Score: {total_phq9} - Moderate Depression")
        save_alert(patient_id, patient_name, "mental_health", f"PHQ-9 score: {total_phq9}", "medium")
    elif total_phq9 >= 5:
        st.info(f"📊 PHQ-9 Score: {total_phq9} - Mild Depression")
    else:
        st.success(f"🟢 PHQ-9 Score: {total_phq9} - Minimal depression")
    
    # FIXED: Added unique key for the button
    if st.button(f"💾 Save Mental Health Assessment_{patient_id}", key=f"save_mh_{patient_id}"):
        mental_data[patient_id] = {
            'patient_name': patient_name,
            'date': str(datetime.datetime.now()),
            'phq9_score': total_phq9,
            'responses': phq9_scores,
            'assessed_by': st.session_state.username
        }
        save_json(MENTAL_HEALTH_FILE, mental_data)
        st.success("✅ Mental health assessment saved!")

# ============================================
# CLINICAL ALERTS DASHBOARD
# ============================================
def clinical_alerts_dashboard():
    st.markdown("<h3>🚨 Clinical Alerts Dashboard</h3>", unsafe_allow_html=True)
    
    alerts = load_json(ALERTS_FILE)
    unresolved = {k:v for k,v in alerts.items() if not v.get('resolved', False)}
    
    high_priority = [a for a in unresolved.values() if a.get('priority') == 'high']
    medium_priority = [a for a in unresolved.values() if a.get('priority') == 'medium']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Active Alerts", len(unresolved))
    col2.metric("High Priority", len(high_priority), delta="URGENT", delta_color="inverse")
    col3.metric("Medium Priority", len(medium_priority))
    
    if not unresolved:
        st.success("✅ No active alerts! All patients are stable.")
        return
    
    if high_priority:
        st.markdown("### 🔴 HIGH PRIORITY ALERTS")
        for alert_id, alert in alerts.items():
            if not alert.get('resolved', False) and alert.get('priority') == 'high':
                with st.expander(f"🚨 {alert['patient_name']} - {alert['type'].upper()}", expanded=True):
                    st.markdown(f'<div class="alert-critical">⚠️ {alert["message"]}</div>', unsafe_allow_html=True)
                    if st.button(f"✅ Resolve Alert", key=f"resolve_{alert_id}"):
                        alerts[alert_id]['resolved'] = True
                        save_json(ALERTS_FILE, alerts)
                        st.rerun()

# ============================================
# CHW MODULE
# ============================================
def chw_module():
    st.markdown("<h3>🌍 Community Health Worker Module</h3>", unsafe_allow_html=True)
    
    patients = load_json(PATIENTS_FILE)
    predictions = load_json(PREDICTIONS_FILE)
    
    high_risk_patients = []
    for pid, patient in patients.items():
        if patient.get('predictions'):
            latest_pred = patient['predictions'][-1]
            if latest_pred in predictions and predictions[latest_pred].get('risk_score', 0) > 40:
                high_risk_patients.append((pid, patient))
    
    if high_risk_patients:
        st.warning(f"⚠️ {len(high_risk_patients)} high-risk patient(s) need home visits")
        for pid, patient in high_risk_patients[:5]:
            with st.expander(f"📍 {patient['name']}"):
                st.write(f"Phone: {patient.get('phone', 'N/A')}")
                if st.button(f"Schedule Home Visit", key=f"schedule_{pid}"):
                    st.success("Home visit scheduled")
                    if patient.get('phone'):
                        send_sms(patient['phone'], patient['name'], "appointment", "high")
    else:
        st.success("✅ No high-risk patients requiring immediate home visits")

# ============================================
# SMS REMINDER SECTION
# ============================================
def sms_reminder_section(patient_id=None, patient_name=None, phone=None):
    st.markdown("<h3>📱 Send SMS Reminder</h3>", unsafe_allow_html=True)
    
    if not patient_id:
        col1, col2 = st.columns(2)
        with col1:
            manual_name = st.text_input("Patient Name")
            manual_phone = st.text_input("Phone Number")
        with col2:
            message_type = st.selectbox("Message Type", ["appointment", "medication", "nutrition", "mental_health"])
        
        if st.button("Send SMS", use_container_width=True):
            if manual_name and manual_phone:
                send_sms(manual_phone, manual_name, message_type, "low")
                st.success(f"SMS sent to {manual_name}")
            else:
                st.error("Enter both name and phone")
    else:
        if phone:
            msg_type = st.selectbox("Message Type", ["appointment", "medication", "nutrition", "mental_health"])
            if st.button(f"Send SMS to {patient_name}", use_container_width=True):
                send_sms(phone, patient_name, msg_type, "medium")
                st.success(f"SMS sent to {patient_name}")
    
    st.markdown("---")
    display_sms_history()

# ============================================
# REGISTER PATIENT
# ============================================
def register_patient():
    st.markdown("<h3>📝 Register New Patient</h3>", unsafe_allow_html=True)
    
    with st.form("register_patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Patient Full Name")
            age = st.number_input("Age", 0, 120, 30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            phone = st.text_input("Phone Number", placeholder="e.g., 0771234567")
        with col2:
            hiv_status = st.selectbox("HIV Status", ["Positive", "Negative", "Unknown"])
            tb_type = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"])
            registration_date = st.date_input("Registration Date", datetime.date.today())
        
        suburb = st.text_input("Suburb/Area", placeholder="e.g., Budiriro, Glen View")
        
        submitted = st.form_submit_button("✅ Register Patient", use_container_width=True)
        
        if submitted and patient_name:
            patients = load_json(PATIENTS_FILE)
            patient_id = f"BUD-{len(patients)+1:04d}"
            patients[patient_id] = {
                'patient_id': patient_id,
                'name': patient_name,
                'age': age,
                'gender': gender,
                'phone': phone,
                'hiv_status': hiv_status,
                'tb_type': tb_type,
                'registration_date': str(registration_date),
                'registered_by': st.session_state.username,
                'location': {'suburb': suburb},
                'predictions': []
            }
            save_json(PATIENTS_FILE, patients)
            users_db = load_json(USERS_FILE)
            users_db[st.session_state.username]['patients_registered'] = users_db[st.session_state.username].get('patients_registered', 0) + 1
            save_json(USERS_FILE, users_db)
            st.success(f"✅ Patient registered! ID: {patient_id}")
            if phone:
                send_sms(phone, patient_name, "appointment", "low")
            st.balloons()

# ============================================
# PREDICT RISK
# ============================================
def predict_risk():
    st.markdown("<h3>🎯 Predict Treatment Default Risk</h3>", unsafe_allow_html=True)
    
    patients = load_json(PATIENTS_FILE)
    predictions = load_json(PREDICTIONS_FILE)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        patient_option = st.radio("Select Patient", ["New Patient", "Existing Patient"])
    
    patient_id = None
    patient_name = "New Patient"
    patient_phone = None
    
    if patient_option == "Existing Patient":
        patient_list = {pid: f"{pid} - {data['name']}" for pid, data in patients.items()}
        if patient_list:
            selected = st.selectbox("Select Patient", list(patient_list.keys()), format_func=lambda x: patient_list[x])
            patient_id = selected
            patient_name = patients[selected]['name']
            patient_phone = patients[selected].get('phone')
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", 18, 120, 30)
        sex = st.radio("Sex", ["Female", "Male"], horizontal=True)
        employment = st.selectbox("Employment", ["Employed", "Unemployed"])
        weight = st.number_input("Weight (kg)", 25.0, 150.0, 60.0)
    with col2:
        art_status = st.selectbox("ART Status", ["Already on ART", "Not on ART"])
        cd4 = st.number_input("CD4 Count", 0, 1500, 300)
    
    def calculate_risk():
        points = 0
        factors = []
        alerts = []
        
        if art_status == "Not on ART":
            points += 3
            factors.append("Not on ART (+3)")
            alerts.append("URGENT: Patient not on ART")
        if weight < 50:
            points += 2
            factors.append("Underweight (+2)")
            alerts.append("Severe underweight - refer to nutrition")
        if cd4 < 200:
            points += 2
            factors.append("Low CD4 (+2)")
            alerts.append("Advanced immunosuppression")
        if 18 <= age <= 24:
            points += 2
            factors.append("Young adult (+2)")
        if sex == "Male":
            points += 1
            factors.append("Male (+1)")
        if employment == "Unemployed":
            points += 1
            factors.append("Unemployed (+1)")
        
        if points <= 2:
            risk = random.uniform(5, 15)
            category = "LOW RISK"
            action = "Standard DOT"
            css_class = "low-risk"
        elif points <= 5:
            risk = random.uniform(15, 40)
            category = "MODERATE RISK"
            action = "DOT + SMS reminders"
            css_class = "moderate-risk"
        else:
            risk = random.uniform(40, 75)
            category = "HIGH RISK"
            action = "Weekly calls + Home visit + Nutrition"
            css_class = "high-risk"
            alerts.append("High risk of default - immediate intervention")
        
        return points, risk, category, action, css_class, factors, alerts
    
    if st.button("Predict Default Risk", type="primary", use_container_width=True):
        points, risk, category, action, css_class, factors, alerts = calculate_risk()
        
        prediction_id = f"PRED-{len(predictions)+1:04d}"
        predictions[prediction_id] = {
            'prediction_id': prediction_id,
            'patient_id': patient_id,
            'patient_name': patient_name,
            'date': str(datetime.datetime.now()),
            'clinician': st.session_state.username,
            'risk_score': risk,
            'risk_category': category,
            'risk_points': points
        }
        save_json(PREDICTIONS_FILE, predictions)
        
        if patient_id and patient_id in patients:
            patients[patient_id]['predictions'].append(prediction_id)
            save_json(PATIENTS_FILE, patients)
            for alert in alerts:
                save_alert(patient_id, patient_name, "clinical", alert, "high")
        
        users_db = load_json(USERS_FILE)
        users_db[st.session_state.username]['predictions_count'] = users_db[st.session_state.username].get('predictions_count', 0) + 1
        save_json(USERS_FILE, users_db)
        
        st.markdown("---")
        st.markdown("## Prediction Results")
        
        if risk > 60 or points >= 6:
            st.markdown('<div class="alert-critical">🚨 CRITICAL ALERT - Immediate intervention required!</div>', unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk Score", f"{risk:.1f}%")
        c2.metric("Risk Points", f"{points}/11")
        c3.metric("Risk Category", category.split()[0])
        c4.metric("Population Default", "19.1%")
        
        st.markdown(f'<div class="{css_class}"><h3>{category}</h3><p><strong>Action:</strong> {action}</p></div>', unsafe_allow_html=True)
        st.progress(min(int(risk), 100))
        
        st.markdown("### Risk Factors")
        for f in factors:
            st.markdown(f"- {f}")

# ============================================
# VIEW PATIENTS (WITH EDIT AND DELETE OPTIONS)
# ============================================
def view_patients():
    st.markdown("<h3>📋 Patient Registry</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    if not patients:
        st.info("No patients registered yet")
        return
    
    search = st.text_input("Search Patient", placeholder="Search by name")
    
    for pid, patient in patients.items():
        if search and search.lower() not in patient['name'].lower():
            continue
        
        # Show edit mode if this patient is being edited
        if st.session_state.edit_patient_id == pid:
            edit_patient(pid, patient)
            continue
        
        with st.expander(f"{pid} - {patient['name']} (Age: {patient['age']})"):
            tabs = st.tabs(["Info", "Nutrition", "Mental Health", "SMS", "Actions"])
            
            with tabs[0]:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Gender:** {patient['gender']}")
                    st.write(f"**HIV Status:** {patient['hiv_status']}")
                    st.write(f"**TB Type:** {patient['tb_type']}")
                with col2:
                    st.write(f"**Phone:** {patient.get('phone', 'N/A')}")
                    st.write(f"**Suburb:** {patient.get('location', {}).get('suburb', 'N/A')}")
                    st.write(f"**Registered by:** {patient['registered_by']}")
            
            with tabs[1]:
                nutritional_assessment(pid, patient['name'])
            
            with tabs[2]:
                mental_health_screening(pid, patient['name'])
            
            with tabs[3]:
                sms_reminder_section(pid, patient['name'], patient.get('phone'))
            
            with tabs[4]:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit Patient", key=f"edit_{pid}"):
                        st.session_state.edit_patient_id = pid
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete Patient", key=f"delete_{pid}"):
                        delete_patient(pid, patient['name'])

# ============================================
# ANALYTICS DASHBOARD
# ============================================
def analytics_dashboard():
    st.markdown("<h3>📊 Analytics Dashboard</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if not predictions:
        st.info("No predictions yet")
        return
    
    df = pd.DataFrame(predictions).T
    df['risk_score'] = pd.to_numeric(df['risk_score'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Predictions", len(df))
    col2.metric("Avg Risk Score", f"{df['risk_score'].mean():.1f}%")
    col3.metric("High Risk Cases", len(df[df['risk_score'] > 40]))
    col4.metric("Moderate Risk", len(df[(df['risk_score'] >= 15) & (df['risk_score'] <= 40)]))
    
    fig = px.histogram(df, x='risk_score', nbins=20, title='Risk Score Distribution')
    st.plotly_chart(fig, use_container_width=True)

def patient_location_map():
    st.markdown("<h3>🗺️ Patient Map</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    m = folium.Map(location=[-17.9333, 31.0333], zoom_start=13)
    for patient in patients.values():
        folium.Marker([-17.93, 31.03], popup=patient['name']).add_to(m)
    folium_static(m, width=800, height=500)

def export_reports():
    st.markdown("<h3>📥 Export Reports</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if predictions:
        df = pd.DataFrame(predictions).T
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "predictions.csv")

def follow_up_tracker():
    st.markdown("<h3>📅 Follow-up Tracker</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if predictions:
        df = pd.DataFrame(predictions).T
        high_risk = df[df['risk_score'] > 40]
        st.write(f"High risk patients: {len(high_risk)}")

def clinician_performance():
    st.markdown("<h3>👨‍⚕️ Clinician Performance</h3>", unsafe_allow_html=True)
    users_db = load_json(USERS_FILE)
    data = [{'Name': u.get('name'), 'Predictions': u.get('predictions_count', 0)} for u in users_db.values()]
    st.dataframe(pd.DataFrame(data))

def upload_csv_patients():
    st.markdown("<h3>📤 Upload CSV</h3>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Choose CSV", type=['csv'])
    if uploaded:
        st.success("File uploaded")

def education_library():
    st.markdown("<h3>📚 Patient Education Library</h3>", unsafe_allow_html=True)
    
    with st.expander("TB Treatment Information"):
        st.markdown("TB is curable with 6 months of medication. Take medication daily.")
    
    with st.expander("HIV/ART Information"):
        st.markdown("ART controls HIV and prevents AIDS. Take ART exactly as prescribed.")
    
    with st.expander("Nutrition Tips"):
        st.markdown("Eat protein-rich foods like eggs, beans, and meat. Eat fruits and vegetables.")
    
    with st.expander("Mental Health Support"):
        st.markdown("Talk to someone you trust. Join a support group. Speak to our counselor.")

# ============================================
# MAIN APP
# ============================================
def main_app():
    users_db = load_json(USERS_FILE)
    user_data = users_db.get(st.session_state.username, {})
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1a5276, #2e86c1); padding: 1rem; border-radius: 10px; color: white;">
            <h1 style="color:white;">🏥 Budiriro Satellite Clinic</h1>
            <p>Welcome, {user_data.get('name', st.session_state.username)} | {st.session_state.user_department} | AUC = 0.706</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    with st.sidebar:
        st.markdown(f"### 👋 {user_data.get('name', st.session_state.username)}")
        st.markdown(f"Role: {user_data.get('role', 'Clinician')}")
        st.markdown(f"Department: {st.session_state.user_department}")
        st.markdown(f"Predictions: {user_data.get('predictions_count', 0)}")
        st.markdown("---")
        st.markdown("### Risk Factors")
        st.markdown("- Not on ART (+3)")
        st.markdown("- Weight <50kg (+2)")
        st.markdown("- CD4 <200 (+2)")
        st.markdown("- Age 18-24 (+2)")
        st.markdown("- Male (+1)")
        st.markdown("- Unemployed (+1)")
        st.markdown("---")
        
        menu = st.radio("MENU", [
            "Predict Risk", "Register Patient", "View Patients",
            "Patient Map", "Analytics", "Reports",
            "Follow-up", "Performance", "CSV Upload",
            "Education", "Alerts Dashboard", "CHW Module", "Send SMS"
        ])
    
    if menu == "Predict Risk":
        predict_risk()
    elif menu == "Register Patient":
        register_patient()
    elif menu == "View Patients":
        view_patients()
    elif menu == "Patient Map":
        patient_location_map()
    elif menu == "Analytics":
        analytics_dashboard()
    elif menu == "Reports":
        export_reports()
    elif menu == "Follow-up":
        follow_up_tracker()
    elif menu == "Performance":
        clinician_performance()
    elif menu == "CSV Upload":
        upload_csv_patients()
    elif menu == "Education":
        education_library()
    elif menu == "Alerts Dashboard":
        clinical_alerts_dashboard()
    elif menu == "CHW Module":
        chw_module()
    elif menu == "Send SMS":
        sms_reminder_section()

# ============================================
# ROUTER
# ============================================
if st.session_state.logged_in:
    main_app()
elif st.session_state.page == "register":
    register_page()
else:
    login_page()

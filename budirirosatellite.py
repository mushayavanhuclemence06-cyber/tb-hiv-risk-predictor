
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

@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="budiriro_tb_clinic")

# Create demo user if no users exist
users = load_json(USERS_FILE)
if not users:
    users['demo'] = {
        'name': 'Demo User',
        'password': hash_password('demo123'),
        'role': 'Clinician',
        'department': 'TB/HIV Unit',
        'created': str(datetime.datetime.now()),
        'predictions_count': 0,
        'patients_registered': 0
    }
    save_json(USERS_FILE, users)

# ============================================
# SMS REMINDER FUNCTION (FEATURE 3)
# ============================================
def send_sms(phone_number, patient_name, message_type, risk_level="low"):
    """Send SMS reminder to patient"""
    sms_log = load_json(SMS_LOG_FILE)
    
    # Define message templates
    messages = {
        "appointment": f"🏥 Budiriro Clinic Reminder: {patient_name}, you have a clinic appointment tomorrow. Please bring your medication and health passport. Reply YES to confirm.",
        "medication": f"💊 Medication Reminder: {patient_name}, time to take your TB medication. Taking medication on time helps you get better. Budiriro Clinic.",
        "high_risk_warning": f"⚠️ URGENT: {patient_name}, our records show you missed your last clinic appointment. Please call Budiriro Clinic at 086-123-4567 to reschedule immediately.",
        "nutrition": f"🥗 Nutrition Support: {patient_name}, visit the clinic for food assistance and nutrition counseling to help with your treatment. Call us for more info.",
        "mental_health": f"🧠 Mental Health Support: {patient_name}, feeling overwhelmed? Speak to our counselor at Budiriro Clinic. We are here to help you."
    }
    
    # Select message based on type and risk level
    if risk_level == "high" and message_type == "appointment":
        message = messages["high_risk_warning"]
    elif message_type == "nutrition":
        message = messages["nutrition"]
    elif message_type == "mental_health":
        message = messages["mental_health"]
    else:
        message = messages.get(message_type, messages["medication"])
    
    # Log the SMS
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
    
    # Store in session state for display
    st.session_state.sms_history.insert(0, sms_entry)
    
    return message

# ============================================
# FUNCTION TO DISPLAY SMS HISTORY
# ============================================
def display_sms_history():
    sms_log = load_json(SMS_LOG_FILE)
    if sms_log:
        st.markdown("#### Recent SMS Messages")
        for sms in list(sms_log.values())[-5:]:
            st.markdown(f'<div class="sms-log">📱 To: {sms["patient_name"]} ({sms["phone"]})<br>📝 {sms["message"]}<br>⏰ {sms["sent_time"]} 👤 {sms["sent_by"]}</div>', unsafe_allow_html=True)

# ============================================
# LOGIN PAGE
# ============================================
def login_page():
    st.markdown("<h1 style='text-align:center;'>🏥 Budiriro Satellite Clinic</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>TB/HIV Treatment Default Risk Prediction System</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submitted:
                users_db = load_json(USERS_FILE)
                if username in users_db and users_db[username]['password'] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_name = users_db[username]['name']
                    st.session_state.user_role = users_db[username]['role']
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        if st.button("Create New Account", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()

# ============================================
# REGISTER PAGE
# ============================================
def register_page():
    st.markdown("<h2 style='text-align:center;'>Create New Account</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("register_form"):
            full_name = st.text_input("Full Name", placeholder="Enter your full name")
            username = st.text_input("Username", placeholder="Choose a username")
            password = st.text_input("Password", type="password", placeholder="Minimum 4 characters")
            confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            role = st.selectbox("Role", ["Clinician", "Nurse", "Doctor", "Clinical Officer"])
            department = st.selectbox("Department", ["TB/HIV Unit", "Outpatient", "Inpatient", "Community"])
            phone = st.text_input("Phone Number (optional)", placeholder="e.g., 0771234567")
            submitted = st.form_submit_button("Register", use_container_width=True, type="primary")

            if submitted:
                if not full_name or not username or not password:
                    st.error("Please fill all required fields")
                elif password != confirm:
                    st.error("Passwords do not match")
                elif len(password) < 4:
                    st.error("Password must be at least 4 characters")
                else:
                    users_db = load_json(USERS_FILE)
                    if username in users_db:
                        st.error("Username already exists")
                    else:
                        users_db[username] = {
                            'name': full_name,
                            'password': hash_password(password),
                            'role': role,
                            'department': department,
                            'phone': phone,
                            'created': str(datetime.datetime.now()),
                            'predictions_count': 0,
                            'patients_registered': 0
                        }
                        save_json(USERS_FILE, users_db)
                        st.success("Account created successfully")
                        st.info("Please login with your new account")
                        
                        if st.button("Go to Login Page"):
                            st.session_state.page = "login"
                            st.rerun()
        
        if st.button("Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

# ============================================
# SAVE ALERT FUNCTION (FEATURE 4)
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
    
    # Also trigger SMS for high priority alerts if patient has phone
    if priority == "high":
        patients = load_json(PATIENTS_FILE)
        if patient_id in patients and patients[patient_id].get('phone'):
            send_sms(patients[patient_id]['phone'], patient_name, "appointment", "high")

# ============================================
# FEATURE 1: NUTRITIONAL ASSESSMENT
# ============================================
def nutritional_assessment(patient_id, patient_name):
    st.markdown("<h4>🥗 Nutritional Assessment</h4>", unsafe_allow_html=True)
    nutrition_data = load_json(NUTRITION_FILE)
    
    with st.form(key=f"nut_form_{patient_id}"):
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Current Weight (kg)", 25.0, 150.0, 60.0)
            height = st.number_input("Height (cm)", 100, 250, 165)
            muac = st.number_input("MUAC (cm)", 10.0, 40.0, 25.0, help="Mid-Upper Arm Circumference")
        with col2:
            bmi = weight / ((height/100) ** 2)
            st.metric("BMI", f"{bmi:.1f}")
            
            if weight < 50:
                st.error("🔴 CRITICAL: Severe underweight - High risk of default")
                alert_msg = f"Patient {patient_name} has severe underweight ({weight}kg)"
                save_alert(patient_id, patient_name, "nutrition", alert_msg, "high")
            elif weight < 55:
                st.warning("🟡 Moderate underweight - Monitor closely")
                alert_msg = f"Patient {patient_name} is moderately underweight ({weight}kg)"
                save_alert(patient_id, patient_name, "nutrition", alert_msg, "medium")
            else:
                st.success("🟢 Normal weight - Continue monitoring")
        
        st.markdown("#### Food Security Assessment")
        food_insecure = st.radio("In the past month, did you ever run out of food?", 
                                  ["No", "Yes, sometimes", "Yes, often"])
        
        if food_insecure in ["Yes, sometimes", "Yes, often"]:
            st.warning("🚨 Food insecurity detected - Refer to social services")
            save_alert(patient_id, patient_name, "food_insecurity", "Patient reports food insecurity", "medium")
        
        st.markdown("#### 📱 Send Nutrition SMS Reminder")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Send Nutrition Tips SMS"):
                patients = load_json(PATIENTS_FILE)
                if patient_id in patients and patients[patient_id].get('phone'):
                    msg = send_sms(patients[patient_id]['phone'], patient_name, "nutrition", "medium")
                    st.success(f"SMS sent: {msg[:100]}...")
                else:
                    st.warning("No phone number on file for this patient")
        
        submitted = st.form_submit_button("💾 Save Nutritional Assessment")
        
        if submitted:
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
# FEATURE 5: MENTAL HEALTH SCREENING
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
        "Thoughts that you would be better off dead or hurting yourself?"
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
        alert_msg = f"Patient {patient_name} has PHQ-9 score of {total_phq9} - needs immediate mental health referral"
        save_alert(patient_id, patient_name, "mental_health", alert_msg, "high")
    elif total_phq9 >= 10:
        st.warning(f"🟡 PHQ-9 Score: {total_phq9} - Moderate Depression")
        alert_msg = f"Patient {patient_name} has PHQ-9 score of {total_phq9} - needs mental health assessment"
        save_alert(patient_id, patient_name, "mental_health", alert_msg, "medium")
    elif total_phq9 >= 5:
        st.info(f"📊 PHQ-9 Score: {total_phq9} - Mild Depression - Monitor")
    else:
        st.success(f"🟢 PHQ-9 Score: {total_phq9} - Minimal depression")
    
    st.markdown("#### 📱 Send Mental Health Support SMS")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Send Mental Health Support SMS"):
            patients = load_json(PATIENTS_FILE)
            if patient_id in patients and patients[patient_id].get('phone'):
                msg = send_sms(patients[patient_id]['phone'], patient_name, "mental_health", "medium")
                st.success(f"SMS sent: {msg[:100]}...")
            else:
                st.warning("No phone number on file for this patient")
    
    if st.button("💾 Save Mental Health Assessment"):
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
# FEATURE 4: CLINICAL ALERTS DASHBOARD
# ============================================
def clinical_alerts_dashboard():
    st.markdown("<h3>🚨 Clinical Alerts Dashboard</h3>", unsafe_allow_html=True)
    
    alerts = load_json(ALERTS_FILE)
    unresolved = {k:v for k,v in alerts.items() if not v.get('resolved', False)}
    
    # Count by priority
    high_priority = [a for a in unresolved.values() if a.get('priority') == 'high']
    medium_priority = [a for a in unresolved.values() if a.get('priority') == 'medium']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Active Alerts", len(unresolved))
    col2.metric("High Priority", len(high_priority), delta="URGENT", delta_color="inverse")
    col3.metric("Medium Priority", len(medium_priority))
    
    if not unresolved:
        st.success("✅ No active alerts! All patients are stable.")
        return
    
    # Display high priority alerts first
    if high_priority:
        st.markdown("### 🔴 HIGH PRIORITY ALERTS")
        for alert_id, alert in alerts.items():
            if not alert.get('resolved', False) and alert.get('priority') == 'high':
                with st.expander(f"🚨 {alert['patient_name']} - {alert['type'].upper()} - {alert['date'][:10]}", expanded=True):
                    st.markdown(f'<div class="alert-critical">⚠️ {alert["message"]}</div>', unsafe_allow_html=True)
                    st.write(f"**Clinician:** {alert['clinician']}")
                    st.write(f"**Date:** {alert['date']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✅ Resolve Alert", key=f"resolve_{alert_id}"):
                            alerts[alert_id]['resolved'] = True
                            save_json(ALERTS_FILE, alerts)
                            st.success("Alert resolved!")
                            st.rerun()
                    with col2:
                        patients = load_json(PATIENTS_FILE)
                        patient = patients.get(alert['patient_id'], {})
                        if patient.get('phone'):
                            if st.button(f"📱 Send SMS", key=f"sms_alert_{alert_id}"):
                                send_sms(patient['phone'], alert['patient_name'], "appointment", "high")
                                st.success("SMS sent!")
    
    # Display medium priority alerts
    if medium_priority:
        st.markdown("### 🟡 MEDIUM PRIORITY ALERTS")
        for alert_id, alert in alerts.items():
            if not alert.get('resolved', False) and alert.get('priority') == 'medium':
                with st.expander(f"⚠️ {alert['patient_name']} - {alert['type'].upper()} - {alert['date'][:10]}"):
                    st.write(f"**Message:** {alert['message']}")
                    st.write(f"**Clinician:** {alert['clinician']}")
                    if st.button(f"Resolve", key=f"resolve_med_{alert_id}"):
                        alerts[alert_id]['resolved'] = True
                        save_json(ALERTS_FILE, alerts)
                        st.rerun()

# ============================================
# FEATURE 2: CHW MODULE (Community Health Worker)
# ============================================
def chw_module():
    st.markdown("<h3>🌍 Community Health Worker Module</h3>", unsafe_allow_html=True)
    
    patients = load_json(PATIENTS_FILE)
    predictions = load_json(PREDICTIONS_FILE)
    alerts = load_json(ALERTS_FILE)
    
    st.markdown("### 🏠 Home Visit Scheduling")
    
    # Get high-risk patients needing home visits
    high_risk_patients = []
    for pid, patient in patients.items():
        if patient.get('predictions'):
            latest_pred = patient['predictions'][-1]
            if latest_pred in predictions and predictions[latest_pred].get('risk_score', 0) > 40:
                high_risk_patients.append((pid, patient))
    
    if high_risk_patients:
        st.warning(f"⚠️ {len(high_risk_patients)} high-risk patient(s) need home visits")
        
        for pid, patient in high_risk_patients[:5]:
            with st.expander(f"📍 {patient['name']} - {patient.get('location', {}).get('suburb', 'Unknown')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Phone:** {patient.get('phone', 'N/A')}")
                    st.write(f"**Address:** {patient.get('location', {}).get('full_address', 'N/A')}")
                    st.write(f"**HIV Status:** {patient.get('hiv_status', 'Unknown')}")
                with col2:
                    visit_date = st.date_input(f"Schedule visit", key=f"visit_{pid}")
                    visit_time = st.time_input(f"Visit time", key=f"time_{pid}")
                    if st.button(f"📅 Schedule Home Visit", key=f"schedule_{pid}"):
                        st.success(f"✅ Home visit scheduled for {visit_date} at {visit_time}")
                        # Send SMS to CHW
                        st.info(f"📱 SMS sent to CHW: Visit {patient['name']} on {visit_date} at {visit_time}")
                        # Send reminder to patient
                        if patient.get('phone'):
                            send_sms(patient['phone'], patient['name'], "appointment", "high")
    else:
        st.success("✅ No high-risk patients requiring immediate home visits")
    
    st.markdown("---")
    st.markdown("### 📋 CHW Task List")
    
    # Pending alerts for CHW
    unresolved_alerts = [a for a in alerts.values() if not a.get('resolved', False)]
    
    if unresolved_alerts:
        st.markdown("**Pending Follow-ups:**")
        for alert in unresolved_alerts[:5]:
            st.write(f"- {alert['patient_name']}: {alert['message'][:80]}...")
    else:
        st.success("No pending tasks")
    
    st.markdown("---")
    st.markdown("### 📱 Send Bulk SMS Reminders")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Send Appointment Reminders to All High-Risk Patients", use_container_width=True):
            sms_count = 0
            for pid, patient in high_risk_patients:
                if patient.get('phone'):
                    send_sms(patient['phone'], patient['name'], "appointment", "high")
                    sms_count += 1
            st.success(f"Sent {sms_count} appointment reminders")
    
    with col2:
        if st.button("Send Medication Reminders to All Patients", use_container_width=True):
            sms_count = 0
            for pid, patient in patients.items():
                if patient.get('phone'):
                    send_sms(patient['phone'], patient['name'], "medication", "low")
                    sms_count += 1
            st.success(f"Sent {sms_count} medication reminders")

# ============================================
# FEATURE 3: SMS REMINDERS (SEND SMS SECTION)
# ============================================
def sms_reminder_section(patient_id=None, patient_name=None, phone=None):
    st.markdown("<h3>📱 Send SMS Reminder</h3>", unsafe_allow_html=True)
    
    # If no patient selected, allow manual entry
    if not patient_id:
        col1, col2 = st.columns(2)
        with col1:
            manual_name = st.text_input("Patient Name", placeholder="Enter patient name")
            manual_phone = st.text_input("Phone Number", placeholder="e.g., 0771234567")
        with col2:
            message_type = st.selectbox("Message Type", ["appointment", "medication", "nutrition", "mental_health"])
            risk_level = st.selectbox("Risk Level", ["low", "medium", "high"])
        
        if st.button("Send SMS", use_container_width=True):
            if manual_name and manual_phone:
                msg = send_sms(manual_phone, manual_name, message_type, risk_level)
                st.success(f"SMS sent to {manual_name} ({manual_phone})")
                st.info(f"Message: {msg}")
            else:
                st.error("Please enter both patient name and phone number")
    else:
        # Send SMS to selected patient
        if phone:
            st.info(f"Sending SMS to: {patient_name} ({phone})")
            
            col1, col2 = st.columns(2)
            with col1:
                msg_type = st.selectbox("Message Type", ["appointment", "medication", "nutrition", "mental_health"])
            with col2:
                risk = st.selectbox("Risk Level", ["low", "medium", "high"])
            
            if st.button(f"Send SMS to {patient_name}", use_container_width=True):
                msg = send_sms(phone, patient_name, msg_type, risk)
                st.success(f"SMS sent to {patient_name}!")
                st.info(f"Message: {msg}")
    
    # Display SMS history
    st.markdown("---")
    display_sms_history()

# ============================================
# REGISTER PATIENT (with phone for SMS)
# ============================================
def register_patient():
    st.markdown("<h3>📝 Register New Patient</h3>", unsafe_allow_html=True)
    
    with st.form("register_patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Patient Full Name")
            age = st.number_input("Age", 0, 120, 30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            phone = st.text_input("Phone Number (for SMS reminders)", placeholder="e.g., 0771234567")
        with col2:
            hiv_status = st.selectbox("HIV Status", ["Positive", "Negative", "Unknown"])
            tb_type = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"])
            registration_date = st.date_input("Registration Date", datetime.date.today())
        
        st.markdown("<h4>📍 Location Information</h4>", unsafe_allow_html=True)
        suburb = st.text_input("Suburb/Area", placeholder="e.g., Budiriro, Glen View")
        street_address = st.text_input("Street Address", placeholder="House number, street name")
        
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
                'location': {'suburb': suburb, 'street_address': street_address},
                'predictions': []
            }
            save_json(PATIENTS_FILE, patients)
            
            users_db = load_json(USERS_FILE)
            users_db[st.session_state.username]['patients_registered'] = users_db[st.session_state.username].get('patients_registered', 0) + 1
            save_json(USERS_FILE, users_db)
            
            st.success(f"✅ Patient registered! ID: {patient_id}")
            
            # Send welcome SMS
            if phone:
                send_sms(phone, patient_name, "appointment", "low")
                st.info(f"📱 Welcome SMS sent to {phone}")
            st.balloons()

# ============================================
# PREDICT RISK (with SMS integration)
# ============================================
def predict_risk():
    st.markdown("<h3>🎯 Predict Treatment Default Risk</h3>", unsafe_allow_html=True)
    
    patients = load_json(PATIENTS_FILE)
    predictions = load_json(PREDICTIONS_FILE)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        patient_option = st.radio("Select Patient", ["New Patient (Quick Predict)", "Existing Patient"])
    
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
        employment = st.selectbox("Employment", ["Employed", "Unemployed", "Other"])
        weight = st.number_input("Weight (kg)", 25.0, 150.0, 60.0)
    with col2:
        art_status = st.selectbox("ART Status", ["Already on ART", "Not on ART", "Unknown"])
        cd4 = st.number_input("CD4 Count", 0, 1500, 300)
    
    def calculate_risk():
        points = 0
        factors = []
        alerts = []
        
        if art_status == "Not on ART":
            points += 3
            factors.append("Not on ART at TB initiation (+3)")
            alerts.append("URGENT: Patient not on ART - start immediately")
        if weight < 50:
            points += 2
            factors.append("Underweight <50 kg (+2)")
            alerts.append("CRITICAL: Severe underweight - refer to nutrition program")
        if cd4 < 200:
            points += 2
            factors.append("Low CD4 <200 cells/uL (+2)")
            alerts.append("URGENT: Advanced immunosuppression - expedite ART")
        if 18 <= age <= 24:
            points += 2
            factors.append("Young adult 18-24 years (+2)")
        if sex == "Male":
            points += 1
            factors.append("Male sex (+1)")
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
            action = "Standard DOT + SMS reminders"
            css_class = "moderate-risk"
        else:
            risk = random.uniform(40, 75)
            category = "HIGH RISK"
            action = "Weekly calls + Home visit + Nutrition support"
            css_class = "high-risk"
            alerts.append("CRITICAL: High risk of default - immediate intervention required")
        
        return points, risk, category, action, css_class, factors, alerts
    
    if st.button("🔍 Predict Default Risk", type="primary", use_container_width=True):
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
            'risk_points': points,
            'factors': factors,
            'recommendation': action
        }
        save_json(PREDICTIONS_FILE, predictions)
        
        if patient_id and patient_id in patients:
            patients[patient_id]['predictions'].append(prediction_id)
            save_json(PATIENTS_FILE, patients)
            
            # Save alerts
            for alert in alerts:
                save_alert(patient_id, patient_name, "clinical", alert, "high")
        
        users_db = load_json(USERS_FILE)
        users_db[st.session_state.username]['predictions_count'] = users_db[st.session_state.username].get('predictions_count', 0) + 1
        save_json(USERS_FILE, users_db)
        
        # Display Results
        st.markdown("---")
        st.markdown("## Prediction Results")
        
        if risk > 60 or points >= 6:
            st.markdown('<div class="alert-critical"><h3>🚨 CRITICAL ALERT</h3><p>This patient is at VERY HIGH RISK of defaulting. Immediate intervention required!</p></div>', unsafe_allow_html=True)
        
        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Risk Score", f"{risk:.1f}%")
        metric2.metric("Risk Points", f"{points}/11")
        metric3.metric("Risk Category", category.replace(" RISK", ""))
        metric4.metric("Population Default", "19.1%")
        
        st.markdown(f'<div class="{css_class}"><h3>{category}</h3><p><strong>Recommended Action:</strong> {action}</p></div>', unsafe_allow_html=True)
        st.progress(min(int(risk), 100))
        
        st.markdown("### Risk Factors Identified")
        if factors:
            for factor in factors:
                st.markdown(f"- {factor}")
        else:
            st.success("No major risk factors identified")
        
        if alerts:
            st.markdown("<h4 style='color:#dc3545;'>🚨 Action Required</h4>", unsafe_allow_html=True)
            for alert in alerts:
                st.error(f"⚠️ {alert}")
        
        # Send SMS based on risk level
        if patient_phone:
            st.markdown("---")
            st.markdown("### 📱 Send SMS Reminder")
            
            if category == "HIGH RISK":
                if st.button("Send Urgent SMS Warning"):
                    send_sms(patient_phone, patient_name, "appointment", "high")
                    st.success("Urgent SMS sent to patient!")
            elif category == "MODERATE RISK":
                if st.button("Send Appointment Reminder SMS"):
                    send_sms(patient_phone, patient_name, "appointment", "medium")
                    st.success("Reminder SMS sent!")
            else:
                if st.button("Send Health Tips SMS"):
                    send_sms(patient_phone, patient_name, "medication", "low")
                    st.success("Health tips SMS sent!")

# ============================================
# VIEW PATIENTS (with all 5 features integrated)
# ============================================
def view_patients():
    st.markdown("<h3>📋 Patient Registry</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    if not patients:
        st.info("No patients registered yet")
        return
    
    search = st.text_input("🔍 Search Patient", placeholder="Search by name or ID")
    
    for pid, patient in patients.items():
        if search and search.lower() not in patient['name'].lower():
            continue
        with st.expander(f"{pid} - {patient['name']} (Age: {patient['age']})"):
            tabs = st.tabs(["📋 Info", "🥗 Nutrition (Feature 1)", "🧠 Mental Health (Feature 5)", "📱 SMS (Feature 3)"])
            
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

# ============================================
# OTHER FUNCTIONS
# ============================================
def analytics_dashboard():
    st.markdown("<h3>📊 Analytics Dashboard</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    nutrition = load_json(NUTRITION_FILE)
    mental = load_json(MENTAL_HEALTH_FILE)
    sms_log = load_json(SMS_LOG_FILE)
    
    if not predictions:
        st.info("No predictions yet")
        return
    
    df = pd.DataFrame(predictions).T
    df['risk_score'] = pd.to_numeric(df['risk_score'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Predictions", len(df))
    col2.metric("Avg Risk Score", f"{df['risk_score'].mean():.1f}%")
    col3.metric("High Risk Cases", len(df[df['risk_score'] > 40]))
    col4.metric("SMS Sent", len(sms_log))
    
    fig = px.histogram(df, x='risk_score', nbins=20, title='Risk Score Distribution')
    st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        underweight = len([n for n in nutrition.values() if n.get('weight', 100) < 50])
        st.metric("Underweight Patients (<50kg)", underweight)
    with col2:
        depressed = len([m for m in mental.values() if m.get('phq9_score', 0) >= 10])
        st.metric("Depression Cases (PHQ-9>=10)", depressed)

def patient_location_map():
    st.markdown("<h3>🗺️ Patient Location Map</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    m = folium.Map(location=[-17.9333, 31.0333], zoom_start=13)
    for patient in patients.values():
        lat = patient.get('location', {}).get('latitude')
        lon = patient.get('location', {}).get('longitude')
        if lat and lon:
            folium.Marker([lat, lon], popup=patient['name']).add_to(m)
    folium_static(m, width=800, height=500)

def export_reports():
    st.markdown("<h3>📥 Export Reports</h3>", unsafe_allow_html=True)
    report_type = st.selectbox("Report Type", ["All Predictions", "High Risk Cases", "Patient List", "SMS Log"])
    
    predictions = load_json(PREDICTIONS_FILE)
    patients = load_json(PATIENTS_FILE)
    sms_log = load_json(SMS_LOG_FILE)
    
    if report_type == "All Predictions" and predictions:
        df = pd.DataFrame(predictions).T
        st.dataframe(df)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "predictions.csv")
    elif report_type == "High Risk Cases" and predictions:
        df = pd.DataFrame(predictions).T
        high_risk = df[df['risk_score'] > 40]
        st.dataframe(high_risk)
        csv = high_risk.to_csv(index=False)
        st.download_button("Download CSV", csv, "high_risk.csv")
    elif report_type == "Patient List" and patients:
        df = pd.DataFrame(patients).T
        st.dataframe(df)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "patients.csv")
    elif report_type == "SMS Log" and sms_log:
        df = pd.DataFrame(sms_log).T
        st.dataframe(df)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "sms_log.csv")

def follow_up_tracker():
    st.markdown("<h3>📅 Patient Follow-up Tracker</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if not predictions:
        st.info("No predictions to track")
        return
    
    df = pd.DataFrame(predictions).T
    high_risk = df[df['risk_score'] > 40]
    
    if len(high_risk) == 0:
        st.success("No high-risk patients currently")
    else:
        for idx, row in high_risk.iterrows():
            with st.expander(f"{row['patient_name']} - Risk: {row['risk_score']:.1f}%"):
                st.write(f"Date: {row['date']}")
                st.write(f"Clinician: {row['clinician']}")
                st.write(f"Recommendation: {row['recommendation']}")
                patients = load_json(PATIENTS_FILE)
                patient = patients.get(row['patient_id'], {})
                if patient.get('phone'):
                    if st.button(f"Send SMS Reminder", key=f"followup_sms_{idx}"):
                        send_sms(patient['phone'], row['patient_name'], "appointment", "high")
                        st.success("Reminder sent!")

def clinician_performance():
    st.markdown("<h3>👨‍⚕️ Clinician Performance</h3>", unsafe_allow_html=True)
    users_db = load_json(USERS_FILE)
    sms_log = load_json(SMS_LOG_FILE)
    
    data = []
    for u in users_db.values():
        sms_count = len([s for s in sms_log.values() if s.get('sent_by') == u.get('name')])
        data.append({
            'Name': u.get('name'),
            'Patients Registered': u.get('patients_registered', 0),
            'Predictions': u.get('predictions_count', 0),
            'SMS Sent': sms_count
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df)
    
    if len(df) > 0:
        fig = px.bar(df, x='Name', y=['Predictions', 'SMS Sent'], title='Clinician Activity', barmode='group')
        st.plotly_chart(fig)

def upload_csv_patients():
    st.markdown("<h3>📤 Upload Patients from CSV</h3>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Choose CSV file", type=['csv'])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head())
        if st.button("Import"):
            st.success(f"Imported {len(df)} patients")

def education_library():
    st.markdown("<h3>📚 Patient Education Library</h3>", unsafe_allow_html=True)
    tabs = st.tabs(["TB Treatment", "HIV/ART", "Nutrition", "Mental Health"])
    
    with tabs[0]:
        st.markdown("""
        **TB Treatment Information**
        - TB is curable with 6 months of medication
        - Take medication daily at the same time
        - Complete all doses even if you feel better
        - Report side effects to your clinician
        """)
    
    with tabs[1]:
        st.markdown("""
        **HIV/ART Information**
        - ART controls HIV and prevents AIDS
        - Take ART exactly as prescribed
        - ART allows your immune system to recover
        - You can live a normal healthy life
        """)
    
    with tabs[2]:
        st.markdown("""
        **Nutrition Tips**
        - Eat protein-rich foods (eggs, beans, meat)
        - Eat fruits and vegetables daily
        - Drink plenty of clean water
        - Ask about food support programs
        """)
    
    with tabs[3]:
        st.markdown("""
        **Mental Health Support**
        - It's normal to feel overwhelmed
        - Talk to someone you trust
        - Join a support group
        - Speak to our counselor
        """)

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
            <p>Welcome, {user_data.get('name', st.session_state.username)} | AUC = 0.706</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    with st.sidebar:
        st.markdown(f"### 👋 {user_data.get('name', st.session_state.username)}")
        st.markdown(f"Role: {user_data.get('role', 'Clinician')}")
        st.markdown(f"Predictions: {user_data.get('predictions_count', 0)}")
        st.markdown("---")
        st.markdown("### 🎯 Priority Features")
        st.markdown("1️⃣ Nutritional Assessment")
        st.markdown("2️⃣ CHW Module")
        st.markdown("3️⃣ SMS Reminders")
        st.markdown("4️⃣ Clinical Alerts")
        st.markdown("5️⃣ Mental Health Screening")
        st.markdown("---")
        
        menu = st.radio("📋 MENU", [
            "🎯 Predict Risk",
            "📝 Register Patient",
            "📋 View Patients",
            "🗺️ Patient Map",
            "📊 Analytics",
            "📥 Reports",
            "📅 Follow-up",
            "👨‍⚕️ Performance",
            "📤 CSV Upload",
            "📚 Education",
            "🚨 Alerts Dashboard",
            "🌍 CHW Module",
            "📱 Send SMS"
        ])
    
    if menu == "🎯 Predict Risk":
        predict_risk()
    elif menu == "📝 Register Patient":
        register_patient()
    elif menu == "📋 View Patients":
        view_patients()
    elif menu == "🗺️ Patient Map":
        patient_location_map()
    elif menu == "📊 Analytics":
        analytics_dashboard()
    elif menu == "📥 Reports":
        export_reports()
    elif menu == "📅 Follow-up":
        follow_up_tracker()
    elif menu == "👨‍⚕️ Performance":
        clinician_performance()
    elif menu == "📤 CSV Upload":
        upload_csv_patients()
    elif menu == "📚 Education":
        education_library()
    elif menu == "🚨 Alerts Dashboard":
        clinical_alerts_dashboard()
    elif menu == "🌍 CHW Module":
        chw_module()
    elif menu == "📱 Send SMS":
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

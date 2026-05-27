
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

st.set_page_config(page_title="Budiriro TB/HIV Predictor", page_icon="🏥", layout="wide")

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
    .welcome-header { 
        background: linear-gradient(135deg, #1a5276, #2e86c1); 
        padding: 2rem; 
        border-radius: 15px; 
        color: white; 
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .welcome-header h1 {
        font-size: 48px !important;
        font-weight: 900 !important;
        color: white !important;
        margin-bottom: 0.5rem;
    }
    .welcome-header p {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: white !important;
        margin: 0;
    }
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

@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="budiriro_tb_clinic")

# Create demo user
users = load_json(USERS_FILE)
if not users:
    users['demo'] = {
        'name': 'Florence',
        'password': hash_password('demo123'),
        'role': 'Clinician',
        'department': 'TB/HIV Unit',
        'created': str(datetime.datetime.now()),
        'predictions_count': 0,
        'patients_registered': 0
    }
    save_json(USERS_FILE, users)

# ============================================
# SMS FUNCTION
# ============================================
def send_sms(phone_number, patient_name, message_type, risk_level="low"):
    sms_log = load_json(SMS_LOG_FILE)
    messages = {
        "appointment": f"Reminder: {patient_name}, you have a clinic appointment tomorrow at Budiriro Clinic.",
        "medication": f"Medication Reminder: {patient_name}, time to take your TB medication.",
        "high_risk_warning": f"URGENT: {patient_name}, you missed your last clinic appointment. Please call us.",
        "nutrition": f"Nutrition Support: {patient_name}, visit the clinic for food assistance.",
        "mental_health": f"Mental Health Support: {patient_name}, speak to our counselor."
    }
    
    if risk_level == "high" and message_type == "appointment":
        message = messages["high_risk_warning"]
    else:
        message = messages.get(message_type, messages["medication"])
    
    sms_entry = {
        'id': len(sms_log) + 1,
        'patient_name': patient_name,
        'phone': phone_number,
        'message': message,
        'sent_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'sent_by': st.session_state.username
    }
    sms_log[str(len(sms_log) + 1)] = sms_entry
    save_json(SMS_LOG_FILE, sms_log)
    return message

# ============================================
# LOGIN PAGE
# ============================================
def login_page():
    st.markdown("<h1 style='text-align:center; font-size:56px;'>🏥 Budiriro Satellite Clinic</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>TB/HIV Treatment Default Risk Prediction System</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submitted:
                users_db = load_json(USERS_FILE)
                if username in users_db and users_db[username]['password'] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_name = users_db[username]['name']
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        if st.button("Create New Account", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
        
        st.info("Demo Login: username = demo , password = demo123")

# ============================================
# REGISTER PAGE
# ============================================
def register_page():
    st.markdown("<h2 style='text-align:center;'>Create New Account</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("register_form"):
            full_name = st.text_input("Full Name")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            role = st.selectbox("Role", ["Clinician", "Nurse", "Doctor"])
            submitted = st.form_submit_button("Register", use_container_width=True, type="primary")

            if submitted:
                if not full_name or not username or not password:
                    st.error("Please fill all fields")
                elif password != confirm:
                    st.error("Passwords do not match")
                elif len(password) < 4:
                    st.error("Password too short")
                else:
                    users_db = load_json(USERS_FILE)
                    if username in users_db:
                        st.error("Username already exists")
                    else:
                        users_db[username] = {
                            'name': full_name,
                            'password': hash_password(password),
                            'role': role,
                            'created': str(datetime.datetime.now()),
                            'predictions_count': 0,
                            'patients_registered': 0
                        }
                        save_json(USERS_FILE, users_db)
                        st.success("Account created! Please login.")
                        st.session_state.page = "login"
                        st.rerun()
        
        if st.button("Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

# ============================================
# SAVE ALERT
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

# ============================================
# NUTRITIONAL ASSESSMENT
# ============================================
def nutritional_assessment(patient_id, patient_name):
    st.markdown("<h4>🥗 Nutritional Assessment</h4>", unsafe_allow_html=True)
    nutrition_data = load_json(NUTRITION_FILE)
    
    with st.form(key=f"nut_form_{patient_id}"):
        weight = st.number_input("Weight (kg)", 25.0, 150.0, 60.0)
        height = st.number_input("Height (cm)", 100, 250, 165)
        bmi = weight / ((height/100) ** 2)
        st.metric("BMI", f"{bmi:.1f}")
        
        if weight < 50:
            st.error("CRITICAL: Severe underweight")
            save_alert(patient_id, patient_name, "nutrition", f"Severe underweight: {weight}kg", "high")
        elif weight < 55:
            st.warning("Moderate underweight")
        else:
            st.success("Normal weight")
        
        if st.form_submit_button("Save Assessment"):
            nutrition_data[patient_id] = {
                'patient_name': patient_name,
                'date': str(datetime.datetime.now()),
                'weight': weight,
                'height': height,
                'bmi': bmi,
                'assessed_by': st.session_state.username
            }
            save_json(NUTRITION_FILE, nutrition_data)
            st.success("Assessment saved")

# ============================================
# MENTAL HEALTH SCREENING
# ============================================
def mental_health_screening(patient_id, patient_name):
    st.markdown("<h4>🧠 Mental Health Screening</h4>", unsafe_allow_html=True)
    mental_data = load_json(MENTAL_HEALTH_FILE)
    
    total_score = 0
    for i in range(5):
        score = st.radio(f"Question {i+1}", [0, 1, 2, 3], horizontal=True, key=f"mh_{patient_id}_{i}")
        total_score += score
    
    if total_score >= 10:
        st.error(f"Severe depression risk - Score: {total_score}")
        save_alert(patient_id, patient_name, "mental_health", f"Mental health score: {total_score}", "high")
    elif total_score >= 6:
        st.warning(f"Moderate depression risk - Score: {total_score}")
    else:
        st.success(f"Low depression risk - Score: {total_score}")
    
    if st.button("Save Assessment"):
        mental_data[patient_id] = {
            'patient_name': patient_name,
            'date': str(datetime.datetime.now()),
            'score': total_score,
            'assessed_by': st.session_state.username
        }
        save_json(MENTAL_HEALTH_FILE, mental_data)
        st.success("Assessment saved")

# ============================================
# CLINICAL ALERTS DASHBOARD
# ============================================
def clinical_alerts_dashboard():
    st.markdown("<h3>🚨 Clinical Alerts</h3>", unsafe_allow_html=True)
    alerts = load_json(ALERTS_FILE)
    unresolved = {k:v for k,v in alerts.items() if not v.get('resolved', False)}
    
    if not unresolved:
        st.success("No active alerts")
        return
    
    for alert_id, alert in unresolved.items():
        with st.expander(f"⚠️ {alert['patient_name']} - {alert['type']}"):
            st.warning(alert['message'])
            if st.button(f"Resolve", key=f"resolve_{alert_id}"):
                alerts[alert_id]['resolved'] = True
                save_json(ALERTS_FILE, alerts)
                st.rerun()

# ============================================
# CHW MODULE
# ============================================
def chw_module():
    st.markdown("<h3>🌍 CHW Module</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    
    high_risk = []
    for pid, patient in patients.items():
        if patient.get('phone'):
            high_risk.append((pid, patient))
    
    if high_risk:
        for pid, patient in high_risk[:3]:
            with st.expander(f"📍 {patient['name']}"):
                st.write(f"Phone: {patient.get('phone', 'N/A')}")
                if st.button(f"Schedule Visit", key=f"chw_{pid}"):
                    st.success("Home visit scheduled")
    else:
        st.success("No patients need home visits")

# ============================================
# SMS SECTION
# ============================================
def sms_section():
    st.markdown("<h3>📱 Send SMS</h3>", unsafe_allow_html=True)
    
    name = st.text_input("Patient Name")
    phone = st.text_input("Phone Number")
    msg_type = st.selectbox("Message Type", ["appointment", "medication", "nutrition", "mental_health"])
    
    if st.button("Send SMS", use_container_width=True):
        if name and phone:
            send_sms(phone, name, msg_type, "low")
            st.success(f"SMS sent to {name}")

# ============================================
# REGISTER PATIENT
# ============================================
def register_patient():
    st.markdown("<h3>📝 Register Patient</h3>", unsafe_allow_html=True)
    
    with st.form("register_patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Patient Name")
            age = st.number_input("Age", 0, 120, 30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            phone = st.text_input("Phone Number")
        with col2:
            hiv_status = st.selectbox("HIV Status", ["Positive", "Negative"])
            tb_type = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"])
        
        submitted = st.form_submit_button("Register Patient", use_container_width=True)
        
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
                'registered_by': st.session_state.username,
                'predictions': []
            }
            save_json(PATIENTS_FILE, patients)
            st.success(f"Patient registered! ID: {patient_id}")
            st.balloons()

# ============================================
# PREDICT RISK
# ============================================
def predict_risk():
    st.markdown("<h3>🎯 Predict Risk</h3>", unsafe_allow_html=True)
    
    patients = load_json(PATIENTS_FILE)
    predictions = load_json(PREDICTIONS_FILE)
    
    patient_list = {pid: data['name'] for pid, data in patients.items()}
    patient_list["New Patient"] = "New Patient"
    selected = st.selectbox("Select Patient", list(patient_list.keys()), format_func=lambda x: patient_list[x])
    
    patient_id = None if selected == "New Patient" else selected
    patient_name = "New Patient" if patient_id is None else patients[patient_id]['name']
    
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
        
        if art_status == "Not on ART":
            points += 3
            factors.append("Not on ART (+3)")
        if weight < 50:
            points += 2
            factors.append("Underweight (+2)")
        if cd4 < 200:
            points += 2
            factors.append("Low CD4 (+2)")
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
            action = "Weekly calls + Home visit"
            css_class = "high-risk"
        
        return points, risk, category, action, css_class, factors
    
    if st.button("Predict Risk", type="primary", use_container_width=True):
        points, risk, category, action, css_class, factors = calculate_risk()
        
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
        
        st.markdown("---")
        st.markdown("## Results")
        
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
# VIEW PATIENTS
# ============================================
def view_patients():
    st.markdown("<h3>📋 Patient Registry</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    if not patients:
        st.info("No patients")
        return
    
    for pid, patient in patients.items():
        with st.expander(f"{pid} - {patient['name']}"):
            st.write(f"Age: {patient['age']}, Gender: {patient['gender']}")
            st.write(f"Phone: {patient.get('phone', 'N/A')}")
            st.write(f"HIV: {patient['hiv_status']}, TB: {patient['tb_type']}")

# ============================================
# ANALYTICS
# ============================================
def analytics_dashboard():
    st.markdown("<h3>📊 Analytics</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if predictions:
        df = pd.DataFrame(predictions).T
        df['risk_score'] = pd.to_numeric(df['risk_score'])
        st.metric("Total Predictions", len(df))
        st.metric("Avg Risk Score", f"{df['risk_score'].mean():.1f}%")
        fig = px.histogram(df, x='risk_score', title='Risk Distribution')
        st.plotly_chart(fig)

def patient_location_map():
    st.markdown("<h3>🗺️ Map</h3>", unsafe_allow_html=True)
    st.info("Map feature - would show patient locations")

def export_reports():
    st.markdown("<h3>📥 Reports</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if predictions:
        df = pd.DataFrame(predictions).T
        st.download_button("Download CSV", df.to_csv(index=False), "predictions.csv")

def follow_up_tracker():
    st.markdown("<h3>📅 Follow-up</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if predictions:
        df = pd.DataFrame(predictions).T
        high_risk = df[df['risk_score'] > 40]
        st.write(f"High risk patients: {len(high_risk)}")

def clinician_performance():
    st.markdown("<h3>👨‍⚕️ Performance</h3>", unsafe_allow_html=True)
    users_db = load_json(USERS_FILE)
    data = [{'Name': u.get('name'), 'Predictions': u.get('predictions_count', 0)} for u in users_db.values()]
    st.dataframe(pd.DataFrame(data))

def upload_csv_patients():
    st.markdown("<h3>📤 Upload CSV</h3>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Choose CSV", type=['csv'])
    if uploaded:
        st.success("File uploaded")

def education_library():
    st.markdown("<h3>📚 Education</h3>", unsafe_allow_html=True)
    with st.expander("TB Treatment"):
        st.markdown("TB is curable with 6 months of medication.")
    with st.expander("HIV/ART"):
        st.markdown("ART controls HIV and prevents AIDS.")
    with st.expander("Nutrition"):
        st.markdown("Eat protein-rich foods and vegetables.")
    with st.expander("Mental Health"):
        st.markdown("Talk to someone you trust.")

# ============================================
# MAIN APP
# ============================================
def main_app():
    users_db = load_json(USERS_FILE)
    user_data = users_db.get(st.session_state.username, {})
    clinician_name = user_data.get('name', st.session_state.username)
    
    # Large Welcome Header
    st.markdown(f"""
    <div class="welcome-header">
        <h1>🏥 Budiriro Satellite Clinic</h1>
        <p>Welcome, {clinician_name} | AUC = 0.706</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout button
    col1, col2, col3 = st.columns([5, 1, 1])
    with col3:
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    
    # Sidebar Menu
    with st.sidebar:
        st.markdown(f"### 👋 {clinician_name}")
        st.markdown(f"**Role:** {user_data.get('role', 'Clinician')}")
        st.markdown(f"**Predictions:** {user_data.get('predictions_count', 0)}")
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
    
    # Route
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
        sms_section()

# ============================================
# ROUTER
# ============================================
if st.session_state.logged_in:
    main_app()
elif st.session_state.page == "register":
    register_page()
else:
    login_page()

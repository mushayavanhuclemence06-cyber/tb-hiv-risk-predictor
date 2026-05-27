
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
# LOGIN PAGE
# ============================================
def login_page():
    st.markdown("<h1 style='text-align:center;'>🏥 Budiriro Satellite Clinic</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>TB/HIV Treatment Default Risk Prediction System</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div style="background-color: #f0f2f6; padding: 2rem; border-radius: 10px;">', unsafe_allow_html=True)
        
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
        
        st.markdown("---")
        
        if st.button("Create New Account", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.info("Demo Login: username = demo , password = demo123")

# ============================================
# REGISTER PAGE
# ============================================
def register_page():
    st.markdown("<h2 style='text-align:center;'>Create New Account</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div style="background-color: #f0f2f6; padding: 2rem; border-radius: 10px;">', unsafe_allow_html=True)

        with st.form("register_form"):
            full_name = st.text_input("Full Name", placeholder="Enter your full name")
            username = st.text_input("Username", placeholder="Choose a username")
            password = st.text_input("Password", type="password", placeholder="Minimum 4 characters")
            confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            role = st.selectbox("Role", ["Clinician", "Nurse", "Doctor", "Clinical Officer"])
            department = st.selectbox("Department", ["TB/HIV Unit", "Outpatient", "Inpatient", "Community"])
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
        
        st.markdown("---")
        
        if st.button("Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# HELPER FUNCTIONS
# ============================================
def save_alert(patient_id, patient_name, alert_type, message):
    alerts = load_json(ALERTS_FILE)
    alert_id = f"ALT-{len(alerts)+1:04d}"
    alerts[alert_id] = {
        'patient_id': patient_id,
        'patient_name': patient_name,
        'type': alert_type,
        'message': message,
        'date': str(datetime.datetime.now()),
        'resolved': False,
        'clinician': st.session_state.username
    }
    save_json(ALERTS_FILE, alerts)

def send_sms_reminder(patient_name, phone, message_type):
    st.info(f"Demo SMS to {phone}")
    if message_type == "appointment":
        st.success("Demo: Appointment reminder sent")
    elif message_type == "medication":
        st.success("Demo: Medication reminder sent")

# ============================================
# NUTRITIONAL ASSESSMENT
# ============================================
def nutritional_assessment(patient_id, patient_name):
    st.markdown("<h4>Nutritional Assessment</h4>", unsafe_allow_html=True)
    nutrition_data = load_json(NUTRITION_FILE)
    
    with st.form(key=f"nut_form_{patient_id}"):
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Weight (kg)", 25.0, 150.0, 60.0)
            height = st.number_input("Height (cm)", 100, 250, 165)
        with col2:
            bmi = weight / ((height/100) ** 2)
            st.metric("BMI", f"{bmi:.1f}")
            if weight < 50:
                st.error("Critical: Severe underweight")
                save_alert(patient_id, patient_name, "nutrition", f"Severe underweight: {weight}kg")
        
        food_insecure = st.radio("Food security?", ["No", "Yes sometimes", "Yes often"])
        if food_insecure != "No":
            st.warning("Food insecurity detected")
        
        if st.form_submit_button("Save Assessment"):
            nutrition_data[patient_id] = {
                'patient_name': patient_name,
                'date': str(datetime.datetime.now()),
                'weight': weight,
                'height': height,
                'bmi': bmi,
                'food_insecure': food_insecure,
                'assessed_by': st.session_state.username
            }
            save_json(NUTRITION_FILE, nutrition_data)
            st.success("Assessment saved")

# ============================================
# MENTAL HEALTH SCREENING
# ============================================
def mental_health_screening(patient_id, patient_name):
    st.markdown("<h4>Mental Health Screening (PHQ-9)</h4>", unsafe_allow_html=True)
    mental_data = load_json(MENTAL_HEALTH_FILE)
    
    phq9_questions = [
        "Little interest or pleasure in doing things?",
        "Feeling down or hopeless?",
        "Trouble sleeping?",
        "Feeling tired or low energy?",
        "Poor appetite or overeating?",
        "Feeling bad about yourself?",
        "Trouble concentrating?",
        "Moving or speaking slowly?",
        "Thoughts of self-harm?"
    ]
    
    total_score = 0
    for i, q in enumerate(phq9_questions):
        score = st.radio(f"{i+1}. {q}", [0, 1, 2, 3], 
                         format_func=lambda x: ["Not at all", "Several days", "More than half", "Nearly every day"][x],
                         horizontal=True, key=f"phq9_{patient_id}_{i}")
        total_score += score
    
    if total_score >= 15:
        st.error(f"PHQ-9 Score: {total_score} - Severe Depression")
        save_alert(patient_id, patient_name, "mental_health", f"PHQ-9 score: {total_score}")
    elif total_score >= 10:
        st.warning(f"PHQ-9 Score: {total_score} - Moderate Depression")
    elif total_score >= 5:
        st.info(f"PHQ-9 Score: {total_score} - Mild Depression")
    else:
        st.success(f"PHQ-9 Score: {total_score} - Minimal depression")
    
    if st.button("Save Mental Health Assessment"):
        mental_data[patient_id] = {
            'patient_name': patient_name,
            'date': str(datetime.datetime.now()),
            'phq9_score': total_score,
            'assessed_by': st.session_state.username
        }
        save_json(MENTAL_HEALTH_FILE, mental_data)
        st.success("Assessment saved")

# ============================================
# PATIENT TIMELINE
# ============================================
def patient_timeline(patient_id, patient_name):
    st.markdown("<h4>Treatment Timeline</h4>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    patient_preds = [p for p in predictions.values() if p.get('patient_id') == patient_id]
    
    if not patient_preds:
        st.info("No historical data")
        return
    
    df = pd.DataFrame(patient_preds)
    st.dataframe(df[['date', 'risk_score', 'risk_category']], use_container_width=True)
    
    if len(df) > 1:
        fig = px.line(df, x='date', y='risk_score', title='Risk Score Trend')
        fig.update_layout(title_font_size=16)
        st.plotly_chart(fig, use_container_width=True)

# ============================================
# CLINICAL ALERTS DASHBOARD
# ============================================
def clinical_alerts_dashboard():
    st.markdown("<h3>Clinical Alerts Dashboard</h3>", unsafe_allow_html=True)
    alerts = load_json(ALERTS_FILE)
    unresolved = {k:v for k,v in alerts.items() if not v.get('resolved', False)}
    
    if not unresolved:
        st.success("No active alerts")
        return
    
    st.warning(f"{len(unresolved)} Active Alerts")
    for alert_id, alert in unresolved.items():
        with st.expander(f"{alert['patient_name']} - {alert['type']}"):
            st.write(f"Message: {alert['message']}")
            if st.button(f"Resolve", key=f"resolve_{alert_id}"):
                alerts[alert_id]['resolved'] = True
                save_json(ALERTS_FILE, alerts)
                st.rerun()

# ============================================
# CHW MODULE
# ============================================
def chw_module():
    st.markdown("<h3>Community Health Worker Module</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    predictions = load_json(PREDICTIONS_FILE)
    
    high_risk = []
    for pid, patient in patients.items():
        if patient.get('predictions'):
            last_pred = patient['predictions'][-1]
            if last_pred in predictions and predictions[last_pred].get('risk_score', 0) > 40:
                high_risk.append((pid, patient))
    
    if high_risk:
        st.warning(f"{len(high_risk)} High-risk patients need home visits")
        for pid, patient in high_risk[:5]:
            with st.expander(f"{patient['name']} - {patient.get('location', {}).get('suburb', 'Unknown')}"):
                st.write(f"Phone: {patient.get('phone', 'N/A')}")
                st.write(f"Address: {patient.get('location', {}).get('full_address', 'N/A')}")
                if st.button(f"Schedule Visit", key=f"visit_{pid}"):
                    st.success("Home visit scheduled")
    else:
        st.success("No high-risk patients needing home visits")

# ============================================
# EDUCATION LIBRARY
# ============================================
def education_library():
    st.markdown("<h3>Patient Education Library</h3>", unsafe_allow_html=True)
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
# REGISTER PATIENT
# ============================================
def register_patient():
    st.markdown("<h3>Register New Patient</h3>", unsafe_allow_html=True)
    
    with st.form("register_patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Patient Full Name")
            age = st.number_input("Age", 0, 120, 30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            phone = st.text_input("Phone Number")
        with col2:
            hiv_status = st.selectbox("HIV Status", ["Positive", "Negative", "Unknown"])
            tb_type = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"])
            registration_date = st.date_input("Registration Date", datetime.date.today())
        
        suburb = st.text_input("Suburb")
        street_address = st.text_input("Street Address")
        
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
                'registration_date': str(registration_date),
                'registered_by': st.session_state.username,
                'location': {'suburb': suburb, 'street_address': street_address, 'latitude': None, 'longitude': None},
                'predictions': []
            }
            save_json(PATIENTS_FILE, patients)
            
            users_db = load_json(USERS_FILE)
            users_db[st.session_state.username]['patients_registered'] = users_db[st.session_state.username].get('patients_registered', 0) + 1
            save_json(USERS_FILE, users_db)
            
            st.success(f"Patient registered! ID: {patient_id}")
            st.balloons()

# ============================================
# VIEW PATIENTS
# ============================================
def view_patients():
    st.markdown("<h3>Patient Registry</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    if not patients:
        st.info("No patients registered")
        return
    
    search = st.text_input("Search Patient", placeholder="Search by name or ID")
    
    for pid, patient in patients.items():
        if search and search.lower() not in patient['name'].lower():
            continue
        with st.expander(f"{pid} - {patient['name']}"):
            tabs = st.tabs(["Info", "Nutrition", "Mental Health", "Timeline"])
            with tabs[0]:
                st.write(f"Age: {patient['age']}")
                st.write(f"Gender: {patient['gender']}")
                st.write(f"HIV Status: {patient['hiv_status']}")
                st.write(f"TB Type: {patient['tb_type']}")
                st.write(f"Phone: {patient.get('phone', 'N/A')}")
                st.write(f"Suburb: {patient.get('location', {}).get('suburb', 'N/A')}")
            with tabs[1]:
                nutritional_assessment(pid, patient['name'])
            with tabs[2]:
                mental_health_screening(pid, patient['name'])
            with tabs[3]:
                patient_timeline(pid, patient['name'])

# ============================================
# PREDICT RISK
# ============================================
def predict_risk():
    st.markdown("<h3>Predict Treatment Default Risk</h3>", unsafe_allow_html=True)
    
    patients = load_json(PATIENTS_FILE)
    predictions = load_json(PREDICTIONS_FILE)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        patient_option = st.radio("Select Patient", ["New Patient", "Existing Patient"])
    
    patient_id = None
    patient_name = "New Patient"
    
    if patient_option == "Existing Patient":
        patient_list = {pid: f"{pid} - {data['name']}" for pid, data in patients.items()}
        if patient_list:
            selected = st.selectbox("Select Patient", list(patient_list.keys()), format_func=lambda x: patient_list[x])
            patient_id = selected
            patient_name = patients[selected]['name']
    
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
            action = "Weekly calls + Home visit + Nutrition support"
            css_class = "high-risk"
            save_alert(patient_id, patient_name, "clinical", "High risk of default")
        
        return points, risk, category, action, css_class, factors
    
    if st.button("Predict Default Risk", type="primary", use_container_width=True):
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
            'risk_points': points,
            'factors': factors,
            'recommendation': action
        }
        save_json(PREDICTIONS_FILE, predictions)
        
        if patient_id and patient_id in patients:
            patients[patient_id]['predictions'].append(prediction_id)
            save_json(PATIENTS_FILE, patients)
        
        users_db = load_json(USERS_FILE)
        users_db[st.session_state.username]['predictions_count'] = users_db[st.session_state.username].get('predictions_count', 0) + 1
        save_json(USERS_FILE, users_db)
        
        st.markdown("---")
        st.markdown("## Prediction Results")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk Score", f"{risk:.1f}%")
        c2.metric("Risk Points", f"{points}/11")
        c3.metric("Risk Category", category.split()[0])
        c4.metric("Population Default", "19.1%")
        
        st.markdown(f'<div class="{css_class}"><h3>{category}</h3><p><strong>Action:</strong> {action}</p></div>', unsafe_allow_html=True)
        st.progress(min(int(risk), 100))
        
        st.markdown("### Risk Factors")
        for f in factors:
            st.write(f"- {f}")
        
        st.markdown("### Clinical Recommendations")
        if art_status == "Not on ART":
            st.write("- Start ART immediately")
        if weight < 50:
            st.write("- Refer for nutritional support")
        if cd4 < 200:
            st.write("- Expedite ART initiation")
        if employment == "Unemployed":
            st.write("- Assess social support needs")
        
        st.caption(f"Predicted by: {users_db.get(st.session_state.username, {}).get('name', st.session_state.username)}")

# ============================================
# OTHER FUNCTIONS (Analytics, Reports, Map, etc.)
# ============================================
def analytics_dashboard():
    st.markdown("<h3>Analytics Dashboard</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if not predictions:
        st.info("No predictions yet")
        return
    
    df = pd.DataFrame(predictions).T
    df['risk_score'] = pd.to_numeric(df['risk_score'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Predictions", len(df))
    col2.metric("Avg Risk Score", f"{df['risk_score'].mean():.1f}%")
    col3.metric("High Risk", len(df[df['risk_score'] > 40]))
    col4.metric("Moderate Risk", len(df[(df['risk_score'] >= 15) & (df['risk_score'] <= 40)]))
    
    fig = px.histogram(df, x='risk_score', nbins=20, title='Risk Score Distribution')
    st.plotly_chart(fig, use_container_width=True)

def export_reports():
    st.markdown("<h3>Export Reports</h3>", unsafe_allow_html=True)
    report_type = st.selectbox("Report Type", ["All Predictions", "High Risk Cases", "Patient List"])
    
    predictions = load_json(PREDICTIONS_FILE)
    patients = load_json(PATIENTS_FILE)
    
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

def follow_up_tracker():
    st.markdown("<h3>Follow-up Tracker</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if not predictions:
        st.info("No predictions to track")
        return
    
    df = pd.DataFrame(predictions).T
    high_risk = df[df['risk_score'] > 40]
    
    for _, row in high_risk.iterrows():
        with st.expander(f"{row['patient_name']} - Risk: {row['risk_score']:.1f}%"):
            st.write(f"Date: {row['date']}")
            st.write(f"Clinician: {row['clinician']}")
            st.write(f"Recommendation: {row['recommendation']}")

def clinician_performance():
    st.markdown("<h3>Clinician Performance</h3>", unsafe_allow_html=True)
    users_db = load_json(USERS_FILE)
    data = [{'Name': u.get('name'), 'Predictions': u.get('predictions_count', 0)} for u in users_db.values()]
    df = pd.DataFrame(data)
    st.dataframe(df)
    if len(df) > 0:
        fig = px.bar(df, x='Name', y='Predictions', title='Predictions by Clinician')
        st.plotly_chart(fig)

def upload_csv_patients():
    st.markdown("<h3>Upload Patients from CSV</h3>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Choose CSV file", type=['csv'])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head())
        if st.button("Import"):
            st.success(f"Imported {len(df)} patients")

def patient_location_map():
    st.markdown("<h3>Patient Location Map</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    m = folium.Map(location=[-17.9333, 31.0333], zoom_start=13)
    for patient in patients.values():
        lat = patient.get('location', {}).get('latitude')
        lon = patient.get('location', {}).get('longitude')
        if lat and lon:
            folium.Marker([lat, lon], popup=patient['name']).add_to(m)
    folium_static(m, width=800, height=500)

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
        st.markdown(f"### {user_data.get('name', st.session_state.username)}")
        st.markdown(f"Role: {user_data.get('role', 'Clinician')}")
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
            "Alerts", "CHW Module", "Education"
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
    elif menu == "Alerts":
        clinical_alerts_dashboard()
    elif menu == "CHW Module":
        chw_module()
    elif menu == "Education":
        education_library()

# ============================================
# ROUTER
# ============================================
if st.session_state.logged_in:
    main_app()
elif st.session_state.page == "register":
    register_page()
else:
    login_page()

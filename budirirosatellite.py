
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
import re

st.set_page_config(page_title="Budiriro TB/HIV Predictor", page_icon="🏥", layout="wide")

# ============================================
# GLOBAL CSS FOR BOLD AND LARGER FONTS
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
    h4 { font-size: 20px !important; font-weight: 600 !important; }
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
if 'login_attempts' not in st.session_state:
    st.session_state.login_attempts = {}

@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="budiriro_tb_clinic")

# ============================================
# LOGIN PAGE (SIMPLIFIED AND WORKING)
# ============================================
def login_page():
    st.markdown("<h1 style='text-align:center;'>🏥 Budiriro Satellite Clinic</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>TB/HIV Treatment Default Risk Prediction System</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div style="background-color: #f0f2f6; padding: 2rem; border-radius: 10px;">', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            submitted = st.form_submit_button("🔐 Login", use_container_width=True, type="primary")
            
            if submitted:
                if not username or not password:
                    st.error("❌ Please enter both username and password")
                else:
                    users = load_json(USERS_FILE)
                    if username in users and users[username]['password'] == hash_password(password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_name = users[username]['name']
                        st.session_state.user_role = users[username]['role']
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                        # Track failed attempts
                        st.session_state.login_attempts[username] = st.session_state.login_attempts.get(username, 0) + 1
                        if st.session_state.login_attempts[username] >= 3:
                            st.warning("⚠️ Multiple failed attempts. Contact administrator if you forgot your password.")
        
        st.markdown("---")
        
        if st.button("📝 Create New Account", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Demo credentials hint
        st.info("💡 **Demo Credentials:**
- Username: `demo` | Password: `demo123`
- Or create your own account")

# ============================================
# REGISTER PAGE
# ============================================
def register_page():
    st.markdown("<h2 style='text-align:center;'>Create New Account</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div style="background-color: #f0f2f6; padding: 2rem; border-radius: 10px;">', unsafe_allow_html=True)

        with st.form("register_form"):
            full_name = st.text_input("Full Name *", placeholder="Enter your full name")
            username = st.text_input("Username *", placeholder="Choose a username")
            password = st.text_input("Password *", type="password", placeholder="Minimum 4 characters")
            confirm = st.text_input("Confirm Password *", type="password", placeholder="Re-enter password")
            role = st.selectbox("Role", ["Clinician", "Nurse", "Doctor", "Clinical Officer"])
            department = st.selectbox("Department", ["TB/HIV Unit", "Outpatient", "Inpatient", "Community"])
            
            submitted = st.form_submit_button("✅ Register", use_container_width=True, type="primary")

            if submitted:
                if not full_name or not username or not password:
                    st.error("❌ Please fill all required fields")
                elif password != confirm:
                    st.error("❌ Passwords do not match")
                elif len(password) < 4:
                    st.error("❌ Password must be at least 4 characters")
                else:
                    users = load_json(USERS_FILE)
                    if username in users:
                        st.error("❌ Username already exists. Please choose another username.")
                    else:
                        users[username] = {
                            'name': full_name, 
                            'password': hash_password(password),
                            'role': role, 
                            'department': department, 
                            'created': str(datetime.datetime.now()),
                            'predictions_count': 0, 
                            'patients_registered': 0
                        }
                        save_json(USERS_FILE, users)
                        st.success("✅ Account created successfully!")
                        st.info("🔐 Please login with your new account")
                        
                        # Add a button to go to login
                        if st.button("Go to Login Page"):
                            st.session_state.page = "login"
                            st.rerun()
        
        st.markdown("---")
        
        if st.button("← Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# SAVE ALERTS FUNCTION
# ============================================
def save_alert(patient_id, patient_name, alert_type, message):
    alerts = load_json(ALERTS_FILE)
    alert_id = f"ALT-{len(alerts)+1:04d}"
    alerts[alert_id] = {
        'patient_id': patient_id, 'patient_name': patient_name,
        'type': alert_type, 'message': message, 'date': str(datetime.datetime.now()),
        'resolved': False, 'clinician': st.session_state.username
    }
    save_json(ALERTS_FILE, alerts)

# ============================================
# NUTRITIONAL ASSESSMENT MODULE
# ============================================
def nutritional_assessment(patient_id, patient_name):
    st.markdown("<h4>🥗 Nutritional Assessment</h4>", unsafe_allow_html=True)
    
    nutrition_data = load_json(NUTRITION_FILE)
    
    with st.form(f"nutrition_form_{patient_id}"):
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
                save_alert(patient_id, patient_name, "nutrition", alert_msg)
            elif weight < 55:
                st.warning("🟡 Moderate underweight - Monitor closely")
            else:
                st.success("🟢 Normal weight - Continue monitoring")
        
        st.markdown("#### Food Security Assessment")
        food_insecure = st.radio("In the past month, did you ever run out of food?", 
                                  ["No", "Yes, sometimes", "Yes, often"])
        
        if food_insecure in ["Yes, sometimes", "Yes, often"]:
            st.warning("🚨 Food insecurity detected - Refer to social services")
        
        submitted = st.form_submit_button("💾 Save Nutritional Assessment")
        
        if submitted:
            nutrition_data[patient_id] = {
                'patient_name': patient_name, 'date': str(datetime.datetime.now()),
                'weight': weight, 'height': height, 'bmi': bmi, 'muac': muac,
                'food_insecure': food_insecure, 'assessed_by': st.session_state.username
            }
            save_json(NUTRITION_FILE, nutrition_data)
            st.success("✅ Nutritional assessment saved!")

# ============================================
# MENTAL HEALTH SCREENING MODULE
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
        alert_msg = f"Patient {patient_name} has PHQ-9 score of {total_phq9} - needs immediate mental health referral"
        save_alert(patient_id, patient_name, "mental_health", alert_msg)
    elif total_phq9 >= 10:
        st.warning(f"🟡 PHQ-9 Score: {total_phq9} - Moderate Depression")
        alert_msg = f"Patient {patient_name} has PHQ-9 score of {total_phq9} - needs mental health assessment"
        save_alert(patient_id, patient_name, "mental_health", alert_msg)
    elif total_phq9 >= 5:
        st.info(f"📊 PHQ-9 Score: {total_phq9} - Mild Depression - Monitor")
    else:
        st.success(f"🟢 PHQ-9 Score: {total_phq9} - Minimal depression")
    
    if st.button("💾 Save Mental Health Assessment"):
        mental_data[patient_id] = {
            'patient_name': patient_name, 'date': str(datetime.datetime.now()),
            'phq9_score': total_phq9, 'responses': phq9_scores,
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
    
    if not unresolved:
        st.success("✅ No active alerts! All patients are stable.")
        return
    
    st.warning(f"⚠️ {len(unresolved)} Active Alert(s) Requiring Attention")
    
    for alert_id, alert in unresolved.items():
        with st.expander(f"🔴 {alert['patient_name']} - {alert['type'].upper()} - {alert['date'][:10]}", expanded=True):
            st.write(f"**Message:** {alert['message']}")
            st.write(f"**Clinician:** {alert['clinician']}")
            st.write(f"**Date:** {alert['date']}")
            
            if st.button(f"✅ Resolve Alert", key=f"resolve_{alert_id}"):
                alerts[alert_id]['resolved'] = True
                save_json(ALERTS_FILE, alerts)
                st.success("Alert resolved!")
                st.rerun()

# ============================================
# PATIENT TIMELINE TRACKING
# ============================================
def patient_timeline(patient_id, patient_name):
    st.markdown("<h4>📅 Treatment Timeline</h4>", unsafe_allow_html=True)
    
    predictions = load_json(PREDICTIONS_FILE)
    nutrition = load_json(NUTRITION_FILE)
    mental = load_json(MENTAL_HEALTH_FILE)
    
    patient_predictions = [p for p in predictions.values() if p.get('patient_id') == patient_id]
    
    if not patient_predictions:
        st.info("No historical data for this patient yet")
        return
    
    # Create timeline dataframe
    timeline_data = []
    for pred in patient_predictions:
        timeline_data.append({
            'Date': pred['date'][:10],
            'Risk Score (%)': pred['risk_score'],
            'Risk Category': pred['risk_category']
        })
    
    df = pd.DataFrame(timeline_data)
    st.dataframe(df, use_container_width=True)
    
    # Risk score trend chart
    if len(df) > 1:
        fig = px.line(df, x='Date', y='Risk Score (%)', title='Risk Score Over Time',
                      markers=True, labels={'Risk Score (%)': 'Default Risk (%)'})
        fig.update_layout(title_font_size=16, title_font_weight='bold')
        st.plotly_chart(fig, use_container_width=True)

# ============================================
# SMS REMINDER SIMULATION
# ============================================
def send_sms_reminder(patient_name, phone, message_type):
    st.info(f"📱 SMS would be sent to {phone}")
    
    if message_type == "appointment":
        st.info("📱 **Message:** REMINDER: You have a clinic appointment tomorrow at Budiriro Clinic. Please bring your medication. Reply YES to confirm.")
    elif message_type == "medication":
        st.info("💊 **Message:** REMINDER: Time to take your TB medication. Taking medication on time helps you get better faster.")
    elif message_type == "high_risk":
        st.warning("⚠️ **Message:** URGENT: Our records show you missed your last appointment. Please call the clinic at 086-123-4567 to reschedule.")
    
    if st.button("📤 Send SMS", key=f"sms_{patient_name}"):
        st.success("✅ SMS sent successfully!")

# ============================================
# EDUCATION LIBRARY
# ============================================
def education_library():
    st.markdown("<h3>📚 Patient Education Library</h3>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📖 TB Treatment", "💊 HIV/ART", "🥗 Nutrition", "🧠 Mental Health"])
    
    with tab1:
        st.markdown("""
        ### Understanding TB Treatment
        
        **What is TB?**
        Tuberculosis (TB) is a bacterial infection that usually affects the lungs. It is curable with proper treatment.
        
        **Why is treatment important?**
        - TB treatment takes 6 months
        - Taking medication daily kills the bacteria
        - Stopping early can cause drug-resistant TB
        
        **What to expect:**
        - First 2 weeks: You may still feel sick but you are less contagious
        - After 2 weeks: You will start feeling better
        - Complete all medication even if you feel better
        
        **Side effects to report:**
        - Yellow eyes or skin
        - Dark urine
        - Severe nausea
        - Vision changes
        """)
    
    with tab2:
        st.markdown("""
        ### Understanding HIV and ART
        
        **What is ART?**
        Antiretroviral Therapy (ART) is medication that controls HIV and prevents AIDS.
        
        **Benefits of ART:**
        - Allows your immune system to recover
        - Reduces HIV to undetectable levels
        - Prevents transmission to others
        - You can live a normal, healthy life
        
        **Taking ART with TB medication:**
        - Both can be taken together safely
        - Some side effects are normal in first few weeks
        - Report severe side effects to your clinician
        """)
    
    with tab3:
        st.markdown("""
        ### Nutrition for TB/HIV Patients
        
        **Why is nutrition important?**
        - Good nutrition helps your body fight infection
        - Prevents weight loss during treatment
        - Helps medications work better
        
        **Foods to eat:**
        - 🥚 Eggs, meat, fish (protein)
        - 🥜 Beans, groundnuts (plant protein)
        - 🥬 Leafy greens (vitamins)
        - 🍚 Sadza, rice, potatoes (energy)
        
        **Food assistance:**
        Ask your clinician about food support programs if you struggle to afford food.
        """)
    
    with tab4:
        st.markdown("""
        ### Mental Health Support
        
        **It's normal to feel:**
        - Overwhelmed by your diagnosis
        - Worried about the future
        - Sad or depressed sometimes
        
        **What can help:**
        - Talk to someone you trust
        - Join a support group
        - Speak to our counselor
        - Take medications as prescribed
        
        **Emergency support:**
        If you have thoughts of harming yourself, call our clinic immediately.
        """)

# ============================================
# CHW MODULE (Community Health Worker)
# ============================================
def chw_module():
    st.markdown("<h3>🌍 Community Health Worker Module</h3>", unsafe_allow_html=True)
    
    patients = load_json(PATIENTS_FILE)
    predictions = load_json(PREDICTIONS_FILE)
    
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
                with col2:
                    visit_date = st.date_input(f"Schedule visit", key=f"visit_{pid}")
                    if st.button(f"📅 Schedule Home Visit", key=f"schedule_{pid}"):
                        st.success(f"✅ Home visit scheduled for {visit_date}")
    else:
        st.success("✅ No high-risk patients requiring immediate home visits")
    
    st.markdown("---")
    st.markdown("### 📋 CHW Task List")
    
    # Show pending follow-ups from alerts
    alerts = load_json(ALERTS_FILE)
    unresolved = [a for a in alerts.values() if not a.get('resolved', False)]
    
    if unresolved:
        st.markdown("**Pending Follow-ups:**")
        for alert in unresolved[:5]:
            st.write(f"- {alert['patient_name']}: {alert['message'][:100]}...")

# ============================================
# REGISTER PATIENT
# ============================================
def register_patient():
    st.markdown("<h3>📝 Register New Patient</h3>", unsafe_allow_html=True)

    with st.form("register_patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Patient Full Name", placeholder="Enter full name")
            age = st.number_input("Age", 0, 120, 30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            phone = st.text_input("Phone Number", placeholder="e.g., 0771234567")
        with col2:
            hiv_status = st.selectbox("HIV Status", ["Positive", "Negative", "Unknown"])
            tb_type = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"])
            registration_date = st.date_input("Registration Date", datetime.date.today())

        st.markdown("<h4>📍 Location Information</h4>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            suburb = st.text_input("Suburb/Area", placeholder="e.g., Budiriro, Glen View")
            street_address = st.text_input("Street Address", placeholder="House number, street name")
        with col4:
            landmark = st.text_input("Nearby Landmark", placeholder="Near shopping center, school")
            additional_notes = st.text_area("Additional Location Notes", placeholder="Directions, special instructions")

        submitted = st.form_submit_button("✅ Register Patient", use_container_width=True)

        if submitted and patient_name:
            patients = load_json(PATIENTS_FILE)
            patient_id = f"BUD-{len(patients)+1:04d}"

            full_address = f"{street_address}, {suburb}, Harare, Zimbabwe"
            latitude = None
            longitude = None

            try:
                geolocator = get_geocoder()
                location = geolocator.geocode(full_address, timeout=10)
                if location:
                    latitude = location.latitude
                    longitude = location.longitude
            except:
                pass

            patients[patient_id] = {
                'patient_id': patient_id, 'name': patient_name, 'age': age,
                'gender': gender, 'phone': phone,
                'hiv_status': hiv_status, 'tb_type': tb_type,
                'registration_date': str(registration_date),
                'registered_by': st.session_state.username,
                'location': {
                    'suburb': suburb, 'street_address': street_address,
                    'landmark': landmark, 'additional_notes': additional_notes,
                    'latitude': latitude, 'longitude': longitude, 'full_address': full_address
                },
                'predictions': []
            }
            save_json(PATIENTS_FILE, patients)

            users = load_json(USERS_FILE)
            users[st.session_state.username]['patients_registered'] = users[st.session_state.username].get('patients_registered', 0) + 1
            save_json(USERS_FILE, users)

            st.success(f"✅ Patient registered! ID: {patient_id}")
            st.balloons()

# ============================================
# PREDICT RISK (Enhanced)
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

    if patient_option == "Existing Patient":
        patient_list = {pid: f"{pid} - {data['name']}" for pid, data in patients.items()}
        if patient_list:
            selected = st.selectbox("Select Patient", list(patient_list.keys()), format_func=lambda x: patient_list[x])
            patient_id = selected
            patient_name = patients[selected]['name']

    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age (years)", 18, 120, 30)
        sex = st.radio("Sex", ["Female", "Male"], horizontal=True)
        employment = st.selectbox("Employment", ["Employed", "Unemployed", "Other"])
        weight = st.number_input("Weight (kg)", 25.0, 150.0, 60.0)
    with col2:
        art_status = st.selectbox("ART Status", ["Already on ART", "Not on ART", "Unknown/Not documented"])
        cd4 = st.number_input("CD4 Count (cells/μL)", 0, 1500, 300)
        tb_type = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"])

    def calculate_risk(age, sex, art_status, weight, cd4, employment):
        points = 0
        factors = []
        alerts = []
        
        if art_status == "Not on ART":
            points += 3
            factors.append("❌ Not on ART at TB initiation (+3)")
            alerts.append("URGENT: Patient not on ART - start immediately")
        if weight < 50:
            points += 2
            factors.append("⚠️ Underweight <50 kg (+2)")
            alerts.append("CRITICAL: Severe underweight - refer to nutrition program")
        if cd4 < 200:
            points += 2
            factors.append("⚠️ Low CD4 <200 cells/uL (+2)")
            alerts.append("URGENT: Advanced immunosuppression - expedite ART")
        if 18 <= age <= 24:
            points += 2
            factors.append("👤 Young adult 18-24 years (+2)")
        if sex == "Male":
            points += 1
            factors.append("👨 Male sex (+1)")
        if employment == "Unemployed":
            points += 1
            factors.append("💰 Unemployed (+1)")

        if points <= 2:
            risk = random.uniform(5, 15)
            category = "LOW RISK"
            action = "✅ Standard DOT"
            css_class = "low-risk"
        elif points <= 5:
            risk = random.uniform(15, 40)
            category = "MODERATE RISK"
            action = "📱 Standard DOT + SMS reminders"
            css_class = "moderate-risk"
        else:
            risk = random.uniform(40, 75)
            category = "HIGH RISK"
            action = "🔴 Weekly calls + Home visit + Nutrition support"
            css_class = "high-risk"
            alerts.append("CRITICAL: High risk of default - immediate intervention required")
        
        return points, risk, category, action, css_class, factors, alerts

    if st.button("🔍 Predict Default Risk", type="primary", use_container_width=True):
        points, risk, category, action, css_class, factors, alerts = calculate_risk(age, sex, art_status, weight, cd4, employment)

        # Save prediction
        prediction_id = f"PRED-{len(predictions)+1:04d}"
        predictions[prediction_id] = {
            'prediction_id': prediction_id, 'patient_id': patient_id, 'patient_name': patient_name,
            'date': str(datetime.datetime.now()), 'clinician': st.session_state.username,
            'age': age, 'sex': sex, 'art_status': art_status, 'weight': weight, 'cd4': cd4,
            'risk_score': risk, 'risk_category': category, 'risk_points': points,
            'factors': factors, 'recommendation': action
        }
        save_json(PREDICTIONS_FILE, predictions)

        if patient_id and patient_id in patients:
            patients[patient_id]['predictions'].append(prediction_id)
            save_json(PATIENTS_FILE, patients)
            
            # Save alerts
            for alert in alerts:
                save_alert(patient_id, patient_name, "clinical", alert)

        users = load_json(USERS_FILE)
        users[st.session_state.username]['predictions_count'] = users[st.session_state.username].get('predictions_count', 0) + 1
        save_json(USERS_FILE, users)

        # Display Results
        st.markdown("---")
        st.markdown("<h3>📊 Prediction Results</h3>", unsafe_allow_html=True)

        # Critical alerts display
        if risk > 60 or points >= 6:
            st.markdown('<div class="alert-critical"><h3>🚨 CRITICAL ALERT</h3><p>This patient is at VERY HIGH RISK of defaulting. Immediate intervention required!</p></div>', unsafe_allow_html=True)

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Risk Score", f"{risk:.1f}%")
        metric2.metric("Risk Points", f"{points}/11")
        metric3.metric("Risk Category", category.replace(" RISK", ""))
        metric4.metric("Population Default", "19.1%")

        st.markdown(f'<div class="{css_class}"><h3>{category}</h3><p><strong>Recommended Action:</strong> {action}</p></div>', unsafe_allow_html=True)

        st.progress(min(int(risk), 100))

        st.markdown("<h4>⚠️ Risk Factors Identified</h4>", unsafe_allow_html=True)
        if factors:
            for factor in factors:
                st.markdown(f"- {factor}")
        else:
            st.success("No major risk factors identified")
            
        if alerts:
            st.markdown("<h4 style='color:#dc3545;'>🚨 Action Required</h4>", unsafe_allow_html=True)
            for alert in alerts:
                st.error(f"⚠️ {alert}")

        st.markdown("<h4>💊 Clinical Recommendations</h4>", unsafe_allow_html=True)
        recommendations = []
        if art_status == "Not on ART":
            recommendations.append("• Start ART immediately (within 2 weeks)")
        if weight < 50:
            recommendations.append("• Refer for nutritional assessment and food support")
        if cd4 < 200:
            recommendations.append("• Expedite ART initiation, screen for cryptococcus")
        if 18 <= age <= 24:
            recommendations.append("• Provide youth-friendly adherence support")
        if employment == "Unemployed":
            recommendations.append("• Assess social and economic support needs")

        if recommendations:
            for recommendation in recommendations:
                st.markdown(recommendation)
        else:
            st.markdown("• Continue with standard care")
        
        st.markdown("---")
        st.caption(f"👨‍⚕️ Predicted by: {users.get(st.session_state.username, {}).get('name', st.session_state.username)} | 📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Offer SMS reminder
        if patient_id and patients.get(patient_id, {}).get('phone'):
            st.markdown("---")
            st.markdown("<h4>📱 Send Patient Reminder</h4>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📅 Appointment Reminder"):
                    send_sms_reminder(patient_name, patients[patient_id]['phone'], "appointment")
            with col2:
                if st.button("💊 Medication Reminder"):
                    send_sms_reminder(patient_name, patients[patient_id]['phone'], "medication")

# ============================================
# VIEW PATIENTS (Enhanced)
# ============================================
def view_patients():
    st.markdown("<h3>📋 Patient Registry</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)
    if not patients:
        st.info("No patients registered yet")
        return

    search = st.text_input("🔍 Search Patient", placeholder="Search by name or ID")

    for pid, patient in patients.items():
        if search and search.lower() not in patient['name'].lower() and search not in pid:
            continue
        with st.expander(f"{pid} - {patient['name']} (Age: {patient['age']})"):
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Info", "🥗 Nutrition", "🧠 Mental Health", "📅 Timeline"])
            
            with tab1:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Gender:** {patient['gender']}")
                    st.write(f"**HIV Status:** {patient['hiv_status']}")
                    st.write(f"**TB Type:** {patient['tb_type']}")
                    st.write(f"**Phone:** {patient.get('phone', 'N/A')}")
                with col2:
                    st.write(f"**Suburb:** {patient.get('location', {}).get('suburb', 'N/A')}")
                    st.write(f"**Registered by:** {patient['registered_by']}")
                    if patient.get('phone'):
                        if st.button(f"📱 Send SMS", key=f"sms_{pid}"):
                            send_sms_reminder(patient['name'], patient['phone'], "appointment")
            
            with tab2:
                nutritional_assessment(pid, patient['name'])
            
            with tab3:
                mental_health_screening(pid, patient['name'])
            
            with tab4:
                patient_timeline(pid, patient['name'])

# ============================================
# ANALYTICS DASHBOARD
# ============================================
def analytics_dashboard():
    st.markdown("<h3>📊 Analytics Dashboard</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    nutrition = load_json(NUTRITION_FILE)
    mental = load_json(MENTAL_HEALTH_FILE)
    
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
    fig.update_layout(title_font_size=18, title_font_weight='bold')
    st.plotly_chart(fig, use_container_width=True)
    
    # Nutrition and Mental Health Stats
    st.markdown("<h4>📊 Program Statistics</h4>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        underweight_count = len([n for n in nutrition.values() if n.get('weight', 100) < 50])
        st.metric("Underweight Patients (<50kg)", underweight_count)
    with col2:
        depressed_count = len([m for m in mental.values() if m.get('phq9_score', 0) >= 10])
        st.metric("Patients with Depression (PHQ-9≥10)", depressed_count)

# ============================================
# PATIENT LOCATION MAP
# ============================================
def patient_location_map():
    st.markdown("<h3>🗺️ Patient Location Map</h3>", unsafe_allow_html=True)
    patients = load_json(PATIENTS_FILE)

    if not patients:
        st.info("No patients registered")
        return

    m = folium.Map(location=[-17.9333, 31.0333], zoom_start=13)
    m.add_child(folium.LatLngPopup())

    for pid, patient in patients.items():
        lat = patient.get('location', {}).get('latitude')
        lon = patient.get('location', {}).get('longitude')
        if lat and lon:
            folium.Marker([lat, lon], popup=f"{patient['name']}<br>ID: {pid}",
                         tooltip=patient['name']).add_to(m)

    folium.Marker([-17.9333, 31.0333], popup="Budiriro Clinic",
                 icon=folium.Icon(color="blue")).add_to(m)

    folium_static(m, width=800, height=500)

# ============================================
# EXPORT REPORTS
# ============================================
def export_reports():
    st.markdown("<h3>📥 Export Data Reports</h3>", unsafe_allow_html=True)
    report_type = st.selectbox("Select Report Type", ["All Predictions", "High Risk Cases", "Patient List"])

    predictions = load_json(PREDICTIONS_FILE)
    patients = load_json(PATIENTS_FILE)

    if report_type == "All Predictions" and predictions:
        df = pd.DataFrame(predictions).T
        st.dataframe(df)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "predictions.csv", "text/csv")
    elif report_type == "High Risk Cases" and predictions:
        df = pd.DataFrame(predictions).T
        high_risk = df[df['risk_score'] > 40]
        st.dataframe(high_risk)
        csv = high_risk.to_csv(index=False)
        st.download_button("Download CSV", csv, "high_risk.csv", "text/csv")
    elif report_type == "Patient List" and patients:
        df = pd.DataFrame(patients).T
        st.dataframe(df)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "patients.csv", "text/csv")

# ============================================
# FOLLOW-UP TRACKER
# ============================================
def follow_up_tracker():
    st.markdown("<h3>📅 Patient Follow-up Tracker</h3>", unsafe_allow_html=True)
    predictions = load_json(PREDICTIONS_FILE)
    if not predictions:
        st.info("No predictions to track")
        return

    df = pd.DataFrame(predictions).T
    df['risk_score'] = pd.to_numeric(df['risk_score'])
    high_risk = df[df['risk_score'] > 40]

    if len(high_risk) == 0:
        st.success("✅ No high-risk patients currently")
    else:
        for idx, row in high_risk.iterrows():
            with st.expander(f"{row['patient_name']} - Risk: {row['risk_score']:.1f}%"):
                st.write(f"**Date:** {row['date']}")
                st.write(f"**Clinician:** {row['clinician']}")
                st.write(f"**Recommendation:** {row['recommendation']}")

# ============================================
# CLINICIAN PERFORMANCE
# ============================================
def clinician_performance():
    st.markdown("<h3>👨‍⚕️ Clinician Performance</h3>", unsafe_allow_html=True)
    users = load_json(USERS_FILE)
    data = [{'Name': u.get('name'), 'Predictions': u.get('predictions_count', 0),
             'Patients': u.get('patients_registered', 0)} for u in users.values()]
    df = pd.DataFrame(data)
    st.dataframe(df)
    if len(df) > 0:
        fig = px.bar(df, x='Name', y='Predictions', title='Predictions by Clinician')
        fig.update_layout(title_font_size=18, title_font_weight='bold')
        st.plotly_chart(fig)

# ============================================
# CSV UPLOAD PATIENTS
# ============================================
def upload_csv_patients():
    st.markdown("<h3>📤 Upload Patients from CSV</h3>", unsafe_allow_html=True)

    template = pd.DataFrame({'name': ['John Doe'], 'age': [35], 'gender': ['Male'],
                              'phone': ['0771234567'], 'hiv_status': ['Positive'],
                              'tb_type': ['Pulmonary'], 'suburb': ['Budiriro'],
                              'street_address': ['123 Main St']})
    csv_template = template.to_csv(index=False)
    st.download_button("📥 Download Template", csv_template, "template.csv", "text/csv")

    uploaded = st.file_uploader("Choose CSV file", type=['csv'])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head())

        if st.button("Import Patients", use_container_width=True):
            patients = load_json(PATIENTS_FILE)
            for _, row in df.iterrows():
                pid = f"BUD-{len(patients)+1:04d}"
                patients[pid] = {
                    'patient_id': pid, 'name': row['name'], 'age': int(row['age']),
                    'gender': row['gender'], 'phone': row.get('phone', ''),
                    'hiv_status': row.get('hiv_status', 'Unknown'),
                    'tb_type': row.get('tb_type', 'Pulmonary'),
                    'registration_date': str(datetime.date.today()),
                    'registered_by': st.session_state.username,
                    'location': {'suburb': row.get('suburb', ''), 'street_address': row.get('street_address', ''),
                                 'latitude': None, 'longitude': None},
                    'predictions': []
                }
            save_json(PATIENTS_FILE, patients)
            st.success(f"Imported {len(df)} patients!")

# ============================================
# MAIN APP
# ============================================
def main_app():
    users = load_json(USERS_FILE)
    user_data = users.get(st.session_state.username, {})

    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1a5276, #2e86c1); padding: 1.5rem; border-radius: 10px; color: white;">
            <h1 style="color:white; margin:0;">🏥 Budiriro Satellite Clinic</h1>
            <p style="font-size:18px; margin:5px 0;">TB/HIV Treatment Default Risk Prediction System</p>
            <p style="font-size:14px; margin:0;">Welcome, {user_data.get('name', st.session_state.username)} | Role: {user_data.get('role', 'Clinician')} | AUC = 0.706</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👋 {user_data.get('name', st.session_state.username)}")
        st.markdown(f"**Role:** {user_data.get('role', 'Clinician')}")
        st.markdown(f"**Predictions:** {user_data.get('predictions_count', 0)}")
        st.markdown(f"**Patients:** {user_data.get('patients_registered', 0)}")
        st.markdown("---")
        st.markdown("### 📊 Model Information")
        st.markdown("**Algorithm:** Random Forest")
        st.markdown("**AUC-ROC:** 0.706")
        st.markdown("**Accuracy:** 81.9%")
        st.markdown("**Default Rate:** 19.1%")
        st.markdown("---")
        st.markdown("### ⚠️ Risk Factors")
        st.markdown("- Not on ART at TB start (+3)")
        st.markdown("- Weight <50 kg (+2)")
        st.markdown("- CD4 <200 cells/uL (+2)")
        st.markdown("- Age 18-24 years (+2)")
        st.markdown("- Male sex (+1)")
        st.markdown("- Unemployed (+1)")
        st.markdown("---")
        
        menu = st.radio("📋 MENU", [
            "🎯 Predict Risk", "📝 Register Patient", "📋 View Patients",
            "🗺️ Patient Map", "📊 Analytics", "📥 Reports",
            "📅 Follow-up", "👨‍⚕️ Performance", "📤 CSV Upload",
            "🚨 Alerts Dashboard", "🌍 CHW Module", "📚 Education Library"
        ])

    # Route to selected menu
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
    elif menu == "🚨 Alerts Dashboard":
        clinical_alerts_dashboard()
    elif menu == "🌍 CHW Module":
        chw_module()
    elif menu == "📚 Education Library":
        education_library()

# ============================================
# CREATE DEMO USER IF NO USERS EXIST
# ============================================
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
# ROUTER
# ============================================
if st.session_state.logged_in:
    main_app()
elif st.session_state.page == "register":
    register_page()
else:
    login_page()

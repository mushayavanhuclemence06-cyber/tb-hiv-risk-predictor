
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
# USER DATABASE
# ============================================
USERS_FILE = "users.json"
PATIENTS_FILE = "patients.json"
PREDICTIONS_FILE = "predictions.json"

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

# ============================================
# LOGIN PAGE
# ============================================
def login_page():
    st.markdown("<h2 style='text-align:center'>🏥 Budiriro Satellite Clinic</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>TB/HIV Treatment Default Risk Prediction System</p>", unsafe_allow_html=True)
    st.markdown("---")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            users = load_json(USERS_FILE)
            if username in users and users[username]['password'] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_name = users[username]['name']
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
    st.markdown("<h2 style='text-align:center'>Create New Account</h2>", unsafe_allow_html=True)

    with st.form("register_form"):
        full_name = st.text_input("Full Name *")
        username = st.text_input("Username *")
        password = st.text_input("Password *", type="password")
        confirm = st.text_input("Confirm Password *", type="password")
        role = st.selectbox("Role", ["Clinician", "Nurse", "Doctor", "Clinical Officer"])
        department = st.selectbox("Department", ["TB/HIV Unit", "Outpatient", "Inpatient", "Community"])
        submitted = st.form_submit_button("Register", use_container_width=True)

        if submitted:
            if not full_name or not username or not password:
                st.error("Please fill all fields")
            elif password != confirm:
                st.error("Passwords don't match")
            elif len(password) < 4:
                st.error("Password too short")
            else:
                users = load_json(USERS_FILE)
                if username in users:
                    st.error("Username already exists")
                else:
                    users[username] = {
                        'name': full_name, 'password': hash_password(password),
                        'role': role, 'department': department, 'created': str(datetime.datetime.now()),
                        'predictions_count': 0, 'patients_registered': 0
                    }
                    save_json(USERS_FILE, users)
                    st.success("Account created! Please login.")
                    st.session_state.page = "login"
                    st.rerun()

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# ============================================
# FUNCTION 1: REGISTER PATIENT
# ============================================
def register_patient():
    st.subheader("📝 Register New Patient")

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

        st.markdown("### 📍 Location Information")
        col3, col4 = st.columns(2)
        with col3:
            suburb = st.text_input("Suburb/Area")
            street_address = st.text_input("Street Address")
        with col4:
            landmark = st.text_input("Nearby Landmark")
            additional_notes = st.text_area("Additional Location Notes")

        submitted = st.form_submit_button("Register Patient", use_container_width=True)

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
# FUNCTION 2: VIEW PATIENTS
# ============================================
def view_patients():
    st.subheader("📋 Patient Registry")
    patients = load_json(PATIENTS_FILE)
    if not patients:
        st.info("No patients registered yet")
        return

    search = st.text_input("🔍 Search Patient", placeholder="Search by name or ID")

    for pid, patient in patients.items():
        if search and search.lower() not in patient['name'].lower() and search not in pid:
            continue
        with st.expander(f"{pid} - {patient['name']} (Age: {patient['age']})"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Gender:** {patient['gender']}")
                st.write(f"**HIV Status:** {patient['hiv_status']}")
                st.write(f"**TB Type:** {patient['tb_type']}")
            with col2:
                st.write(f"**Suburb:** {patient.get('location', {}).get('suburb', 'N/A')}")
                st.write(f"**Registered by:** {patient['registered_by']}")

# ============================================
# FUNCTION 3: PREDICT RISK (WITH ENHANCED UI)
# ============================================
def predict_risk():
    st.subheader("🎯 Predict Treatment Default Risk")

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
        age = st.number_input("Age", 18, 120, 30)
        sex = st.radio("Sex", ["Female", "Male"], horizontal=True)
        employment = st.selectbox("Employment", ["Employed", "Unemployed", "Other"])
        weight = st.number_input("Weight (kg)", 25.0, 150.0, 60.0)
    with col2:
        art_status = st.selectbox("ART Status", ["Already on ART", "Not on ART", "Unknown/Not documented"])
        cd4 = st.number_input("CD4 Count", 0, 1500, 300)
        tb_type = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"])

    # ======================================
    # RISK CALCULATION FUNCTION
    # ======================================
    def calculate_risk(age, sex, art_status, weight, cd4, employment):
        points = 0
        factors = []
        if art_status == "Not on ART":
            points += 3
            factors.append("Not on ART at TB initiation (+3)")
        if weight < 50:
            points += 2
            factors.append("Underweight <50 kg (+2)")
        if cd4 < 200:
            points += 2
            factors.append("Low CD4 <200 cells/uL (+2)")
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
        return points, risk, category, action, css_class, factors

    # ======================================
    # PREDICTION BUTTON
    # ======================================
    if st.button("Predict Default Risk", type="primary", use_container_width=True):
        points, risk, category, action, css_class, factors = calculate_risk(age, sex, art_status, weight, cd4, employment)

        # Save prediction to database
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

        users = load_json(USERS_FILE)
        users[st.session_state.username]['predictions_count'] = users[st.session_state.username].get('predictions_count', 0) + 1
        save_json(USERS_FILE, users)

        # Display Results
        st.markdown("---")
        st.markdown("## Prediction Results")

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

        st.markdown("### Clinical Recommendations")
        recommendations = []
        if art_status == "Not on ART":
            recommendations.append("Start ART immediately")
        if weight < 50:
            recommendations.append("Refer for nutritional assessment")
        if cd4 < 200:
            recommendations.append("Optimise ART regimen")
        if 18 <= age <= 24:
            recommendations.append("Provide youth-friendly adherence support")
        if employment == "Unemployed":
            recommendations.append("Assess social and economic support needs")

        if recommendations:
            for recommendation in recommendations:
                st.markdown(f"- {recommendation}")
        else:
            st.markdown("- Continue with standard care")
        
        # Add clinician signature
        st.markdown("---")
        st.caption(f"👨‍⚕️ Predicted by: {users.get(st.session_state.username, {}).get('name', st.session_state.username)} | 📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================
# FUNCTION 4: ANALYTICS DASHBOARD
# ============================================
def analytics_dashboard():
    st.subheader("📊 Analytics Dashboard")
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

# ============================================
# FUNCTION 5: EXPORT REPORTS
# ============================================
def export_reports():
    st.subheader("📥 Export Data Reports")
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
# FUNCTION 6: FOLLOW-UP TRACKER
# ============================================
def follow_up_tracker():
    st.subheader("📅 Patient Follow-up Tracker")
    predictions = load_json(PREDICTIONS_FILE)
    if not predictions:
        st.info("No predictions to track")
        return

    df = pd.DataFrame(predictions).T
    df['risk_score'] = pd.to_numeric(df['risk_score'])
    high_risk = df[df['risk_score'] > 40]

    for idx, row in high_risk.iterrows():
        with st.expander(f"{row['patient_name']} - Risk: {row['risk_score']:.1f}%"):
            st.write(f"**Date:** {row['date']}")
            st.write(f"**Clinician:** {row['clinician']}")
            st.write(f"**Recommendation:** {row['recommendation']}")

# ============================================
# FUNCTION 7: CLINICIAN PERFORMANCE
# ============================================
def clinician_performance():
    st.subheader("👨‍⚕️ Clinician Performance")
    users = load_json(USERS_FILE)
    data = [{'Name': u.get('name'), 'Predictions': u.get('predictions_count', 0),
             'Patients': u.get('patients_registered', 0)} for u in users.values()]
    df = pd.DataFrame(data)
    st.dataframe(df)
    fig = px.bar(df, x='Name', y='Predictions', title='Predictions by Clinician')
    st.plotly_chart(fig)

# ============================================
# FUNCTION 8: CSV UPLOAD PATIENTS
# ============================================
def upload_csv_patients():
    st.subheader("📤 Upload Patients from CSV")

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

        if st.button("Import Patients"):
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
# FUNCTION 9: PATIENT LOCATION MAP
# ============================================
def patient_location_map():
    st.subheader("🗺️ Patient Location Map")
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

    st.markdown("---")
    st.markdown("### 📍 Pinpoint Location - Add Patient")

    col1, col2 = st.columns(2)
    with col1:
        pinpoint_lat = st.number_input("Latitude", value=-17.93, format="%.6f")
    with col2:
        pinpoint_lon = st.number_input("Longitude", value=31.03, format="%.6f")

    with st.form("pinpoint_form"):
        p_name = st.text_input("Patient Name")
        p_age = st.number_input("Age", 0, 120, 30)
        p_gender = st.selectbox("Gender", ["Male", "Female"])
        p_suburb = st.text_input("Suburb")

        if st.form_submit_button("Add Patient at This Location"):
            if p_name:
                patients = load_json(PATIENTS_FILE)
                pid = f"BUD-{len(patients)+1:04d}"
                patients[pid] = {
                    'patient_id': pid, 'name': p_name, 'age': p_age, 'gender': p_gender,
                    'phone': '', 'hiv_status': 'Unknown', 'tb_type': 'Pulmonary',
                    'registration_date': str(datetime.date.today()),
                    'registered_by': st.session_state.username,
                    'location': {'suburb': p_suburb, 'street_address': '', 'latitude': pinpoint_lat, 'longitude': pinpoint_lon},
                    'predictions': []
                }
                save_json(PATIENTS_FILE, patients)
                st.success(f"Added {p_name} at pinpointed location!")
                st.rerun()

# ============================================
# MAIN APP
# ============================================
def main_app():
    st.markdown("""
    <style>
    .header {background: linear-gradient(135deg, #1a5276, #2e86c1); padding: 1rem; border-radius: 10px; color: white; text-align: center;}
    .low-risk {background-color: #d4edda; padding: 1rem; border-radius: 10px; border-left: 5px solid #28a745; margin: 1rem 0;}
    .moderate-risk {background-color: #fff3cd; padding: 1rem; border-radius: 10px; border-left: 5px solid #ffc107; margin: 1rem 0;}
    .high-risk {background-color: #f8d7da; padding: 1rem; border-radius: 10px; border-left: 5px solid #dc3545; margin: 1rem 0;}
    </style>
    """, unsafe_allow_html=True)

    users = load_json(USERS_FILE)
    user_data = users.get(st.session_state.username, {})

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f'<div class="header"><h1>🏥 Budiriro Clinic</h1><p>Welcome, {user_data.get("name", st.session_state.username)}</p></div>', unsafe_allow_html=True)
    with col3:
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

    with st.sidebar:
        st.markdown(f"### 👋 {user_data.get('name', st.session_state.username)}")
        st.markdown(f"**Role:** {user_data.get('role', 'Clinician')}")
        st.markdown("---")
        menu = st.radio("📋 MENU", [
            "🎯 Predict Risk", "📝 Register Patient", "📋 View Patients",
            "🗺️ Patient Map", "📊 Analytics", "📥 Reports",
            "📅 Follow-up", "👨‍⚕️ Performance", "📤 CSV Upload"
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

# ============================================
# ROUTER
# ============================================
if st.session_state.logged_in:
    main_app()
elif st.session_state.page == "register":
    register_page()
else:
    login_page()

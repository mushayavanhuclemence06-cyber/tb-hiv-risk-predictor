def register_patient():
    st.markdown("<h3>📝 Register New Patient</h3>", unsafe_allow_html=True)
    
    with st.form("register_patient_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_name = st.text_input("Patient Full Name", key="reg_name")
            age = st.number_input("Age", 0, 120, 30, key="reg_age")
            gender = st.selectbox("Gender", ["Male", "Female"], key="reg_gender")
            phone = st.text_input("Phone Number (for SMS)", placeholder="e.g., 0771234567", key="reg_phone")
            email = st.text_input("Email Address (for Email)", placeholder="e.g., patient@example.com", key="reg_email")
        with col2:
            hiv_status = st.selectbox("HIV Status", ["Positive", "Negative", "Unknown"], key="reg_hiv")
            tb_type = st.selectbox("TB Type", ["Pulmonary", "Extrapulmonary"], key="reg_tb")
            registration_date = st.date_input("Registration Date", datetime.date.today(), key="reg_date")
        
        st.markdown("<h4>📍 Location Information</h4>", unsafe_allow_html=True)
        suburb = st.text_input("Suburb/Area", placeholder="e.g., Budiriro, Glen View", key="reg_suburb")
        street_address = st.text_input("Street Address", placeholder="House number, street name", key="reg_address")
        
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
                'email': email,  # NEW EMAIL FIELD
                'hiv_status': hiv_status,
                'tb_type': tb_type,
                'registration_date': str(registration_date),
                'registered_by': st.session_state.username,
                'location': {'suburb': suburb, 'street_address': street_address},
                'predictions': []
            }
            save_json(PATIENTS_FILE, patients)
            
            users_db = load_json(USERS_FILE)
            if st.session_state.username not in users_db:
                users_db[st.session_state.username] = {'predictions_count': 0, 'patients_registered': 0}
            users_db[st.session_state.username]['patients_registered'] = users_db[st.session_state.username].get('patients_registered', 0) + 1
            save_json(USERS_FILE, users_db)
            
            st.success(f"✅ Patient registered! ID: {patient_id}")
            if phone:
                send_sms(phone, patient_name, "appointment", "low")
            if email:
                send_email(email, patient_name, "welcome")  # NEW EMAIL FUNCTION
            st.balloons()

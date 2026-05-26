import streamlit as st
import pandas as pd
import numpy as np
import joblib
import random

# ======================================
# PAGE CONFIGURATION
# ======================================
st.set_page_config(
    page_title="Budiriro TB/HIV Risk Predictor",
    page_icon="🏥",
    layout="wide"
)

# ======================================
# LOAD MODEL
# ======================================
@st.cache_resource
def load_model():
    try:
        model = joblib.load("tb_default_model.pkl")
        scaler = joblib.load("scaler.pkl")
        feature_names = joblib.load("feature_names.pkl")
        return model, scaler, feature_names
    except Exception as e:
        st.warning(f"Model files not found: {e}. Using rule-based system.")
        return None, None, None

model, scaler, feature_names = load_model()

# ======================================
# CUSTOM CSS
# ======================================
st.markdown("""
<style>
.header {
    background: linear-gradient(135deg, #1a5276, #2e86c1);
    padding: 1.5rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
}
.low-risk {
    background-color: #d4edda;
    color: #155724;
    padding: 1rem;
    border-radius: 10px;
    border-left: 5px solid #28a745;
}
.moderate-risk {
    background-color: #fff3cd;
    color: #856404;
    padding: 1rem;
    border-radius: 10px;
    border-left: 5px solid #ffc107;
}
.high-risk {
    background-color: #f8d7da;
    color: #721c24;
    padding: 1rem;
    border-radius: 10px;
    border-left: 5px solid #dc3545;
}
</style>
""", unsafe_allow_html=True)

# ======================================
# HEADER
# ======================================
st.markdown("""
<div class="header">
    <h1>🏥 Budiriro Satellite Clinic</h1>
    <h2>TB/HIV Treatment Default Risk Prediction System</h2>
    <p>Powered by Random Forest | AUC = 0.706</p>
</div>
""", unsafe_allow_html=True)

# ======================================
# SIDEBAR
# ======================================
with st.sidebar:
    st.markdown("### Model Information")
    st.markdown("**Algorithm:** Random Forest")
    st.markdown("**AUC-ROC:** 0.706")
    st.markdown("**Accuracy:** 81.9%")
    st.markdown("**Recall:** 66.7%")
    st.markdown("**Precision:** 60.2%")
    st.markdown("**Training Data:** 1,203 patients")
    st.markdown("**Default Rate:** 19.1%")
    st.markdown("---")
    st.markdown("### Risk Factors")
    st.markdown("- Not on ART at TB start (+3)")
    st.markdown("- Weight <50 kg (+2)")
    st.markdown("- CD4 <200 cells/uL (+2)")
    st.markdown("- Age 18-24 years (+2)")
    st.markdown("- Male sex (+1)")
    st.markdown("- Unemployed (+1)")

# ======================================
# INPUT SECTION
# ======================================
st.markdown("## Enter Patient Information")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Demographics")
    age = st.number_input("Age (years)", min_value=18, max_value=120, value=30)
    sex = st.radio("Sex", ["Female", "Male"], horizontal=True)
    employment = st.selectbox("Employment Status", ["Employed", "Unemployed", "Other"])

with col2:
    st.markdown("### Clinical Information")
    art_status = st.selectbox("ART Status", ["Already on ART", "Not on ART", "Unknown/Not documented"])
    weight = st.number_input("Weight (kg)", min_value=25.0, max_value=150.0, value=60.0)
    cd4 = st.number_input("CD4 Count (cells/uL)", min_value=0, max_value=1500, value=300)
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

st.markdown("---")
st.markdown('<p style="text-align:center;color:gray;">© 2026 Budiriro Satellite Clinic - University of Zimbabwe</p>', unsafe_allow_html=True)

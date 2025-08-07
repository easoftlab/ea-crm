import spacy
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import os
import joblib

nlp = spacy.load('en_core_web_sm')

# Example: features to extract from a lead
FEATURES = [
    'seniority', 'department', 'company_size', 'industry', 'activity_level', 'intent_score'
]

# Dummy encoders and model for demonstration
seniority_encoder = LabelEncoder()
department_encoder = LabelEncoder()
industry_encoder = LabelEncoder()

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'lead_scoring_model.pkl')

try:
    model = joblib.load(MODEL_PATH)
except Exception:
    # Fallback to dummy model
    from sklearn.linear_model import LogisticRegression
    model = LogisticRegression()

# Example: fit encoders and model with your data (to be replaced with real data)
def fit_lead_scoring_model(leads, labels):
    seniorities = [l['seniority'] for l in leads]
    departments = [l['department'] for l in leads]
    industries = [l['industry'] for l in leads]
    X = np.column_stack([
        seniority_encoder.fit_transform(seniorities),
        department_encoder.fit_transform(departments),
        [l['company_size'] for l in leads],
        industry_encoder.fit_transform(industries),
        [l['activity_level'] for l in leads],
        [l['intent_score'] for l in leads],
    ])
    model.fit(X, labels)

# Example: extract features from a lead dict
def extract_lead_features(lead):
    # Use spaCy to analyze title, about, posts, etc.
    doc = nlp(lead.get('about', '') + ' ' + lead.get('recent_post', ''))
    # Dummy feature extraction for demo
    seniority = lead.get('seniority', 'Unknown')
    department = lead.get('department', 'Unknown')
    company_size = lead.get('company_size', 0)
    industry = lead.get('industry', 'Unknown')
    activity_level = lead.get('activity_level', 0)  # e.g., number of posts in last month
    intent_score = lead.get('intent_score', 0)      # e.g., from intent detection
    return [
        seniority_encoder.transform([seniority])[0],
        department_encoder.transform([department])[0],
        company_size,
        industry_encoder.transform([industry])[0],
        activity_level,
        intent_score
    ]

def score_lead(lead):
    features = np.array(extract_lead_features(lead)).reshape(1, -1)
    score = model.predict_proba(features)[0, 1]  # Probability of being a good lead
    return score 
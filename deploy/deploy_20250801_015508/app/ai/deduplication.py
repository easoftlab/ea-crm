import spacy
from fuzzywuzzy import fuzz
import os
import joblib

nlp = spacy.load('en_core_web_sm')

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'deduplication_model.pkl')

try:
    _dedup_model_bundle = joblib.load(MODEL_PATH)
    _dedup_threshold = _dedup_model_bundle['threshold']
except Exception:
    _dedup_threshold = 85

# Example: check if two leads are duplicates

def are_leads_duplicates(lead1, lead2, threshold=None):
    if threshold is None:
        threshold = _dedup_threshold
    # Fuzzy match company name
    name_score = fuzz.token_set_ratio(lead1['company_name'], lead2['company_name'])
    # Fuzzy match key person
    person_score = fuzz.token_set_ratio(lead1.get('key_person', ''), lead2.get('key_person', ''))
    # spaCy similarity for About/Notes
    about1 = lead1.get('about', '') or lead1.get('notes', '')
    about2 = lead2.get('about', '') or lead2.get('notes', '')
    doc1 = nlp(about1)
    doc2 = nlp(about2)
    about_score = doc1.similarity(doc2) if about1 and about2 else 0
    # Combine scores (weighted)
    combined_score = 0.5 * name_score + 0.3 * person_score + 0.2 * (about_score * 100)
    return combined_score >= threshold

# Example: deduplicate a list of leads
def deduplicate_leads(leads, threshold=85):
    unique = []
    for lead in leads:
        if not any(are_leads_duplicates(lead, u, threshold) for u in unique):
            unique.append(lead)
    return unique 
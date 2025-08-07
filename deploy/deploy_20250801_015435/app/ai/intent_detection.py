import spacy
import os
import joblib

nlp = spacy.load('en_core_web_sm')

# Example intent keywords/phrases
BUYING_INTENT_KEYWORDS = [
    'looking for', 'seeking', 'need', 'interested in', 'buy', 'purchase', 'vendor', 'supplier', 'solution', 'partner', 'collaborate', 'outsourcing', 'automation', 'expanding', 'growth', 'new project', 'open to', 'request for proposal', 'rfp', 'rfq'
]
HIRING_INTENT_KEYWORDS = [
    'hiring', 'recruiting', 'open position', 'job opening', 'join our team', 'career opportunity', 'talent acquisition', 'expanding team', 'we are hiring', 'apply now', 'vacancy', 'looking for', 'seeking', 'freelance', 'contractor'
]

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'intent_detection_model.pkl')

try:
    _intent_model_bundle = joblib.load(MODEL_PATH)
    _intent_model = _intent_model_bundle['model']
    _intent_vectorizer = _intent_model_bundle['vectorizer']
    def detect_intent(text):
        if not text.strip():
            return 0, []
        X = _intent_vectorizer.transform([text])
        score = float(_intent_model.predict_proba(X)[0][1])
        tags = ['positive_intent'] if score > 0.5 else []
        return score, tags
except Exception:
    # Fallback to keyword-based method
    def detect_intent(text):
        doc = nlp(text)
        score = 0
        tags = []
        for token in doc:
            if token.lemma_.lower() in BUYING_INTENT_KEYWORDS or token.lemma_.lower() in HIRING_INTENT_KEYWORDS:
                score += 1
                tags.append(token.lemma_)
        return min(score / 3, 1.0), tags 
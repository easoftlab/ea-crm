import spacy
import random
import os
import joblib
from collections import Counter

nlp = spacy.load('en_core_web_sm')

SHORT_TEMPLATES = [
    "Hi {name}, let's connect!",
    "Hello {name}, would love to connect.",
    "Hi {name}, thanks for connecting!"
]
MEDIUM_TEMPLATES = [
    "Hi {name}, I came across your profile and was impressed by your work at {company}. Let's connect and share insights!",
    "Hello {name}, as a fellow {role} in {industry}, I'd love to connect and discuss industry trends.",
    "Hi {name}, always great to meet professionals from {company}. Looking forward to connecting!"
]
LONG_TEMPLATES = [
    "Hi {name}, I noticed your recent achievements at {company} and your experience in {industry}. I'd be delighted to connect and exchange ideas on how our industries are evolving.",
    "Hello {name}, your leadership in {industry} and your recent post really resonated with me. If you're open to it, I'd love to connect and discuss potential collaboration opportunities.",
    "Hi {name}, I see we share mutual connections and similar interests in {industry}. Looking forward to learning from your experience and sharing insights!"
]
TONES = ['friendly', 'formal', 'enthusiastic']

MESSAGE_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai_message_model.pkl')

def retrain_message_model(leads):
    # Simple frequency-based model: which variant gets most replies
    reply_variants = [lead.message_variant for lead in leads if lead.message_reply and lead.message_variant]
    if reply_variants:
        variant_counts = Counter(reply_variants)
        best_variant = variant_counts.most_common(1)[0][0]
        joblib.dump({'best_variant': best_variant, 'variant_counts': variant_counts}, MESSAGE_MODEL_PATH)
        print(f'Message model retrained. Best variant: {best_variant}')
    else:
        print('Not enough reply data to retrain message model.')

def predict_best_variant():
    try:
        model = joblib.load(MESSAGE_MODEL_PATH)
        return model['best_variant']
    except Exception:
        return None

def ai_generate_message(profile_data, forced_variant=None):
    """
    Generate a personalized LinkedIn message using spaCy to extract context from the profile.
    profile_data: dict with keys 'name', 'company', 'about', 'recent_post', 'industry', 'role', 'mutuals' (list)
    """
    doc = nlp((profile_data.get('about', '') or '') + ' ' + (profile_data.get('recent_post', '') or ''))
    # 0. Reference recent post if available
    recent_post = profile_data.get('recent_post', '').strip()
    if recent_post:
        msg = f"Hi {profile_data.get('name', 'there')}, I saw your recent post: '{recent_post[:80]}...' and wanted to connect!"
        return msg, 'recent_post'
    # 1. Mention project, award, product, event, org, location, or date
    for ent in doc.ents:
        if ent.label_ in ['WORK_OF_ART', 'PRODUCT', 'EVENT', 'AWARD', 'ORG'] or 'project' in ent.text.lower():
            msg = f"Hi {profile_data.get('name', 'there')}, congrats on your recent {ent.label_.lower()} '{ent.text}'! Would love to connect and discuss {profile_data.get('industry', 'the industry')}."
            return msg, 'entity_congrats'
        if ent.label_ == 'GPE':
            msg = f"Hi {profile_data.get('name', 'there')}, I see you’re based in {ent.text}. Always great to connect with professionals from {ent.text}!"
            return msg, 'location_gpe'
        if ent.label_ == 'DATE':
            msg = f"Hi {profile_data.get('name', 'there')}, congrats on your recent achievement in {ent.text}! Would love to connect."
            return msg, 'date_achievement'
    # 2. Mention skill
    for ent in doc.ents:
        if ent.label_ == 'SKILL':
            msg = f"Hi {profile_data.get('name', 'there')}, your expertise in {ent.text} is impressive! Would love to connect."
            return msg, 'skill_mention'
    # 3. Mention mutual connections
    mutuals = profile_data.get('mutuals', [])
    if mutuals:
        msg = f"Hi {profile_data.get('name', 'there')}, I noticed we both know {mutuals[0]}. Always great to connect with mutual contacts!"
        return msg, 'mutual_connection'
    # 4. Mention industry or role
    if profile_data.get('industry') and profile_data.get('role'):
        msg = f"Hi {profile_data.get('name', 'there')}, as a fellow {profile_data['role']} in {profile_data['industry']}, I’d love to connect and share insights."
        return msg, 'industry_role'
    # 5. Randomly select tone and length for fallback
    tone = random.choice(TONES)
    length = random.choices(['short', 'medium', 'long'], weights=[0.2, 0.5, 0.3])[0]
    # Forced variant logic
    if forced_variant:
        # Parse forced_variant like 'short_0', 'medium_2', etc.
        try:
            group, idx = forced_variant.split('_')
            idx = int(idx)
            if group == 'short':
                template = SHORT_TEMPLATES[idx % len(SHORT_TEMPLATES)]
            elif group == 'medium':
                template = MEDIUM_TEMPLATES[idx % len(MEDIUM_TEMPLATES)]
            elif group == 'long':
                template = LONG_TEMPLATES[idx % len(LONG_TEMPLATES)]
            else:
                template = random.choice(MEDIUM_TEMPLATES)
            variant = forced_variant
        except Exception:
            template = random.choice(MEDIUM_TEMPLATES)
            variant = 'medium_fallback'
    else:
        if length == 'short':
            template = random.choice(SHORT_TEMPLATES)
            variant = f'short_{SHORT_TEMPLATES.index(template)}'
        elif length == 'medium':
            template = random.choice(MEDIUM_TEMPLATES)
            variant = f'medium_{MEDIUM_TEMPLATES.index(template)}'
        else:
            template = random.choice(LONG_TEMPLATES)
            variant = f'long_{LONG_TEMPLATES.index(template)}'
    msg = template.format(
        name=profile_data.get('name', 'there'),
        company=profile_data.get('company', ''),
        industry=profile_data.get('industry', ''),
        role=profile_data.get('role', ''),
        tone=tone
    )
    return msg, variant 
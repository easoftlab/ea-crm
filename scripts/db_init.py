from app import create_app, db
from app.models import Lead, Contact, ContactPhone, ContactEmail, SocialProfile, ScrapedLead, FollowUpHistory
import datetime
from sqlalchemy import inspect

app = create_app()
 
with app.app_context():
    # Create all tables
    db.create_all()
    print("Database tables created successfully!")
    # Remove any demo/mockup data insertion for PixelPro Studios and Acme Global 

def init_scrap_db():
    from app import db
    db.create_all(bind_key='scrap')

def ensure_scraped_leads_columns():
    from sqlalchemy import inspect, text
    from app import db
    engine = db.get_engine(app, bind='scrap')
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('scraped_leads')]
    with engine.connect() as conn:
        if 'about' not in columns:
            conn.execute(text('ALTER TABLE scraped_leads ADD COLUMN about VARCHAR(1024)'))
        if 'recent_post' not in columns:
            conn.execute(text('ALTER TABLE scraped_leads ADD COLUMN recent_post VARCHAR(1024)'))
        if 'ai_message' not in columns:
            conn.execute(text('ALTER TABLE scraped_leads ADD COLUMN ai_message VARCHAR(1024)'))
        if 'message_variant' not in columns:
            conn.execute(text('ALTER TABLE scraped_leads ADD COLUMN message_variant VARCHAR(32)'))
        if 'message_reply' not in columns:
            conn.execute(text('ALTER TABLE scraped_leads ADD COLUMN message_reply VARCHAR(1024)'))

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        init_scrap_db()
        ensure_scraped_leads_columns() 
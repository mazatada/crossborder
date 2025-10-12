from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

def init_db():
    from .models import Product, Job, Artifact, Audit, PNSubmission, HSOverride
    db.create_all()

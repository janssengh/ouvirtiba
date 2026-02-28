# admin/blog_post/models.py

from datetime import datetime
from extension import db

# =========================================================
# CLASSE BASE ABSTRATA (MIXIN)
# =========================================================
class Base(db.Model):
    __abstract__ = True
    __table_args__ = {'schema': 'ouvirtiba'}

# =========================================================
# MODEL BLOG POST
# =========================================================
class BlogPost(Base):
    __tablename__ = 'blog_post'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.String(355), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(45), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=True)
    image = db.Column(db.String(150), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=True)
    
    def __repr__(self):
        return f'<BlogPost {self.title}>'
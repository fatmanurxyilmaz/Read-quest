# app/models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    test_results = db.relationship('TestResult', backref='author', lazy='dynamic')
    saved_books = db.relationship('SavedBook', backref='owner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reader_type = db.Column(db.String(140))
    score = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<TestResult {self.reader_type}>'

class SavedBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.String(140))
    title = db.Column(db.String(140))
    author = db.Column(db.String(140))
    thumbnail = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<SavedBook {self.title}>'
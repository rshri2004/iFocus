from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()
DB_NAME = "ifocus.db"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Student")

    assignments = db.relationship("Assignment", back_populates="teacher", lazy="dynamic")
    notes = db.relationship("Note", back_populates="user", lazy="dynamic")
    enrollments = db.relationship('Enrollment', back_populates='user', cascade="all, delete-orphan", lazy="dynamic")
    focus_data = db.relationship("FocusData", back_populates="user", lazy="dynamic")

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    pdf_path = db.Column(db.String(2000), nullable=True)
    youtube_url = db.Column(db.String(2000), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    insights = db.Column(db.Text, nullable=True)

    teacher = db.relationship("User", back_populates="assignments")
    notes = db.relationship("Note", back_populates="assignment", cascade="all, delete-orphan", lazy="dynamic")
    enrollments = db.relationship("Enrollment", back_populates="assignment", cascade="all, delete-orphan",
                                  lazy="dynamic")
    focus_data = db.relationship("FocusData", back_populates="assignment", lazy="dynamic")


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.pdf_path and not self.youtube_url:
            raise ValueError("An assignment must have either a PDF or a YouTube video.")

    @validates('pdf_path', 'youtube_url')
    def validate_assignment_type(self, key, value):
        if key == 'pdf_path' and value and self.youtube_url:
            raise ValueError("An assignment cannot have both a PDF and a YouTube video.")
        if key == 'youtube_url' and value and self.pdf_path:
            raise ValueError("An assignment cannot have both a YouTube video and a PDF.")
        return value


    def is_pdf_assignment(self):
        return self.pdf_path is not None

    def is_video_assignment(self):
        return self.youtube_url is not None

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id', ondelete='CASCADE'), nullable=False)
    grade = db.Column(db.Float, nullable=True)
    insights = db.Column(db.Text, nullable=True)

    user = db.relationship('User', back_populates='enrollments')
    assignment = db.relationship('Assignment', back_populates='enrollments')

    @validates('grade')
    def validate_grade(self, key, value):
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Grade must be between 0 and 100.")
        return value


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.Text, nullable=False)

    user = db.relationship("User", back_populates="notes")
    assignment = db.relationship("Assignment", back_populates="notes")



class FocusData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    x_coord = db.Column(db.Float, nullable=False)
    y_coord = db.Column(db.Float, nullable=False)
    outside = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="focus_data")
    assignment = db.relationship("Assignment", back_populates="focus_data")
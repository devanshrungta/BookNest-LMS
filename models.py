from app import app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import datetime

db=SQLAlchemy(app)


class user(db.Model):
    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(), unique=True)
    email = db.Column(db.String, unique=True)
    date_created = db.Column(db.DateTime, default=datetime.datetime.now) 
    passhash = db.Column(db.String(256))
    is_admin=db.Column(db.Boolean, default=False)

class section(db.Model):
    section_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    date_created = db.Column(db.DateTime, default=datetime.datetime.now)
    description = db.Column(db.String)
    books=db.relationship('book', backref='sections', lazy=True, cascade='all, delete-orphan')

class book(db.Model):
    book_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    content = db.Column(db.String)
    date_created = db.Column(db.DateTime, default=datetime.datetime.now)
    authors = db.Column(db.String)
    section_id=db.Column(db.Integer, db.ForeignKey('section.section_id'))

class requests(db.Model):
    request_id = db.Column( db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer,   db.ForeignKey("user.user_id"))
    book_id = db.Column(db.Integer,  db.ForeignKey("book.book_id"))
    request_date = db.Column(db.DateTime, default=datetime.datetime.now)
    grant_date = db.Column(db.DateTime)
    status = db.Column(db.String)  #pending or approved or returned or rejected

class ratings(db.Model):
    ratings_id=db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer,   db.ForeignKey("user.user_id"))
    book_id = db.Column(db.Integer,  db.ForeignKey("book.book_id"))
    rate=db.Column(db.Integer)

class bought(db.Model):
    bought_id=db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer,   db.ForeignKey("user.user_id"))
    book_id = db.Column(db.Integer,  db.ForeignKey("book.book_id"))
    bought_date = db.Column(db.DateTime, default=datetime.datetime.now)

with app.app_context():
    db.create_all()

    #creating a default admin
    # try:
    #     num_rows_deleted = db.session.query(requests).delete()
    #     db.session.commit()
    # except:
    #     db.session.rollback()

    admin=user.query.filter_by(is_admin=True).first()
    if not admin:
        password=generate_password_hash('admin')
        admin=user(username='Admin', passhash=password, is_admin=True)
        db.session.add(admin)
        db.session.commit()

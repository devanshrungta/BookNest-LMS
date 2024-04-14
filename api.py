from flask_restful import Resource, Api, request
from app import app
from models import db, section, book


api = Api(app)

class Section(Resource):
    def get(self):
        sections = section.query.all()
        return {'sections': [{'section_id': section.section_id, 'name': section.name, 'description': section.description} for section in sections]}
    
    def post(self):
        data = request.get_json()
        if not data:
            return {'message': 'No JSON data provided'}, 400
        new_section = section(name=data['name'], description=data['description'])
        db.session.add(new_section)
        db.session.commit()
        return "New section created", 201

class Book(Resource):
    def get(self):        
        books = book.query.all()
        return {'books': [{'book_id': book.book_id, 'name': book.name, 'content': book.content, 'authors': book.authors} for book in books]}
    def post(self):
        data = request.get_json()
        if not data:
            return {'message': 'No JSON data provided'}, 400
        new_book = book(name=data['name'], content=data['content'], authors=data['authors'], section_id=data['section_id'])
        db.session.add(new_book)
        db.session.commit()
        return "New book created", 201
    
api.add_resource(Section, '/api/section')
api.add_resource(Book, '/api/book')

    
        
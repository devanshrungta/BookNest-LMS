from app import app
from flask import Flask, render_template, flash, redirect, url_for, request, session
from sqlalchemy import func
from models import db, user, section, book, requests, bought, ratings
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta

#imports for print functionality
from flask import send_file
import tempfile
from fpdf import FPDF


# LOGIN AND REGISTER PAGES ---------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/login", methods=["POST"])
def login_post():
    username=request.form.get('username')
    password=request.form.get('password')

    if not username or not password:
        flash('Please fill out all fields')
        return redirect(url_for('login'))
    
    User=user.query.filter_by(username=username).first()
    if not User:
        flash('Username does not exists')
        return redirect(url_for('login'))

    if not check_password_hash(User.passhash, password):
        flash('Incorrect password')
        return redirect(url_for('login'))
    
    session['user_id'] = User.user_id
    flash('Login successful')
    return redirect(url_for('dashboard'))


@app.route("/register")
def register():
   return render_template('register.html')

@app.route("/register", methods=["POST"])
def register_post():
    username=request.form.get('username')
    email=request.form.get('email')
    password=request.form.get('password')
    confirm_password=request.form.get('confirm_password')

    if not username or not email or not password or not confirm_password:
        flash('Please fill out all fields')
        redirect(url_for('register'))
    
    if password!=confirm_password:
        flash('Password do not match')
        redirect(url_for('register'))
    
    username_check=user.query.filter_by(username=username).first()
    if username_check:
        flash('Username already exists')
        redirect(url_for('register'))
    
    passhash=generate_password_hash(password)
    new_user=user(username=username, email=email, passhash=passhash)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('login'))

# AUTHENTICATION AND AUTHORIZATION ---------------------------------------------------------------------------------------------------------------------------------------------------------
def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please login to proceed')
            return redirect(url_for('login'))
    return inner

def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue')
            return redirect(url_for('login'))
        User = user.query.get(session['user_id'])
        if not User.is_admin:
            flash('You are not authorized to access this page')
            return redirect(url_for('dashboard'))
        return func(*args, **kwargs)
    return inner

# DASHBOARD AND USER PAGES ---------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/')
@auth_required
def dashboard():
   if 'user_id' in session:
       User=user.query.get(session['user_id'])
       if User.is_admin:
           return redirect(url_for('admin'))
       else:
           return redirect(url_for('user_dashboard', id=session['user_id']))
   else:
       flash('Please login to continue')
       return redirect(url_for('login'))
   
@app.route('/dashboard/<int:id>')
@auth_required
def user_dashboard(id):
    User=user.query.get(id)
    my_books=db.session.query(book).join(requests, requests.book_id == book.book_id).filter(requests.user_id==id, requests.status=='approved').all()
    recently_added_books=book.query.order_by(book.date_created.desc()).all()
    top_books=db.session.query(\
    book.book_id,\
    book.name,\
    book.authors,\
    func.avg(ratings.rate).label('average_rating')\
    ).join(\
    ratings, ratings.book_id == book.book_id\
    ).group_by(\
    book.book_id\
    ).order_by(\
    func.avg(ratings.rate).desc()\
    ).limit(5).all()
    return render_template('userDashboard.html', User=User , recently_added_books=recently_added_books, my_books=my_books, top_books=top_books , active='Dashboard')     #active, username

@app.route('/MyBooks/<int:id>')
@auth_required
def myBook(id):
    User=user.query.get(id)
    request=requests.query.filter_by(user_id=id, status='approved').all()
    request = db.session.query(requests.request_id, requests.request_date, requests.grant_date, section.name.label('section_name'), book.name, book.authors, book.content, requests.book_id)\
    .join(user, user.user_id == requests.user_id)\
    .join(book, book.book_id == requests.book_id)\
    .join(section, section.section_id == book.section_id)\
    .filter(requests.status=='approved', requests.user_id==session['user_id'])\
    .all()
    return render_template('myBooks.html', User=User, request=request, active='myBook')

@app.route('/browseBooks/')
@auth_required
def browseBooks():
    User=user.query.get(session['user_id'])
    books=book.query.all()

    #search functionality
    book_name=request.args.get('book_name') or ''
    author=request.args.get('author') or ''
    if book_name and author:
        books=book.query.filter(book.name.ilike(f'%{book_name}%'), book.authors.ilike(f'%{author}%')).all()
    elif book_name:
        books=book.query.filter(book.name.ilike(f'%{book_name}%')).all()
    elif author:
        books=book.query.filter(book.authors.ilike(f'%{author}%')).all()

    return render_template('browseBooks.html', User=User, active='browseBooks', books=books)

@app.route('/browseSections/')
@auth_required
def browseSections():
    User=user.query.get(session['user_id'])
    sections=section.query.order_by(section.date_created.desc()).all()

    #search functionality
    Sections=request.args.get('Sections') or ''
    if Sections:
        sections=section.query.filter(section.name.ilike(f'%{Sections}%')).all()
    return render_template('browseSections.html', sections=sections, User=User, active='browseSections', Sections=Sections)

@app.route('/profile/<int:id>')
@auth_required
def profile(id):
    User=user.query.get(id)
    return render_template('profile.html', User=User)
@app.route('/profile/<int:id>', methods=["POST"])
def profile_post(id):
    User=user.query.get(id)
    username=request.form.get('username')
    email=request.form.get('email')
    oldpassword=request.form.get('oldpassword')
    newpassword=request.form.get('newpassword')

    if not username or not email or not oldpassword:
        flash('Please fill out all fields')
        return redirect(url_for('profile',id=User.user_id))
    
    if  not check_password_hash(User.passhash, oldpassword):
        flash('Password does not match')
        return redirect(url_for('profile',id=User.user_id))
    
    if username != User.username:
        username_check = user.query.filter_by(username=username).first()
        if username_check:
            flash('Username already exists')
            return redirect(url_for('profile',id=User.user_id))
        
    if newpassword:
        User.passhash=generate_password_hash(newpassword)
        
    User.username=username
    User.email=email
    db.session.commit()
    flash('Profile updated successfully')
    return redirect(url_for('profile',id=User.user_id))

# BOOKS AND REQUESTS ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/view_book/<int:id>')
@auth_required
def view_book_user(id):
    User=user.query.get(session['user_id'])
    Book=book.query.get(id)
    rating= db.session.query(func.avg(ratings.rate)).filter(ratings.book_id == id).scalar()
    status=requests.query.filter_by(user_id=session['user_id'], book_id=id).order_by(requests.request_date.desc()).first()
    return render_template('viewBook.html', Book=Book, status=status, User=User, active='browseBooks', rating=rating)
@app.route('/view_book/<int:id>', methods=['POST'])
@auth_required
def view_book_user_post(id):
    rate=request.form.get('rate')
    if not rate:
        flash('Please rate the book')
        return redirect(url_for('view_book_user', id=id))
    check_rate=ratings.query.filter_by(user_id=session['user_id'], book_id=id).first()
    if check_rate:
        check_rate.rate=rate
    else:
        new_rate=ratings(user_id=session['user_id'], book_id=id, rate=rate)
        db.session.add(new_rate)
    db.session.commit()
    flash('Book rated successfully')
    return redirect(url_for('view_book_user', id=id))

@app.route('/request_book/<int:id>')
@auth_required
def request_book(id):
    count = requests.query.filter((requests.user_id==session['user_id']) & ((requests.status=='pending') | (requests.status=='approved'))).count()
    if count > 5:
        flash('You have already requested 5 books. Please wait for approval or return a book before requesting a new one.')
        return redirect(url_for('view_book_user', id=id))
    
    Request=requests.query.filter_by(user_id=session['user_id'], book_id=id).order_by(requests.request_date.desc()).first()
    if Request:
        if Request.status=='pending':   
            flash('Book is already requested. Kindly wait for admin approval.')
            return redirect(url_for('view_book_user', id=id)) 
        if Request.status=='approved':
            flash('You already have access to this book')
            return redirect(url_for('view_book_user', id=id))
            
    new_request=requests(user_id=session['user_id'], book_id=id, status='pending')
    db.session.add(new_request)
    db.session.commit()
    flash('Book requested successfully! Kindly wait for the admin to approve')
    return redirect(url_for('view_book_user', id=id))
        
@app.route('/read_book/<int:id>')
@auth_required
def read_book(id):
    User=user.query.get(session['user_id'])
    if requests.query.filter_by(user_id=session['user_id'], book_id=id, status='approved').first():   
        Book=book.query.get(id)
        rating= db.session.query(func.avg(ratings.rate)).filter(ratings.book_id == id).scalar()
        return render_template('readBook.html', Book=Book, User=User, rating=rating)
    flash("You don't have access to read this book. Kindly request the book first.")
    return redirect(url_for('view_book_user', id=id))
@app.route('/read_book/<int:id>', methods=['POST'])
@auth_required
def read_book_post(id):
    rate=request.form.get('rate')
    if not rate:
        flash('Please rate the book')
        return redirect(url_for('read_book', id=id))
    check_rate=ratings.query.filter_by(user_id=session['user_id'], book_id=id).first()
    if check_rate:
        check_rate.rate=rate
    else:
        new_rate=ratings(user_id=session['user_id'], book_id=id, rate=rate)
        db.session.add(new_rate)
    db.session.commit()
    flash('Book rated successfully')
    return redirect(url_for('read_book', id=id))
    
@app.route('/return_book/<int:id>')
@auth_required
def return_book(id):
    request=requests.query.filter_by(user_id=session['user_id'], book_id=id, status='approved').first()
    if not request:
        flash('You have not requested this book')
        return redirect(url_for('view_book_user', id=id))
    if request.status=='pending':
        flash('You have not yet received the book')
        return redirect(url_for('view_book_user', id=id))
    request.status='returned'
    db.session.commit()
    flash('Book returned successfully')
    return redirect(url_for('view_book_user', id=id))

@app.route('/buy_book/<int:id>')
@auth_required
def buy_book(id):   
    new_bought=bought(user_id=session['user_id'], book_id=id)
    db.session.add(new_bought)
    db.session.commit()
    flash('Book bought successfully')

    # Get the book content
    Book = book.query.get(id)
    pdf_content = Book.content

    # Create a temporary PDF file
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size = 15)

    # Add the book name, author, and section name
    pdf.cell(200, 10, txt = f"Name: {Book.name}", ln = True, align = 'C')
    pdf.cell(200, 10, txt = f"Author: {Book.authors}", ln = True, align = 'C')
    pdf.cell(200, 10, txt = f"Section: {Book.sections.name}", ln = True, align = 'C')

    # Add a line break
    pdf.ln(10)

    # Add the book content
    pdf.multi_cell(200, 10, txt = pdf_content)

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)

    return send_file(temp.name, as_attachment=True)

@app.route('/viewBySection/<int:id>')
@auth_required
def viewBySection(id):
    User=user.query.get(session['user_id'])
    Books=book.query.filter_by(section_id=id).all()
    return render_template('viewBySection.html', Books=Books, User=User, active='browseSections')

# DELETE AND LOGOUT -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/deleteAccount/<int:id>')
@auth_required
def deleteAccount(id):
    User=user.query.get(id)
    return render_template('deleteAccount.html', User=User)
@app.route('/deleteAccount/<int:id>', methods=['POST'])
@auth_required
def deleteAccount_post(id):
    User=user.query.get(id)
    oldpassword=request.form.get('oldpassword')

    if not oldpassword:
        flash('Please enter your password')
        return redirect(url_for('deleteAccount',id=User.user_id))
    
    if not check_password_hash(User.passhash, oldpassword):
        flash('Password does not match')
        return redirect(url_for('deleteAccount',id=User.user_id))
        
    db.session.delete(User)
    db.session.commit()
    flash('Account deleted successfully. Please Login/Register to continue')
    return redirect(url_for('login'))

@app.route('/logout')
@auth_required
def logout():
    session.pop('user_id')
    return redirect(url_for('login'))



# ADMIN PAGES -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/admin/dashboard')                            #quick manage requests, section, book, user
@admin_required
def admin():                                    # stats --> 1. no. of books approved(line chart) 2. no of books sold 3. no. of books  4. no. of sections    
    User=user.query.get(session['user_id'])
    top_requests = db.session.query(requests.request_id, requests.user_id, requests.book_id, requests.request_date, requests.status, user.username, book.name)\
    .join(user, user.user_id == requests.user_id)\
    .join(book, book.book_id == requests.book_id)\
    .filter(requests.status=='pending')\
    .limit(5).all()
    books=book.query.limit(5).all()
    sections=section.query.limit(5).all()
    
    return render_template('/admin_pages/adminDashboard.html', User=User, top_requests=top_requests, books=books,sections=sections, active='Dashboard')

@app.route('/admin/section_management')         #CRUD; later can show stats like top sections; sections having most books, etc
@admin_required
def sectionManagement():
    Sections=section.query.all()
    User=user.query.get(session['user_id'])

    #search functionality
    sections=request.args.get('sections') or ''
    if sections:
        Sections=section.query.filter(section.name.ilike(f'%{sections}%')).all()
    

    return render_template('/admin_pages/adminSection.html', active='Section',User=User, Sections=Sections, sections=sections)

@app.route('/admin/book_management')            #CRUD; monitor it to whom being assigned
@admin_required
def bookManagement():
    books=book.query.all()
    User=user.query.get(session['user_id'])

    #search functionality
    book_name=request.args.get('book_name') or ''
    author=request.args.get('author') or ''
    if book_name and author:
        books=book.query.filter(book.name.ilike(f'%{book_name}%'), book.authors.ilike(f'%{author}%')).all()
    elif book_name:
        books=book.query.filter(book.name.ilike(f'%{book_name}%')).all()
    elif author:
        books=book.query.filter(book.authors.ilike(f'%{author}%')).all()

    return render_template('/admin_pages/adminBook.html', active='Books',User=User, books=books, book_name=book_name, author=author)

@app.route('/admin/manage_requests')             #APPROVE/REJECT; hyperlink user to their user profile page
@admin_required
def manageRequest():
    request=requests.query.filter_by(status='pending')
    Requests = db.session.query(requests.request_id, requests.user_id, requests.book_id, requests.request_date, requests.status, user.username, book.name)\
    .join(user, user.user_id == requests.user_id)\
    .join(book, book.book_id == requests.book_id)\
    .filter(requests.status=='pending')\
    .all()
    User=user.query.get(session['user_id'])
    return render_template('/admin_pages/adminManageRequests.html', active='Requests', User=User, request=request, Requests=Requests)

@app.route('/admin/user_management')             #TOP USER BY(days active, # books, longest streak)
@admin_required
def userManagement():                           #total number of books read, currently borrowed book
    users = db.session.query(user.user_id, user.username, user.email, user.date_created, func.count(requests.request_id).label('total_books_borrowed'))\
    .join(requests, user.user_id == requests.user_id, isouter=True).group_by(user.user_id).all()
    User=user.query.get(session['user_id'])
    
    return render_template('/admin_pages/adminUserManagement.html', active='Users', User=User, users=users)

@app.route('/admin/borrowed_books_management') 
@admin_required
def borrowedBooksManagement():
    request=db.session.query(requests.request_id, requests.grant_date, user.username, book.name)\
    .join(user, user.user_id == requests.user_id)\
    .join(book, book.book_id == requests.book_id)\
    .filter(requests.status=='approved')\
    .all()
    User=user.query.get(session['user_id'])
    for i in range(len(request)):
        request_id, grant_date, username, book_name = request[i]
        days_since_grant = (datetime.now() - grant_date).days
        request[i] = (request_id, grant_date, username, book_name, days_since_grant)
    return render_template('/admin_pages/borrowedBooks.html', active='borrowedBooks', User=User, request=request)

@app.route('/admin/statistics')
@admin_required
def statistics():
    User=user.query.get(session['user_id'])

    total_books=db.session.query(func.count(book.book_id)).scalar()
    total_sections=db.session.query(func.count(section.section_id)).scalar()
    total_users=db.session.query(func.count(user.user_id)).scalar()
    total_requests=db.session.query(func.count(requests.request_id)).scalar()
    total_bought=db.session.query(func.count(bought.bought_id)).scalar()
    total_ratings=db.session.query(func.count(ratings.ratings_id)).scalar()

    subquery_requests = db.session.query(requests.book_id, func.count(requests.request_id).label('total_requests')).group_by(requests.book_id).subquery()
    subquery_ratings = db.session.query(ratings.book_id, func.count(ratings.ratings_id).label('total_ratings')).group_by(ratings.book_id).subquery()
    subquery_bought = db.session.query(bought.book_id, func.count(bought.bought_id).label('total_bought')).group_by(bought.book_id).subquery()
    book_stats = db.session.query(book.book_id, book.name, subquery_requests.c.total_requests, subquery_ratings.c.total_ratings, subquery_bought.c.total_bought)\
    .outerjoin(subquery_requests, book.book_id == subquery_requests.c.book_id)\
    .outerjoin(subquery_ratings, book.book_id == subquery_ratings.c.book_id)\
    .outerjoin(subquery_bought, book.book_id == subquery_bought.c.book_id)\
    .all()


    return render_template('/admin_pages/adminStatistics.html', active='statistics', User=User, total_books=total_books, total_sections=total_sections, total_users=total_users, total_requests=total_requests, total_bought=total_bought, total_ratings=total_ratings, book_stats=book_stats)



# ADMIN CRUD OPERATIONS ON SECTION ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/admin/section_management/add')
@admin_required
def add_section():
    User=user.query.get(session['user_id'])
    return render_template('/admin_pages/addSection.html', User=User, active='Section')
@app.route('/admin/section_management/add', methods=['post'])
@admin_required
def add_section_post():
    name=request.form.get('name')
    description=request.form.get('description')
    if not name or not description:
        flash('Please fill out all fields')
        return redirect(url_for('add_section'))
    new_section=section(name=name,description=description)
    db.session.add(new_section)
    db.session.commit()
    flash('New section added successfully!')
    return redirect(url_for('sectionManagement'))

@app.route('/admin/section_management/view/<int:id>')       #reuse it for general user too
@admin_required
def view_section(id):
    User=user.query.get(session['user_id'])
    Section=section.query.get(id)
    if not Section:
        flash('Category does not exists.')
        return render_template(url_for('sectionManagement', active='Section'))
    return render_template('/admin_pages/viewSection.html', active='Section', User=User, Section=Section)

@app.route('/admin/section_management/edit/<int:id>')       #don't reuse it and delete wala for user! auth only to admin
@admin_required
def edit_section(id):
    User=user.query.get(session['user_id'])
    Section=section.query.get(id)
    if not Section:
        flash('Section does not exist')
        return redirect(url_for('edit_section', id=id))
    return render_template('/admin_pages/editSection.html', active='Section', User=User, Section=Section)
@app.route('/admin/section_management/edit/<int:id>', methods=['post'])
@admin_required
def edit_section_post(id):
    name=request.form.get('name')
    description=request.form.get('description')
    Section=section.query.get(id)
    if not name or not description:
        flash('Please fill out all fields')
        return redirect(url_for('edit_section', id))   
    Section.name=name
    Section.description=description
    db.session.commit()
    flash('Section edited successfully')
    return redirect(url_for('sectionManagement'))


@app.route('/admin/section_management/delete/<int:id>')
@admin_required
def delete_section(id):
    User=user.query.get(session['user_id'])
    Section=section.query.get(id)
    if not Section:
        flash('Section does not exists!')
        return redirect(url_for('sectionManagement'))
    return render_template('/admin_pages/deleteSection.html', active='Section', User=User, Section=Section)
@app.route('/admin/section_management/delete/<int:id>', methods=['post'])
@admin_required
def delete_section_post(id):
    Section=section.query.get(id)
    if not Section:
        flash('Section does not exists!')
        return redirect(url_for('sectionManagement'))
    db.session.delete(Section)
    db.session.commit()
    flash('Section deleted successfully!')
    return redirect(url_for('sectionManagement'))


# ADMIN CRUD OPERATIONS ON BOOK ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/admin/book_management/add')
@admin_required
def add_book():
    User=user.query.get(session['user_id'])
    sections=section.query.all()
    return render_template('/admin_pages/addBook.html', active='Books', User=User, sections=sections)
@app.route('/admin/book_management/add', methods=['post'])
@admin_required
def add_book_post():
    name=request.form.get('name')
    description=request.form.get('description')
    authors=request.form.get('authors')
    section_id=request.form.get('sectionID')
    section_id=int(section_id.split('.')[0])
    if not name or not description or not authors or not section_id:
        flash('Please fill out all fields')
        return redirect(url_for('add_book'))
    new_book=book(name=name,content=description, authors=authors, section_id=section_id)
    db.session.add(new_book)
    db.session.commit()
    flash('New Book added successfully!')
    return redirect(url_for('bookManagement'))

@app.route('/admin/book_management/view/<int:id>')
@admin_required
def view_book(id):
    User=user.query.get(session['user_id'])
    Book=book.query.get(id)
    if not Book:
        flash('Book does not exists.')
        return render_template(url_for('bookManagement'))
    return render_template('/admin_pages/viewBook.html', active='Books', User=User, Book=Book)

@app.route('/admin/book_management/edit/<int:id>')
@admin_required
def edit_book(id):
    User=user.query.get(session['user_id'])
    Book=book.query.get(id)
    if not Book:
        flash('Book does not exist')
        return redirect(url_for('edit_book', id=id))
    return render_template('/admin_pages/editBook.html', active='Books', User=User, Book=Book)
@app.route('/admin/book_management/edit/<int:id>', methods=['post'])
@admin_required
def edit_book_post(id):
    name=request.form.get('name')
    authors=request.form.get('authors')
    content=request.form.get('content') 
    Book=book.query.get(id)
    if not name or not content:
        flash('Please fill out all fields')
        return redirect(url_for('edit_book', id))   
    Book.name=name
    Book.authors=authors
    Book.content=content
    db.session.commit()
    flash('Book edited successfully')
    return redirect(url_for('bookManagement'))

@app.route('/admin/book_management/delete/<int:id>')
@admin_required
def delete_book(id):
    User=user.query.get(session['user_id'])
    Book=book.query.get(id)
    if not Book:
        flash('Book does not exists!')
        return redirect(url_for('bookManagement'))
    return render_template('/admin_pages/deleteBook.html', active='Books', User=User, Book=Book)
@app.route('/admin/book_management/delete/<int:id>', methods=['post'])
@admin_required
def delete_book_post(id):
    Book=book.query.get(id)
    if not Book:
        flash('Book does not exists!')
        return redirect(url_for('bookManagement'))
    db.session.delete(Book)
    db.session.commit()
    flash('Book deleted successfully!')
    return redirect(url_for('bookManagement'))

# ADMIN MANAGING REQUESTS ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/admin/grant_book/<int:id>')
@admin_required
def grant_book(id):
    request=requests.query.get(id)
    if not request:
        flash('The request does not exist')
        return redirect(url_for('manageRequest'))
    request.status='approved'
    request.grant_date=datetime.now()
    db.session.commit()
    flash('Book permission granted successfully')
    return redirect(url_for('manageRequest'))
        
@app.route('/admin/reject_book/<int:id>')
@admin_required
def reject_book(id):
    request=requests.query.get(id)
    if not request:
        flash('The request does not exist')
        return redirect(url_for('manageRequest'))
    request.status='rejected'
    db.session.commit()
    flash('Book permission rejected successfully')
    return redirect(url_for('manageRequest'))

@app.route('/admin/revoke_book/<int:id>')
@admin_required
def revoke_book(id):
    request = requests.query.get(id)
    if not request:
        flash('The request does not exist')
        return redirect(url_for('borrowedBooksManagement'))
    
    request.status = 'returned'
    db.session.commit()
    flash('Book permission revoked successfully')
    return redirect(url_for('borrowedBooksManagement'))

@app.route('/admin/revoke_all_book')
@admin_required
def revoke_all_book():
    seven_days_ago = datetime.now() - timedelta(days=7)
    requests.query.filter(requests.grant_date < seven_days_ago).update({requests.status: 'returned'})
    db.session.commit()
    flash('All books granted more than 7 days ago have been revoked successfully')
    return redirect(url_for('borrowedBooksManagement'))
# END ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------


   






import os

from pony.orm import db_session, core, select
from hashlib import md5
from app import app, models, loggedin
from app.auth import login_required
from app.models import User, Thread, Message, File
from app.controllers import add_thread_to_user, get_user_threads
from flask import render_template, request, redirect, session, send_from_directory


@app.route('/api/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        return render_template('login.html')
    login = request.form.get('login')
    password = request.form.get('password')
    if login and password:
        with db_session:
            user = select(u for u in User if u.login == login and u.password == password)[:]
            if user:
                user = user[0]
                session['id'] = user.id
                session['login'] = user.login
                return redirect('/')
            else:
                return redirect('/login')
    else:
        return "All fields are required"


@app.route('/api/register', methods=['POST', 'GET'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    login = request.form.get('login')
    password = request.form.get('password')
    if login and password:
        try:
            with db_session:
                models.User(login=login, password=password)
            app.logger.info("New user %s" % login)
        except core.TransactionIntegrityError:
            return "Login already exists"
        return redirect('/login')
    return "All fields are required"


@login_required
@app.route('/api/me', methods=['POST', 'GET'])
def create_thread():
    if request.method == 'GET':
        return render_template('create.html')
    else:
        name = request.form.get('name')
        if not name:
            return "All fields are required"
        with db_session:
            thr = models.Thread(name=name)
        app.logger.info("New thread %s " % name)
        add_thread_to_user(session['login'], thr.id)
        return redirect('/list')


@login_required
@app.route('/api/users')
def list_threads():
    threads = get_user_threads(session['login'])
    if threads is None:
        return render_template('list.html', threads=None)
    else:
        with db_session:
            threads = Thread.select(lambda c: c.id in threads)[:]
            return render_template('list.html', threads=threads)

        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        with db_session:
            author = list(User.select(lambda u: u.id == session['id']))[0]
            File(filename=file.filename, user=author)
        return redirect('/')
    return render_template('upload.html')

@login_required
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

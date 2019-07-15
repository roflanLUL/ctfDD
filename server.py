import sqlite3
from flask import Flask, request, render_template, g, redirect, send_file
from base64 import b64encode, b64decode
from json import dumps, loads
from hashlib import md5
import os

app = Flask(__name__)

app.config['KEY'] = 'c00lkey'
app.config['DEBUGG'] = True
app.config['DATABASE'] = os.path.abspath(os.path.join(os.path.dirname(__file__), 'example.db'))



# DB Connection create
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.before_first_request
def init_tables():
    db = get_db()
    init_query = 'CREATE TABLE IF NOT EXISTS providers(id  integer NOT NULL PRIMARY KEY AUTOINCREMENT,login text,password text)'
    db.execute(init_query)
    init_query = 'CREATE TABLE IF NOT EXISTS blocked_resources(id  integer NOT NULL PRIMARY KEY AUTOINCREMENT,link text,provider_id integer,searchable bool)'
    db.execute(init_query)


# Decode cookie and get session dict
def session_decode(cookie_data):
    try:
        data = cookie_data.split('.')
        data = [b64decode(x) for x in data]
        json_str, hash_str = data[0], data[1]
        hash_key = request.args.get('debug_key', '') if app.config['DEBUGG'] else app.config['KEY']
        if md5(json_str + hash_key.encode()).hexdigest() == hash_str.decode():
            return loads(json_str.decode())
    except Exception as e:
        return None


# Encode session ang get cookie
def session_encode(data):
    json_str = dumps(data)
    json_str = json_str
    hash_key = request.args.get('debug_key', '') if app.config['DEBUGG'] else app.config['KEY']
    hash_string = md5((json_str + hash_key).encode()).hexdigest()
    return '.'.join([b64encode(json_str.encode()).decode(), b64encode(hash_string.encode()).decode()])


def check_exist(login):
    query = "SELECT * FROM providers WHERE login = '{}'".format(login)
    conn = get_db()
    db = conn.cursor()
    db.execute(query)
    result = db.fetchone()
    return result is not None


@app.route('api/register', methods=['POST'])
def reqister_page():
    login = request.form.get('login', '')
    password = request.form.get('password', '')
    if login == '' and password == '':
        return "Login and password are required"
    if check_exist(login):
        return "Login already exists"
    query = "INSERT INTO providers (login,password) VALUES ('{}','{}')".format(login, password)
    conn = get_db()
    db = conn.cursor()
    db.execute(query)
    conn.commit()
    return redirect('/login')


@app.route('/login', methods=['POST', 'GET'])
def login_page():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        login = request.form.get('login', '')
        password = request.form.get('password', '')
        if login == '' and password == '':
            return "Login and password are required"
        query = "SELECT * FROM providers where login = '{}' and password = '{}'".format(login, password)
        conn = get_db()
        db = conn.cursor()
        db.execute(query)
        result = db.fetchone()
        if result is None:
            return "User not found"
        data = {'id': result[0], 'login': result[1]}
        cookie_value = session_encode(data)
        response = redirect('/provider')
        response.set_cookie('session', cookie_value)
        return response


@app.route('/check/<pr_id>')
def check_resource(pr_id):
    link = request.args.get('link', '')
    if len(link) < 3:
        return render_template('blocked.html',blocked=None)

    query = "SELECT * FROM blocked_resources WHERE provider_id = {} and searchable = 1".format(pr_id)
    conn = get_db()
    db = conn.cursor()
    db.execute(query)
    results = db.fetchall()
    if results is None:
        return "Provider not found or he doesnt block any resource"
    resources = []
    #Try to find by prefix

    if '*' in link:
        prefix = link.split('*')[0]
        for result in results:
            if str(result[1]).startswith(prefix):
                resources.append(result[1])
    else:
        for result in results:
            if link == str(result[1]):
                resources.append(result[1])
    return render_template('blocked.html',blocked=resources)


@app.route('/list')
def provider_list():
    query = "SELECT * FROM providers "
    conn = get_db()
    db = conn.cursor()
    db.execute(query)
    results = db.fetchall()
    return render_template('list.html', providers=results)


@app.route('/add', methods=['POST'])
def add_resource():
    try:
        cookie = request.cookies.get('session', None)
        data = session_decode(cookie)
        provider_id = data.get('id', None)
        site_name = request.form.get('name', None)
        print(request.form)
        searchable = request.form.get('searchable',None)
        if searchable is None:
            searchable = False
        else:
            searchable = True
        print(searchable)
        if site_name is None:
            return "Bad site name"
        site_name = site_name.encode("ascii", 'ignore').decode()
        query = "INSERT INTO blocked_resources (link,provider_id,searchable) VALUES ('{}',{},{})".format(site_name, provider_id,int(searchable))
        conn = get_db()
        db = conn.cursor()
        db.execute(query)
        conn.commit()
        return redirect('/provider')
    except Exception as e:
        print(e)
        return "Bad session or data", 500


@app.route('/provider')
def provider_page():
    try:
        cookie = request.cookies.get('session', None)
        data = session_decode(cookie)
        provider_id = data.get('id', None)
        query = "SELECT * FROM blocked_resources WHERE provider_id = {}".format(provider_id)
        conn = get_db()
        db = conn.cursor()
        db.execute(query)
        results = db.fetchall()
        return render_template('provider.html', resources=results, name=data['login'])
    except Exception:
        return u"Простите, не получилось вас авторизовать. <a href='/'>&larr; На главную</a>", 500

@app.route('/file/<path:file>')
def rules(file):
    directory = os.path.join(os.path.dirname(__file__),'files')
    file_path = os.path.join(directory,file)
    return send_file(os.path.abspath(file_path))


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    conn = sqlite3.connect(app.config['DATABASE'])
    db = conn.cursor()
    init_query = 'CREATE TABLE IF NOT EXISTS providers(id  integer NOT NULL PRIMARY KEY AUTOINCREMENT,login text,password text)'
    db.execute(init_query)
    init_query = 'CREATE TABLE IF NOT EXISTS blocked_resources(id  integer NOT NULL PRIMARY KEY AUTOINCREMENT,link text,provider_id integer,searchable bool)'
    db.execute(init_query)
    app.run(port=5005, debug=False,host='0.0.0.0')

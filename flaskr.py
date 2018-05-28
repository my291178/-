import sqlite3
import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

from flask_uuid import FlaskUUID

import uuid

from flask_mail import Mail
from flask_mail import Message

app = Flask(__name__)
app.config.update(
    DEBUG=True,
    # EMAIL SETTINGS
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME='hhiconversion@gmail.com',
    MAIL_PASSWORD='HiConversion2018'
)
# здесь необходимо вставить smtp порт вашей почты, саму почту и пароль
mail = Mail(app)
flask_uuid = FlaskUUID()
flask_uuid.init_app(app)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    USERNAME='admin',
    PASSWORD='admin',
    EMAIL='admin',
    SECRET_KEY='DEVELOPMENT KEY FOR SESSIONS',
    HOME_URL='http://localhost:5000/'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    if not hasattr(g, app.config['DATABASE']):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, app.config['DATABASE']):
        g.sqlite_db.close()


@app.route('/authorized')
def show_entries():
    return render_template('show_entries.html')


@app.route('/<invite>', methods=['GET', 'POST'])
def register(invite):
    db = get_db()
    cur = db.execute('select * from users where invite=?', [invite])
    res = cur.fetchall()
    if len(res) > 0:

        if res[0]['status'] == 1:
            return "This link was used by another user"

        session['invite_link'] = invite

        return render_template('register.html')
    else:
        abort(404)


@app.route('/add-user', methods=['POST'])
def add_user():
    if len(request.form) > 0:

        db = get_db()
        cur = db.execute('select * from users where email=? and invite=?',
                         [request.form['email'], session.get("invite_link")])
        if len(cur.fetchall()) > 0:

            db = get_db()
            db.execute("update users set password=?, status=1 where email=?",
                       [request.form['password'], request.form['email']])
            db.commit()
            flash("Successfully registered!")
            return redirect("/")
        else:
            abort(400)


def send_email(recipients, body):
    msg = Message("You've been invited",
                  sender="from@example.com",
                  recipients=recipients)
    msg.body = body
    mail.send(msg)


@app.route('/invite', methods=['POST'])
def send_invite():
    if not session.get('logged_in'):
        abort(401)

    db = get_db()
    cur = db.execute('select * from users where email=?',
                     [request.form['email']])

    if len(cur.fetchall()) > 0:
        flash("User with this email is already registered")
        return redirect(url_for("show_entries"))

    while True:

        invite_uuid = uuid.uuid4()

        db = get_db()
        # берет из базы
        cur = db.execute("select * from users where invite=?", [str(invite_uuid)])

        if len(cur.fetchall()) == 0:
            break

    db = get_db()
    db.execute("insert into users (email, invite, status) values (? , ?, 0)", [request.form['email'], str(invite_uuid)])
    db.commit()
    flash('New invite was successfully posted')

    print(f"{app.config['HOME_URL']}{invite_uuid}")

    send_email([request.form['email']], f"{app.config['HOME_URL']}{invite_uuid}")

    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':

        if request.form['email'] == app.config['EMAIL'] and request.form['password'] == app.config['PASSWORD']:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))

        db = get_db()
        cur = db.execute('select * from users where email=?', [request.form['email']])
        res = cur.fetchall()

        if len(res) > 0:
            if res[0]['password'] != request.form['password']:
                error = 'Invalid password'
            else:
                session['logged_in'] = True
                flash('You were logged in')
                return redirect(url_for('show_entries'))
        else:
            error = 'Invalid email'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


if __name__ == '__main__':
    app.run()

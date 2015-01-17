import os, sqlite3
from flask import Flask, url_for, render_template, request, redirect, session, abort, flash, g
from flask.ext import login
from flask.ext.login import LoginManager, login_user
from flask.ext.security import login_required
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.wtf import Form
from wtforms.fields import TextField, PasswordField
from wtforms.validators import *

app = Flask(__name__)
app.config.from_object(__name__)

# App settings
app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'pantry.db'),
    DEBUG=True,
    SECRET_KEY='pantry key',
))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE']

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    real_name = db.Column(db.String(80), unique=True)
    address = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    items_available = db.Column(db.String(1000))
    items_desired = db.Column(db.String(1000))
    points = db.Column(db.Integer)
    num_given = db.Column(db.Integer)
    num_bought = db.Column(db.Integer)
    created_at = db.Column(db.TIMESTAMP)

    def __init__(self, username, password, real_name, address, email):
        self.username = username
        self.password = password
        self.real_name = real_name
        self.address = address
        self.email = email

    def check_password(self, other_pass):
        return self.password == other_pass

    def is_authenticated(self):
        return session['user_id'] == self.id

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return '<User {} {} {} {}' \
                .format(self.username, self.real_name, self.address, self.email)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_from = db.Column(db.String(80))
    name_to = db.Column(db.String(80))
    item = db.Column(db.String(80))
    price = db.Column(db.Float)
    created_at = db.Column(db.TIMESTAMP)

    def __init__(self, name_from, name_to, item, price):
        self.name_from = name_from
        self.name_to = name_to
        self.item = item
        self.price = price

    def __repr__(self):
        return 'Transaction {} {} {} {}' \
               .format(self.name_from, self.name_to, self.item, self.price)

class LoginForm(Form):
    username = TextField(validators=[required()])
    password = PasswordField(validators=[required()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self):
        # rv = Form.validate(self)
        # if not rv:
        #     return False

        user = User.query.filter_by(username=self.username.data).first()

        if user is None:
            self.username.errors.append('Unknown username')

        if not user.check_password(self.password.data):
            self.username.errors.append('Invalid password')
            return False

        self.user = user
        return True

    def get_user(self):
        return db.session.query(User).filter_by(username=self.username.data).first()

@app.route("/")
def pantry():
    return render_template('home.html')

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route("/examples")
def examples():
    return render_template('examples.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = form.get_user()
        login_user(user)
        flash("Logged in!", 'success')
        session['user_id'] = form.user.id
        return redirect(request.args.get("next") or url_for('dashboard'))
    flash("No! Wrong Password! Fuck!", 'error')
    return render_template("home.html", form=form)

@app.route("/register")
def register():
    return render_template('register.html')

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)

if __name__ == "__main__":
    app.run()

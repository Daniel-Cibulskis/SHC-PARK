from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta, datetime
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carpark.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=30)

# 4. Add these imports and config after your Flask app setup
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'danielcibulskis102@gmail.com'  # <-- Set backend email here
app.config['MAIL_PASSWORD'] = 'cfmsyntoysygwrko'  # <-- Use the app password for this account
mail = Mail(app)

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    plate = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(150), nullable=False, unique=True)  # <-- Add this line

@app.route('/')
def home():
    taken_slots = User.query.filter(User.plate.isnot(None)).count()
    vacant_slots = 90 - taken_slots
    username = session.get('user')
    return render_template('index.html', taken=taken_slots, vacant=vacant_slots, username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user'] = user.username
            return redirect(url_for('dashboard'))
        flash('Invalid login')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(
            username=request.form['username'],
            password=hashed_pw,
            email=request.form['email']
        )
        db.session.add(new_user)
        db.session.commit()
        # Send email notification
        msg = Message(
            subject="Carpark Registration",
            sender=app.config['MAIL_USERNAME'],
            recipients=[new_user.email],
            body=f"login user\n{new_user.username} has entered the carpark at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
        )
        mail.send(msg)
        # Log the user in immediately after registration
        session['user'] = new_user.username
        flash('Registered and logged in!')
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['user']).first()
    if request.method == 'POST':
        if 'plate' in request.form and request.form['plate']:
            if User.query.filter(User.plate.isnot(None)).count() < 90:
                user.plate = request.form['plate']
                db.session.commit()
                flash('Plate added.')
            else:
                flash('Full.')
        elif 'remove' in request.form:
            user.plate = None
            db.session.commit()
            # Send exit email
            msg = Message(
                subject="Carpark Update",
                sender=app.config['MAIL_USERNAME'],
                recipients=[user.email],
                body=f"{user.username}, You have left the carpark at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Drive safely :)."
            )
            mail.send(msg)
            flash('Plate removed.')
    taken_slots = User.query.filter(User.plate.isnot(None)).count()
    vacant_slots = 90 - taken_slots
    return render_template('dashboard.html', user=user, taken=taken_slots, vacant=vacant_slots)

@app.route('/admin')
def admin():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out')
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)



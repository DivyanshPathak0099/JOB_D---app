from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jod_d.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    pincode = db.Column(db.String(10))

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    salary = db.Column(db.String(50), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    poster_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class AcceptedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    accepter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    poster_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accepter_name = db.Column(db.String(100))
    accepter_address = db.Column(db.String(200))
    accepter_city = db.Column(db.String(50))
    accepter_pincode = db.Column(db.String(10))

# Create database if not exists
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_base = request.form['username']
        number = request.form['number']
        password = request.form['password']
        # Combine username and number with @
        username = f"{username_base}@{number}"
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            if user.name:  # If user has details, go to home
                return redirect(url_for('home'))
            else:  # If no details, go to details
                return redirect(url_for('details'))
        else:
            flash('Invalid username or password. If new, try signing up with these credentials.')
            # Check if username@number already exists
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                hashed_pw = generate_password_hash(password)
                new_user = User(username=username, password=hashed_pw)
                db.session.add(new_user)
                db.session.commit()
                session['user_id'] = new_user.id
                return redirect(url_for('details'))
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/details', methods=['GET', 'POST'])
def details():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.name:  # If user already has details, redirect to home
        return redirect(url_for('home'))
    if request.method == 'POST':
        user.name = request.form['name']
        user.address = request.form['address']
        user.city = request.form['city']
        user.pincode = request.form['pincode']
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('details.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    total_users = User.query.count()  # Get total number of users
    total_jobs = Job.query.count()  # Get total number of jobs
    jobs = Job.query.all()  # All jobs
    # Debug: Log the number of jobs fetched
    print(f"DEBUG: Fetched {len(jobs)} jobs for home page")
    return render_template('home.html', user=user, total_users=total_users, total_jobs=total_jobs, jobs=jobs)

@app.route('/search', methods=['POST'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    pincode = request.form.get('pincode')
    jobs = Job.query.filter_by(pincode=pincode).all() if pincode else []
    return render_template('search.html', jobs=jobs, pincode=pincode)

@app.route('/provide', methods=['GET', 'POST'])
def provide():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        company_name = request.form['company_name']
        address = request.form['address']
        pincode = request.form['pincode']
        salary = request.form['salary']
        job_type = request.form['job_type']
        phone = request.form['phone']
        new_job = Job(company_name=company_name, address=address, pincode=pincode,
                      salary=salary, job_type=job_type, phone=phone,
                      poster_id=session['user_id'])
        db.session.add(new_job)
        db.session.commit()
        # Debug: Confirm job was added
        print(f"DEBUG: Added job {company_name} by user {session['user_id']}")
        return redirect(url_for('home'))
    return render_template('provide.html')

@app.route('/accept/<int:job_id>')
def accept(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    job = Job.query.get(job_id)
    if not user.name:
        flash('Please complete your details before accepting a job.')
        return redirect(url_for('details'))
    if job:
        accepted_job = AcceptedJob(
            job_id=job_id,
            accepter_id=user.id,
            poster_id=job.poster_id,
            accepter_name=user.name,
            accepter_address=user.address,
            accepter_city=user.city,
            accepter_pincode=user.pincode
        )
        db.session.add(accepted_job)
        db.session.commit()
        flash('Job accepted! Your details have been sent to the job poster\'s inbox.')
    else:
        flash('Job not found.')
    return redirect(url_for('home'))

@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    accepted_jobs = AcceptedJob.query.filter_by(poster_id=user.id).all()
    return render_template('inbox.html', accepted_jobs=accepted_jobs)

if __name__ == '__main__':
    app.run(debug=True)
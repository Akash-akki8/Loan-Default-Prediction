from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from functools import wraps
from datetime import datetime
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
try:
    client = MongoClient(mongo_uri)
    db = client['loan_default_prediction']
    users_collection = db['users']
    loan_details_collection = db['loan_details']
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    users_collection = None
    loan_details_collection = None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash('Please log in first.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        gender = request.form.get('gender')
        dob = request.form.get('dob')
        phone = request.form.get('phone')

        if not all([name, email, password, confirm_password, gender, dob, phone]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('sign_up'))

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('sign_up'))

        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash('A user already exists with this email.', 'danger')
            return redirect(url_for('sign_up'))

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users_collection.insert_one({
            'name': name,
            'email': email,
            'password': hashed_password,
            'gender': gender,
            'dob': dob,
            'phone': phone,
            'created_at': datetime.utcnow()
        })

        flash('Registration successful! You can now sign in.', 'success')
        return redirect(url_for('index'))

    return render_template('sign_up.html')


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'GET':
        return redirect(url_for('index'))

    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        flash('Please enter both email and password.', 'danger')
        return redirect(url_for('index'))

    user = users_collection.find_one({'email': email})
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        session['email'] = user['email']
        session['name'] = user.get('name', '')
        flash('Signed in successfully.', 'success')
        return redirect(url_for('details'))

    flash('Invalid email or password. Please try again.', 'danger')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/details', methods=['GET', 'POST'])
@login_required
def details():
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        pan_card_number = request.form.get('pan_card_number')
        credit_score = request.form.get('credit_score')

        if not all([user_name, pan_card_number, credit_score]):
            flash('Please complete all fields in the application form.', 'danger')
            return redirect(url_for('details'))

        try:
            credit_score = int(credit_score)
        except ValueError:
            flash('Credit score must be a valid number.', 'danger')
            return redirect(url_for('details'))

        if credit_score < 300 or credit_score > 850:
            flash('Credit score must be between 300 and 850.', 'danger')
            return redirect(url_for('details'))

        loan_details_collection.insert_one({
            'user_name': user_name,
            'pan_card_number': pan_card_number,
            'credit_score': credit_score,
            'submitted_at': datetime.utcnow(),
            'user_email': session['email']
        })

        flash('Loan application submitted successfully!', 'success')
        return redirect(url_for('details'))

    user = users_collection.find_one({'email': session['email']})
    return render_template('details.html', user=user)


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('forgot_password'))

        user = users_collection.find_one({'email': email})
        if user:
            flash('Password reset instructions have been sent to your email.', 'info')
        else:
            flash('No account found with that email address.', 'danger')

        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

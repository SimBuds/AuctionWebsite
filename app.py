import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Auction, Bid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['SECRET_KEY'] = 'auctionMeow'
db.init_app(app)

loginManager = LoginManager()
loginManager.init_app(app)
loginManager.login_view = 'login'

@loginManager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))

        flash('Invalid username or password.')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('The username already exists. Please choose a different one.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password, email=email, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/profile')
@login_required
def user_profile():
    return render_template('profile.html', user=current_user)

@app.route('/auctions')
def auctions():
    active_auctions = Auction.query.filter(Auction.expiryDate > datetime.datetime.utcnow()).all()
    return render_template('auctions.html', auctions=active_auctions)

@app.route('/create_auction', methods=['GET', 'POST'])
@login_required
def create_auction():
    if request.method == 'POST':
        image = request.form['image']
        start_price = request.form['start_price']
        reserve_price = request.form['reserve_price']
        name = request.form['name']
        description = request.form['description']
        expiry_date = request.form['expiry_date']

        # Convert input to correct data types
        start_price = float(start_price)
        reserve_price = float(reserve_price)
        expiry_date = datetime.datetime.strptime(expiry_date, '%Y-%m-%d')

        auction = Auction(image=image, startPrice=start_price, reservePrice=reserve_price, name=name,
                          description=description, expiryDate=expiry_date, userId=current_user.id)
        db.session.add(auction)
        db.session.commit()

        flash('Auction created successfully!')
        return redirect(url_for('index'))

    return render_template('create_auction.html')

if __name__ == '__main__':
    app.run(debug=True)
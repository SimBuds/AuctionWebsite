import datetime, atexit
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, User, Auction, Bid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['SECRET_KEY'] = 'auctionMeow'
db.init_app(app)

# Create database
@app.before_first_request
def create_tables():
    db.create_all()

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

@app.route('/create-auction', methods=['GET', 'POST'])
@login_required
def create_auction():
    if request.method == 'POST':
        # Get form data and validate
        image = request.form['image']
        start_price = float(request.form['start_price'])
        reserve_price = float(request.form['reserve_price'])
        name = request.form['name']
        description = request.form['description']
        expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d')  # Assuming expiry_date is in 'YYYY-MM-DD' format

        # Create new auction and save to the database
        auction = Auction(image=image, start_price=start_price, reserve_price=reserve_price, name=name, description=description, expiry_date=expiry_date, userId=current_user.id)
        db.session.add(auction)
        db.session.commit()

        flash('Auction created successfully.')
        return redirect(url_for('my_auctions'))

    return render_template('auction_form.html')

@app.route('/edit-auction/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def edit_auction(auction_id):
    auction = Auction.query.get(auction_id)
    
    if auction.userId != current_user.id:
        flash("You don't have permission to edit this auction.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Get form data and validate
        auction.image = request.form['image']
        auction.start_price = float(request.form['start_price'])
        auction.reserve_price = float(request.form['reserve_price'])
        auction.name = request.form['name']
        auction.description = request.form['description']
        auction.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d')

        # Save changes to the database
        db.session.commit()

        flash('Auction updated successfully.')
        return redirect(url_for('my_auctions'))

    return render_template('auction_form.html', auction=auction, action="Edit")

@app.route('/delete-auction/<int:auction_id>', methods=['POST'])
@login_required
def delete_auction(auction_id):
    auction = Auction.query.get_or_404(auction_id)

    # Ensure the current user is the owner of the auction or an admin
    if current_user.id != auction.userId and current_user.role != 'admin':
        flash('You do not have permission to delete this auction.')
        return redirect(url_for('index'))

    # Delete associated bids
    Bid.query.filter_by(auctionId=auction_id).delete()

    # Delete the auction
    db.session.delete(auction)
    db.session.commit()

    flash('Auction deleted successfully.')
    return redirect(url_for('my_auctions'))

@app.route('/auction/<int:auction_id>', methods=['GET', 'POST'])
@login_required
def auction_detail(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    # Get the current highest bid for the auction
    highest_bid = Bid.query.filter_by(auctionId=auction_id).order_by(Bid.amount.desc()).first()

    if request.method == 'POST':
        # Fetch the user's bid amount from the form
        new_bid_amount = float(request.form['bid_amount'])

        # Check if the new bid amount is valid and higher than the current highest bid
        if highest_bid is None or new_bid_amount > highest_bid.amount:
            # Update the existing user's bid or create a new bid
            user_bid = Bid.query.filter_by(auctionId=auction_id, userId=current_user.id).first()
            if user_bid:
                user_bid.amount = new_bid_amount
                user_bid.result = "pending"
            else:
                user_bid = Bid(amount=new_bid_amount, userId=current_user.id, auctionId=auction_id, result="pending")
                db.session.add(user_bid)

            # Save the updated bid to the database
            db.session.commit()

            # Update all other bids' results to "losing"
            losing_bids = Bid.query.filter(Bid.auctionId == auction_id, Bid.id != user_bid.id)
            for bid in losing_bids:
                bid.result = "losing"
            db.session.commit()

            flash('Your bid has been successfully placed.')
        else:
            flash('Your bid must be higher than the current highest bid.')

    # Fetch the updated highest bid for the auction
    highest_bid = Bid.query.filter_by(auctionId=auction_id).order_by(Bid.amount.desc()).first()

    return render_template('auction_detail.html', auction=auction, highest_bid=highest_bid)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Update user information
        current_user.username = request.form['username']
        current_user.email = request.form['email']
        db.session.commit()
        flash('Profile updated successfully.')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html')

@app.route('/my-auctions')
@login_required
def my_auctions():
    user_id = current_user.id
    auctions = Auction.query.filter_by(userId=user_id).all()
    return render_template('my_auctions.html', auctions=auctions)

@app.route('/my-bids')
@login_required
def my_bids():
    user_bids = Bid.query.filter_by(userId=current_user.id).all()
    return render_template('my_bids.html', bids=user_bids)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('index'))

    users = User.query.all()
    auctions = Auction.query.all()
    return render_template('admin_dashboard.html', users=users, auctions=auctions)


def check_expired_auctions():
    expired_auctions = Auction.query.filter(Auction.expiryDate < datetime.now()).all()
    for auction in expired_auctions:
        bids = Bid.query.filter(Bid.auctionId == auction.id).order_by(Bid.amount.desc()).all()
        if bids and bids[0].amount >= auction.reservePrice:
            winning_bid = bids[0]
            winning_bid.result = 'winning'
            db.session.commit()
        else:
            for bid in bids:
                bid.result = 'losing'
            db.session.commit()

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_expired_auctions, trigger="interval", minutes=2.5)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(debug=True)
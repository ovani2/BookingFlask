from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, User, Product, Review
from hotels import generate_hotels

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///booking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super-secret-key-123'

db.init_app(app)

with app.app_context():
    db.create_all()
    generate_hotels()


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    products = db.session.execute(db.select(Product)).scalars().all()
    
    my_bookings = db.session.execute(
        db.select(Product).filter_by(booked_by=session['user_id'], is_booked=True)
    ).scalars().all()
    
    my_reviews = db.session.execute(
        db.select(Review).filter_by(user_id=session['user_id']).order_by(Review.created_at.desc())
    ).scalars().all()
    
    return render_template(
        'index.html', 
        products=products, 
        my_bookings=my_bookings, 
        my_reviews=my_reviews,
        username=session.get('username')
    )


@app.route('/room/<int:product_id>')
def room_detail(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    product = db.session.execute(db.select(Product).filter_by(id=product_id)).scalar_one_or_none()
    if not product:
        flash("Номер не знайдено!")
        return redirect(url_for('index'))
        
    days = request.args.get('days', 1, type=int)
    if days < 1: days = 1
    if days > 7: days = 7
    
    total_price = product.price * days
    
    reviews = db.session.execute(
        db.select(Review).filter_by(product_id=product_id).order_by(Review.created_at.desc())
    ).scalars().all()
    
    return render_template('room.html', product=product, days=days, total_price=total_price, reviews=reviews)


@app.route('/book/<int:product_id>', methods=['POST'])
def book_hotel(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    days = int(request.form.get('booking_days', 1))
    if days < 1 or days > 7:
        flash("Можна забронювати лише від 1 до 7 днів!")
        return redirect(url_for('index'))
        
    product = db.session.execute(db.select(Product).filter_by(id=product_id)).scalar_one_or_none()
    
    if product and not product.is_booked:
        product.is_booked = True
        product.booked_by = session['user_id']
        product.booking_days = days
        db.session.commit()
        flash(f"Номер '{product.name}' успішно заброньовано!")
    else:
        flash("Цей номер уже заброньовано!")
        
    return redirect(url_for('index'))


@app.route('/cancel_booking/<int:product_id>', methods=['POST'])
def cancel_booking(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    product = db.session.execute(db.select(Product).filter_by(id=product_id, booked_by=session['user_id'])).scalar_one_or_none()
    
    if product:
        product.is_booked = False
        product.booked_by = None
        product.booking_days = 0
        db.session.commit()
        flash(f"Бронювання скасовано.")
        
    return redirect(url_for('index'))


@app.route('/add_review/<int:product_id>', methods=['POST'])
def add_review(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    text = request.form.get('review_text')
    if text and text.strip() != "":
        new_review = Review(
            product_id=product_id,
            user_id=session['user_id'],
            username=session['username'],
            text=text.strip()
        )
        db.session.add(new_review)
        db.session.commit()
        flash("Відгук успішно додано!")
        
    return redirect(url_for('room_detail', product_id=product_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none():
            flash('Користувач існує!')
            return redirect(url_for('register'))
        db.session.add(User(username=username, password=generate_password_hash(password)))
        db.session.commit()
        flash('Успішно!')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        flash('Помилка входу!')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
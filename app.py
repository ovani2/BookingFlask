from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, User, Product, Review
from hotels import generate_hotels
import datetime

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

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()
    balance = user.balance if user else 0.0

    return render_template(
        'index.html',
        products=products,
        my_bookings=my_bookings,
        my_reviews=my_reviews,
        username=session.get('username'),
        balance=balance
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
    
    if days == 1:
        total_price = product.price
    
    if days == 2:
        total_price = product.price * 1.9
    
    if days == 3:
        total_price = product.price * 1.8
    
    if days == 4:
        total_price = product.price * 1.7
    
    if days == 5:
        total_price = product.price * 1.6
    
    if days == 6:
        total_price = product.price * 1.5
    
    if days == 7:
        total_price = product.price * 1.4
    
    if days > 7:
        total_price = product.price * 1.4 * days
    
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
    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if not product or not user:
        flash("Помилка бронювання!")
        return redirect(url_for('index'))

    # Розрахунок ціни
    if days == 1:
        total_price = product.price
    elif days == 2:
        total_price = product.price * 1.9
    elif days == 3:
        total_price = product.price * 2.7
    elif days == 4:
        total_price = product.price * 3.4
    elif days == 5:
        total_price = product.price * 4.0
    elif days == 6:
        total_price = product.price * 4.5
    elif days == 7:
        total_price = product.price * 4.9
    else:
        total_price = product.price * days

    # Перевірка балансу
    if user.balance < total_price:
        flash(f"Недостатньо коштів! Потрібно {total_price:.2f} грн, а у вас {user.balance:.2f} грн")
        return redirect(url_for('room_detail', product_id=product_id))

    if product and not product.is_booked:
        product.is_booked = True
        product.booked_by = session['user_id']
        product.booking_days = days
        user.balance -= total_price
        db.session.commit()
        flash(f"Номер '{product.name}' успішно заброньовано! Списано {total_price:.2f} грн")
    else:
        flash("Цей номер уже заброньовано!")

    return redirect(url_for('index'))


@app.route('/cancel_booking/<int:product_id>', methods=['POST'])
def cancel_booking(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product = db.session.execute(db.select(Product).filter_by(id=product_id, booked_by=session['user_id'])).scalar_one_or_none()
    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if product and user:
        # Розрахунок ціни для повернення
        days = product.booking_days
        if days == 1:
            refund = product.price
        elif days == 2:
            refund = product.price * 1.9
        elif days == 3:
            refund = product.price * 2.7
        elif days == 4:
            refund = product.price * 3.4
        elif days == 5:
            refund = product.price * 4.0
        elif days == 6:
            refund = product.price * 4.5
        elif days == 7:
            refund = product.price * 4.9
        else:
            refund = product.price * days

        product.is_booked = False
        product.booked_by = None
        product.booking_days = 0
        user.balance += refund
        db.session.commit()
        flash(f"Бронювання скасовано. Повернено {refund:.2f} грн")

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


@app.route('/add_balance', methods=['POST'])
def add_balance():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    amount = request.form.get('amount', type=float)
    print(f"DEBUG: Received amount: {amount}")

    if amount and amount > 0 and amount <= 10000:
        user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()
        if user:
            old_balance = user.balance
            user.balance += amount
            db.session.commit()
            print(f"DEBUG: Balance updated from {old_balance} to {user.balance}")
            flash(f"Баланс поповнено на {amount:.2f} грн")
        else:
            print("DEBUG: User not found")
            flash("Помилка: користувача не знайдено")
    else:
        print(f"DEBUG: Invalid amount: {amount}")
        flash("Невірна сума! Введіть від 1 до 10000 грн")

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
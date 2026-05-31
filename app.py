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


def calculate_price(base_price, days):
    """Розраховує ціну бронювання з урахуванням сезону та дня тижня"""
    now = datetime.datetime.now()
    month = now.month
    weekday = now.weekday()


    total = base_price * days


    if month in [12, 1, 2, 6, 7, 8]:
        seasonal_multiplier = 1.4

    elif month in [3, 4, 5, 9, 10, 11]:
        seasonal_multiplier = 1.0
    else:
        seasonal_multiplier = 1.0

    if weekday in [5, 6]:
        weekend_multiplier = 1.3
    else:
        weekend_multiplier = 1.0


    if days >= 7:
        duration_discount = 0.85
    elif days >= 5:
        duration_discount = 0.90
    elif days >= 3:
        duration_discount = 0.95
    else:
        duration_discount = 1.0


    final_price = total * seasonal_multiplier * weekend_multiplier * duration_discount

    return round(final_price, 2)


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
    if days < 1:
        days = 1
    if days > 7:
        days = 7

    total_price = calculate_price(product.price, days)

    raw_reviews = db.session.execute(
        db.select(Review).filter_by(product_id=product_id).order_by(Review.created_at.desc())
    ).scalars().all()

    reviews = []
    total_rating = 0
    rating_count = 0

    for r in raw_reviews:
        review_text = r.text
        review_rating = 5
        if review_text.startswith("[RATING:"):
            try:
                parts = review_text.split("] ", 1)
                review_rating = int(parts[0].replace("[RATING:", ""))
                review_text = parts[1]
            except:
                pass
        
        total_rating += review_rating
        rating_count += 1
        
        reviews.append({
            "username": r.username,
            "text": review_text,
            "rating": review_rating,
            "created_at": r.created_at
        })

    avg_rating = round(total_rating / rating_count, 1) if rating_count > 0 else 0.0

    return render_template(
        'room.html', 
        product=product, 
        days=days, 
        total_price=total_price, 
        reviews=reviews, 
        avg_rating=avg_rating,
        rating_count=rating_count
    )


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

    total_price = calculate_price(product.price, days)

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


@app.route('/confirm_cancel/<int:product_id>')
def confirm_cancel(product_id):
    """Сторінка підтвердження скасування бронювання"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Знаходимо бронювання користувача
    product = db.session.execute(
        db.select(Product).filter_by(id=product_id, booked_by=session['user_id'], is_booked=True)
    ).scalar_one_or_none()

    # Якщо бронювання не знайдено або воно не належить користувачу
    if not product:
        flash("Бронювання не знайдено або воно вам не належить!")
        return redirect(url_for('index'))

    # Розраховуємо суму повернення
    refund_amount = calculate_price(product.price, product.booking_days)

    # Показуємо сторінку підтвердження з усією інформацією
    return render_template(
        'confirm_cancel.html',
        product=product,
        refund_amount=refund_amount
    )


@app.route('/cancel_booking/<int:product_id>', methods=['POST'])
def cancel_booking(product_id):
    """Реальне скасування бронювання (POST-запит)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product = db.session.execute(db.select(Product).filter_by(id=product_id, booked_by=session['user_id'])).scalar_one_or_none()
    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if product and user:
        # Використовуємо нашу функцію для розрахунку повернення
        refund = calculate_price(product.price, product.booking_days)

        # Скасовуємо бронювання
        product.is_booked = False
        product.booked_by = None
        product.booking_days = 0

        # Повертаємо гроші на баланс
        user.balance += refund
        db.session.commit()

        flash(f"Бронювання скасовано. Повернено {refund:.2f} грн")

    return redirect(url_for('index'))


@app.route('/add_review/<int:product_id>', methods=['POST'])
def add_review(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    text = request.form.get('review_text')
    rating = request.form.get('review_rating', '5')
    
    if text and text.strip() != "":
        full_text = f"[RATING:{rating}] {text.strip()}"
        new_review = Review(
            product_id=product_id,
            user_id=session['user_id'],
            username=session['username'],
            text=full_text
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

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, User, Product, Review, Booking
from hotels import generate_hotels
import datetime
from datetime import date, timedelta

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


def is_room_available(product_id, check_in, check_out):
    """Перевіряє чи доступний номер в заданий період"""
    overlapping_bookings = db.session.execute(
        db.select(Booking).filter(
            Booking.product_id == product_id,
            Booking.status == 'active',
            Booking.check_in < check_out,
            Booking.check_out > check_in
        )
    ).scalars().all()

    return len(overlapping_bookings) == 0


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    available_only = request.args.get('available_only', 'false') == 'true'

    query = db.select(Product)

    if search_query:
        query = query.filter(Product.name.ilike(f'%{search_query}%'))

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if available_only:
        query = query.filter(Product.is_booked == False)

    products = db.session.execute(query).scalars().all()

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
        balance=balance,
        search_query=search_query,
        min_price=min_price,
        max_price=max_price,
        available_only=available_only
    )


@app.route('/room/<int:product_id>')
def room_detail(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product = db.session.execute(db.select(Product).filter_by(id=product_id)).scalar_one_or_none()
    if not product:
        flash("Номер не знайдено!")
        return redirect(url_for('index'))

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
        reviews=reviews,
        avg_rating=avg_rating,
        rating_count=rating_count,
        today=date.today().isoformat()
    )


@app.route('/book/<int:product_id>', methods=['POST'])
def book_hotel(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    check_in_str = request.form.get('check_in')
    check_out_str = request.form.get('check_out')

    if not check_in_str or not check_out_str:
        flash("Будь ласка, виберіть дати заїзду та виїзду!")
        return redirect(url_for('room_detail', product_id=product_id))

    try:
        check_in = datetime.datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Невірний формат дати!")
        return redirect(url_for('room_detail', product_id=product_id))

    if check_in < date.today():
        flash("Дата заїзду не може бути в минулому!")
        return redirect(url_for('room_detail', product_id=product_id))

    if check_out <= check_in:
        flash("Дата виїзду повинна бути пізніше дати заїзду!")
        return redirect(url_for('room_detail', product_id=product_id))

    days = (check_out - check_in).days

    if days > 30:
        flash("Максимальний термін бронювання - 30 днів!")
        return redirect(url_for('room_detail', product_id=product_id))

    product = db.session.execute(db.select(Product).filter_by(id=product_id)).scalar_one_or_none()
    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if not product or not user:
        flash("Помилка бронювання!")
        return redirect(url_for('index'))

    if not is_room_available(product_id, check_in, check_out):
        flash("Номер вже заброньовано на ці дати!")
        return redirect(url_for('room_detail', product_id=product_id))

    total_price = calculate_price(product.price, days)

    if user.balance < total_price:
        flash(f"Недостатньо коштів! Потрібно {total_price:.2f} грн, а у вас {user.balance:.2f} грн")
        return redirect(url_for('room_detail', product_id=product_id))

    new_booking = Booking(
        user_id=session['user_id'],
        product_id=product_id,
        check_in=check_in,
        check_out=check_out,
        total_price=total_price,
        status='active'
    )

    user.balance -= total_price
    db.session.add(new_booking)
    db.session.commit()

    flash(f"Номер '{product.name}' успішно заброньовано з {check_in} по {check_out}! Списано {total_price:.2f} грн")
    return redirect(url_for('booking_history'))


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


@app.route('/cancel_booking_new/<int:booking_id>', methods=['POST'])
def cancel_booking_new(booking_id):
    """Скасування бронювання з нової системи"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    booking = db.session.execute(
        db.select(Booking).filter_by(id=booking_id, user_id=session['user_id'], status='active')
    ).scalar_one_or_none()

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if booking and user:
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.datetime.utcnow()

        user.balance += booking.total_price
        db.session.commit()

        flash(f"Бронювання скасовано. Повернено {booking.total_price:.2f} грн")
    else:
        flash("Бронювання не знайдено або вже скасоване!")

    return redirect(url_for('booking_history'))


@app.route('/booking_history')
def booking_history():
    """Сторінка з історією всіх бронювань користувача"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    bookings = db.session.execute(
        db.select(Booking).filter_by(user_id=session['user_id']).order_by(Booking.created_at.desc())
    ).scalars().all()

    bookings_with_products = []
    for booking in bookings:
        product = db.session.execute(db.select(Product).filter_by(id=booking.product_id)).scalar_one_or_none()
        if product:
            bookings_with_products.append({
                'booking': booking,
                'product': product,
                'days': (booking.check_out - booking.check_in).days
            })

    return render_template('booking_history.html', bookings=bookings_with_products)


@app.route('/profile')
def profile():
    """Сторінка профілю користувача"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if not user:
        flash("Користувача не знайдено!")
        return redirect(url_for('login'))

    active_bookings = db.session.execute(
        db.select(Booking).filter_by(user_id=session['user_id'], status='active').order_by(Booking.check_in)
    ).scalars().all()

    past_bookings = db.session.execute(
        db.select(Booking).filter(
            Booking.user_id == session['user_id'],
            (Booking.status == 'cancelled') | (Booking.check_out < date.today())
        ).order_by(Booking.created_at.desc()).limit(10)
    ).scalars().all()

    total_spent = db.session.execute(
        db.select(db.func.sum(Booking.total_price)).filter_by(user_id=session['user_id'], status='active')
    ).scalar() or 0.0

    return render_template(
        'profile.html',
        user=user,
        active_bookings=active_bookings,
        past_bookings=past_bookings,
        total_spent=total_spent
    )


@app.route('/update_profile', methods=['POST'])
def update_profile():
    """Оновлення профілю користувача"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if user:
        user.email = request.form.get('email', '').strip()
        user.phone = request.form.get('phone', '').strip()
        avatar_url = request.form.get('avatar_url', '').strip()

        if avatar_url:
            user.avatar_url = avatar_url

        db.session.commit()
        flash("Профіль успішно оновлено!")

    return redirect(url_for('profile'))


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
    app.run(debug=True, port=5001)

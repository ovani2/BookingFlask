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

    admin = db.session.execute(db.select(User).filter_by(username='admin')).scalar_one_or_none()
    if not admin:
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin'),
            balance=0.0,
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Адмін-акаунт створено: username='admin', password='admin'")


def calculate_price(base_price, days):
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

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()
    balance = user.balance if user else 0.0
    is_admin = user.is_admin if user else False

    return render_template(
        'index.html',
        products=products,
        my_bookings=my_bookings,
        username=session.get('username'),
        balance=balance,
        is_admin=is_admin,
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
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product = db.session.execute(
        db.select(Product).filter_by(id=product_id, booked_by=session['user_id'], is_booked=True)
    ).scalar_one_or_none()

    if not product:
        flash("Бронювання не знайдено або воно вам не належить!")
        return redirect(url_for('index'))

    refund_amount = calculate_price(product.price, product.booking_days)

    return render_template(
        'confirm_cancel.html',
        product=product,
        refund_amount=refund_amount
    )


@app.route('/cancel_booking/<int:product_id>', methods=['POST'])
def cancel_booking(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product = db.session.execute(db.select(Product).filter_by(id=product_id, booked_by=session['user_id'])).scalar_one_or_none()
    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if product and user:
        refund = calculate_price(product.price, product.booking_days)

        product.is_booked = False
        product.booked_by = None
        product.booking_days = 0

        user.balance += refund
        db.session.commit()

        flash(f"Бронювання скасовано. Повернено {refund:.2f} грн")

    return redirect(url_for('index'))


@app.route('/cancel_booking_new/<int:booking_id>', methods=['POST'])
def cancel_booking_new(booking_id):
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


@app.route('/admin')
def admin_panel():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()
    if not user or not user.is_admin:
        flash("Доступ заборонено! Тільки для адміністраторів.")
        return redirect(url_for('index'))

    products = db.session.execute(db.select(Product).order_by(Product.id)).scalars().all()

    return render_template('admin.html', products=products, username=session.get('username'))


@app.route('/admin/add_hotel', methods=['POST'])
def admin_add_hotel():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()
    if not user or not user.is_admin:
        flash("Доступ заборонено!")
        return redirect(url_for('index'))

    name = request.form.get('name', '').strip()
    price = request.form.get('price', type=float)
    description = request.form.get('description', '').strip()
    image_url = request.form.get('image_url', '').strip()

    if not name or not price or price <= 0:
        flash("Назва та ціна обов'язкові!")
        return redirect(url_for('admin_panel'))

    new_product = Product(
        name=name,
        price=price,
        description=description or "Опис готелю",
        image_url=image_url or "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=500"
    )

    db.session.add(new_product)
    db.session.commit()

    flash(f"Готель '{name}' успішно додано!")
    return redirect(url_for('admin_panel'))


@app.route('/admin/edit_hotel/<int:product_id>', methods=['POST'])
def admin_edit_hotel(product_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()
    if not user or not user.is_admin:
        flash("Доступ заборонено!")
        return redirect(url_for('index'))

    product = db.session.execute(db.select(Product).filter_by(id=product_id)).scalar_one_or_none()

    if not product:
        flash("Готель не знайдено!")
        return redirect(url_for('admin_panel'))

    name = request.form.get('name', '').strip()
    price = request.form.get('price', type=float)
    description = request.form.get('description', '').strip()
    image_url = request.form.get('image_url', '').strip()

    if name:
        product.name = name
    if price and price > 0:
        product.price = price
    if description:
        product.description = description
    if image_url:
        product.image_url = image_url

    db.session.commit()

    flash(f"Готель '{product.name}' успішно оновлено!")
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete_hotel/<int:product_id>', methods=['POST'])
def admin_delete_hotel(product_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()
    if not user or not user.is_admin:
        flash("Доступ заборонено!")
        return redirect(url_for('index'))

    product = db.session.execute(db.select(Product).filter_by(id=product_id)).scalar_one_or_none()

    if not product:
        flash("Готель не знайдено!")
        return redirect(url_for('admin_panel'))

    active_bookings = db.session.execute(
        db.select(Booking).filter_by(product_id=product_id, status='active')
    ).scalars().all()

    if active_bookings:
        flash(f"Неможливо видалити готель '{product.name}' - є активні бронювання!")
        return redirect(url_for('admin_panel'))

    hotel_name = product.name
    db.session.delete(product)
    db.session.commit()

    flash(f"Готель '{hotel_name}' успішно видалено!")
    return redirect(url_for('admin_panel'))


@app.route('/extend_booking/<int:booking_id>', methods=['POST'])
def extend_booking(booking_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    booking = db.session.execute(
        db.select(Booking).filter_by(id=booking_id, user_id=session['user_id'], status='active')
    ).scalar_one_or_none()

    if not booking:
        flash("Бронювання не знайдено або вже скасоване!")
        return redirect(url_for('booking_history'))

    extra_days = request.form.get('extra_days', type=int)

    if not extra_days or extra_days <= 0:
        flash("Вкажіть кількість днів для продовження!")
        return redirect(url_for('booking_history'))

    if extra_days > 30:
        flash("Максимальне продовження - 30 днів!")
        return redirect(url_for('booking_history'))

    new_check_out = booking.check_out + timedelta(days=extra_days)

    product = db.session.execute(db.select(Product).filter_by(id=booking.product_id)).scalar_one_or_none()

    if not product:
        flash("Готель не знайдено!")
        return redirect(url_for('booking_history'))

    overlapping_bookings = db.session.execute(
        db.select(Booking).filter(
            Booking.product_id == booking.product_id,
            Booking.status == 'active',
            Booking.id != booking_id,
            Booking.check_in < new_check_out,
            Booking.check_out > booking.check_out
        )
    ).scalars().all()

    if overlapping_bookings:
        flash(f"Неможливо продовжити бронювання - номер вже заброньовано на ці дати!")
        return redirect(url_for('booking_history'))

    extra_price = calculate_price(product.price, extra_days)

    user = db.session.execute(db.select(User).filter_by(id=session['user_id'])).scalar_one_or_none()

    if not user:
        flash("Користувача не знайдено!")
        return redirect(url_for('booking_history'))

    if user.balance < extra_price:
        flash(f"Недостатньо коштів! Потрібно {extra_price:.2f} грн, а у вас {user.balance:.2f} грн")
        return redirect(url_for('booking_history'))

    booking.check_out = new_check_out
    booking.total_price += extra_price
    user.balance -= extra_price

    db.session.commit()

    flash(f"Бронювання успішно продовжено на {extra_days} дн. до {new_check_out.strftime('%d.%m.%Y')}! Списано {extra_price:.2f} грн")
    return redirect(url_for('booking_history'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)

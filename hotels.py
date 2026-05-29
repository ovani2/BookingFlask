from database import db, Product

def generate_hotels():
    if not db.session.execute(db.select(Product)).scalars().first():
        print("Наповнюємо базу даних 50 готельними номерами...")
        
        products_list = [
            Product(name="Номер Люкс №101", price=2500.0, description="Просторий номер з видом на місто.", image_url="https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=500"),
            Product(name="Стандартний номер №102", price=1200.0, description="Затишний номер для двох.", image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"),
            Product(name="Сімейний номер №103", price=3000.0, description="Просторий номер для всієї родини.", image_url="https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=500"),
            Product(name="Делюкс №104", price=1800.0, description="Комфортний номер з усіма зручностями.", image_url="https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=500"),
            Product(name="Люкс Преміум №105", price=2200.0, description="Елегантний номер з високим рівнем комфорту.", image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500"),
            Product(name="Стандарт одномісний №106", price=1000.0, description="Затишний номер для одного або двох.", image_url="https://images.unsplash.com/photo-1505691938895-1758e0c283e1?w=500"),
            Product(name="Номер Люкс №107", price=2600.0, description="Просторий преміум-номер з великим ліжком.", image_url="https://images.unsplash.com/photo-1582719508461-905c673771fd?w=500"),
            Product(name="Стандартний номер №108", price=1250.0, description="Класичний стандарт з усією необхідною технікою.", image_url="https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=500"),
            Product(name="Сімейний номер №109", price=3100.0, description="Комфортне розміщення для батьків та дітей.", image_url="https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=500"),
            Product(name="Делюкс №110", price=1850.0, description="Покращений інтер'єр та сучасний дизайн.", image_url="https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=500"),
            
            Product(name="Люкс №111", price=2300.0, description="Чудовий номер з окремою зоною для відпочинку.", image_url="https://images.unsplash.com/photo-1591088398332-8a7791972843?w=500"),
            Product(name="Стандарт №112", price=1050.0, description="Економний та комфортний варіант для поїздки.", image_url="https://images.unsplash.com/photo-1611892440504-42a792e24d02?w=500"),
            Product(name="Номер Люкс №113", price=2700.0, description="Люкс класу преміум з видом на центральний парк.", image_url="https://images.unsplash.com/photo-1568495248636-6432b97bd949?w=500"),
            Product(name="Стандартний номер №114", price=1300.0, description="Світлий номер зі швидким Wi-Fi та кондиціонером.", image_url="https://images.unsplash.com/photo-1598928506311-c55ded91a20c?w=500"),
            Product(name="Сімейний номер №115", price=3200.0, description="Дві окремі кімнати для максимальної зручності.", image_url="https://images.unsplash.com/photo-1606046604972-77cc76aee944?w=500"),
            Product(name="Делюкс №116", price=1900.0, description="Сучасні меблі та велика ванна кімната.", image_url="https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=500"),
            Product(name="Люкс №117", price=2400.0, description="Панорамні вікна та включений сніданок.", image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"),
            Product(name="Стандарт №118", price=1100.0, description="Компактний номер зі зручним одномісним ліжком.", image_url="https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=500"),
            Product(name="Номер Люкс №119", price=2800.0, description="Дизайнерський ремонт та розкішна міні-бар зона.", image_url="https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=500"),
            Product(name="Стандартний номер №120", price=1350.0, description="Оптимальний вибір для ділових поїздок та відряджень.", image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500"),
            
            Product(name="Сімейний номер №121", price=3300.0, description="Затишна атмосфера та додаткові дитячі ліжка.", image_url="https://images.unsplash.com/photo-1505691938895-1758e0c283e1?w=500"),
            Product(name="Делюкс №122", price=1950.0, description="Звукоізольовані стіни та робочий стіл біля вікна.", image_url="https://images.unsplash.com/photo-1582719508461-905c673771fd?w=500"),
            Product(name="Люкс №123", price=2450.0, description="Кавомашина у номері та халати з капцями.", image_url="https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=500"),
            Product(name="Стандарт №124", price=1120.0, description="Чистий та охайний номер з ортопедичним матрацом.", image_url="https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=500"),
            Product(name="Номер Люкс №125", price=2900.0, description="Ексклюзивний люкс з власною терасою.", image_url="https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=500"),
            Product(name="Стандартний номер №126", price=1400.0, description="Свіжий ремонт та телевізор з плоским екраном.", image_url="https://images.unsplash.com/photo-1591088398332-8a7791972843?w=500"),
            Product(name="Сімейний номер №127", price=3400.0, description="Великий обідній стіл та міні-кухня.", image_url="https://images.unsplash.com/photo-1611892440504-42a792e24d02?w=500"),
            Product(name="Делюкс №128", price=2000.0, description="Максимальний комфорт, халати та косметичні засоби.", image_url="https://images.unsplash.com/photo-1568495248636-6432b97bd949?w=500"),
            Product(name="Люкс №129", price=2500.0, description="Стильний люкс з великою гардеробною кімнатою.", image_url="https://images.unsplash.com/photo-1598928506311-c55ded91a20c?w=500"),
            Product(name="Стандарт №130", price=1150.0, description="Ідеальний вибір для ночівлі під час подорожі.", image_url="https://images.unsplash.com/photo-1606046604972-77cc76aee944?w=500"),
            
            Product(name="Номер Люкс №131", price=2950.0, description="Ванна кімната з джакузі та душовою кабіною.", image_url="https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=500"),
            Product(name="Стандартний номер №132", price=1420.0, description="Комфортні умови за доступною ціною.", image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"),
            Product(name="Сімейний номер №133", price=3450.0, description="Простір для ігор дітей та відпочинку дорослих.", image_url="https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=500"),
            Product(name="Делюкс №134", price=2050.0, description="Гарний краєвид на вечірнє місто.", image_url="https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=500"),
            Product(name="Люкс №135", price=2550.0, description="Індивідуальна система кондиціонування клімату.", image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500"),
            Product(name="Стандарт №136", price=1180.0, description="Компактне планування, зручне крісло.", image_url="https://images.unsplash.com/photo-1505691938895-1758e0c283e1?w=500"),
            Product(name="Номер Люкс №137", price=3000.0, description="Сніданок шведський стіл включено у вартість.", image_url="https://images.unsplash.com/photo-1582719508461-905c673771fd?w=500"),
            Product(name="Стандартний номер №138", price=1450.0, description="Щоденне прибирання, чиста білизна та рушники.", image_url="https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=500"),
            Product(name="Сімейний номер №139", price=3500.0, description="Безпечний та просторий номер для сімей з малюками.", image_url="https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=500"),
            Product(name="Делюкс №140", price=2100.0, description="Електронний сейф для цінних речей.", image_url="https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=500"),
            
            Product(name="Люкс №141", price=2600.0, description="Окремий кабінет для роботи та переговорів.", image_url="https://images.unsplash.com/photo-1591088398332-8a7791972843?w=500"),
            Product(name="Стандарт №142", price=1200.0, description="Фен, праска та прасувальна дошка за запитом.", image_url="https://images.unsplash.com/photo-1611892440504-42a792e24d02?w=500"),
            Product(name="Номер Люкс №143", price=3100.0, description="Доступ до VIP-зали відпочинку готелю.", image_url="https://images.unsplash.com/photo-1568495248636-6432b97bd949?w=500"),
            Product(name="Стандартний номер №144", price=1480.0, description="Зручне розташування на першому поверсі.", image_url="https://images.unsplash.com/photo-1598928506311-c55ded91a20c?w=500"),
            Product(name="Сімейний номер №145", price=3600.0, description="Повністю укомплектована кухня та посудомийка.", image_url="https://images.unsplash.com/photo-1606046604972-77cc76aee944?w=500"),
            Product(name="Делюкс №146", price=2150.0, description="М'яке освітлення та велике дзеркало.", image_url="https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=500"),
            Product(name="Люкс №147", price=2650.0, description="Покращена шумоізоляція та меню подушок.", image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"),
            Product(name="Стандарт №148", price=1220.0, description="Бюджетний номер для короткотривалих зупинок.", image_url="https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=500"),
            Product(name="Номер Люкс №149", price=3200.0, description="Королівське ліжко розміру King Size.", image_url="https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=500"),
            Product(name="Стандартний номер №150", price=1500.0, description="Класичний світлий номер з чудовою атмосферою.", image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500")
        ]
        
        db.session.add_all(products_list)
        db.session.commit()
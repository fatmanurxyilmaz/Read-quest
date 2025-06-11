# app/routes.py

from flask import render_template, request, current_app, Blueprint, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
from . import recommendations_logic_vol2
from .models import db, User, TestResult, SavedBook

main = Blueprint('main', __name__)


@main.route('/')
def home():
    return render_template('home.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.profile'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user is None or not user.check_password(request.form['password']):
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        login_user(user, remember=True)
        return redirect(url_for('main.profile'))
    return render_template('login.html')


@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@main.route('/register', methods=['GET', 'POST'])
# app/routes.py dosyasındaki YENİ ve GÜVENLİ fonksiyon

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.profile'))

    if request.method == 'POST':
        # Formdan gelen kullanıcı adını ve emaili kontrol et
        existing_user = User.query.filter_by(username=request.form['username']).first()
        if existing_user:
            flash('This username is already taken. Please choose a different one.')
            return redirect(url_for('main.register'))

        existing_email = User.query.filter_by(email=request.form['email']).first()
        if existing_email:
            flash('This email address is already registered. Please use a different one.')
            return redirect(url_for('main.register'))

        # Eğer kullanıcı adı ve email uygunsa, yeni kullanıcıyı oluştur
        user = User(username=request.form['username'], email=request.form['email'])
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()

        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('main.login'))

    return render_template('register.html')


@main.route('/profile')
@login_required
def profile():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    test_results = user.test_results.order_by(TestResult.timestamp.desc()).all()
    saved_books = user.saved_books.order_by(SavedBook.timestamp.desc()).all()
    return render_template('profile.html', user=user, test_results=test_results, saved_books=saved_books)


@main.route('/quiz')
def quiz():
    questions = current_app.config['QUIZ_QUESTIONS']
    return render_template('quiz_form_vol2.html', questions=questions)


@main.route('/result', methods=['POST'])
@login_required
def result():
    # ... (result fonksiyonunuzun başındaki skor hesaplama mantığı aynı kalacak) ...
    quiz_questions = current_app.config['QUIZ_QUESTIONS']
    reader_type_genres = current_app.config['READER_TYPE_GENRES']
    reader_type_descriptions = current_app.config['READER_TYPE_DESCRIPTIONS']
    scores = {ptype: 0 for ptype in reader_type_genres.keys()}

    for q in quiz_questions:
        qid = str(q['id'])
        if q.get("multiple"):
            selected_indices = request.form.getlist(f"question_{qid}")
            if "max_select" in q and len(selected_indices) > q["max_select"]:
                selected_indices = selected_indices[:q["max_select"]]

            for idx_str in selected_indices:
                try:
                    idx = int(idx_str)
                    if 0 <= idx < len(q['options']):
                        option = q['options'][idx]
                        for ptype in option['types']:
                            if ptype in scores:
                                scores[ptype] += 1
                except ValueError:
                    pass
        else:
            selected_idx_str = request.form.get(f"question_{qid}")
            if selected_idx_str is not None:
                try:
                    idx = int(selected_idx_str)
                    if 0 <= idx < len(q['options']):
                        option = q['options'][idx]
                        for ptype in option['types']:
                            if ptype in scores:
                                scores[ptype] += 1
                except ValueError:
                    pass

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_scores[:3]
    top_type_description = ""

    # Test sonucunu veritabanına kaydet
    if top_3:
        top_type_name = top_3[0][0]
        # YENİ: En üstteki tipin açıklamasını alalım
        top_type_description = reader_type_descriptions.get(top_type_name, "Bu tip için bir açıklama bulunamadı.")
        top_type_image = f"{top_type_name}.jpg"
        test_result = TestResult(reader_type=top_type_name, score=top_3[0][1], author=current_user)
        db.session.add(test_result)
        db.session.commit()
        flash('Your test result has been saved!')

    return render_template('quiz_result.html',
                           top_types=top_3,
                           top_type_description=top_type_description,
                           top_type_image=top_type_image)


@main.route('/recommendations')
@login_required
def recommendations():
    # ... (recommendations fonksiyonunuzun mantığı büyük ölçüde aynı kalacak) ...
    user_reader_type = request.args.get('type')
    reader_type_genres = current_app.config['READER_TYPE_GENRES']
    global_excluded_tags = current_app.config['GLOBAL_EXCLUDED_TAGS']
    character_specific_exclusions = current_app.config['CHARACTER_SPECIFIC_EXCLUSIONS']
    tag_weights = current_app.config['TAG_WEIGHTS']
    if not user_reader_type or user_reader_type not in reader_type_genres:
        return "Geçersiz okuyucu tipi veya tip belirtilmedi. <a href='/'>Ana Sayfa</a>"

    preferred_genres = reader_type_genres[user_reader_type]

    # Genel ve özel dışlama listelerini birleştir
    final_excluded_tags = set(global_excluded_tags)
    specific_exclusions = character_specific_exclusions.get(user_reader_type, [])
    final_excluded_tags.update(specific_exclusions)

    # O karaktere özel ağırlıkları al
    character_weights = tag_weights.get(user_reader_type, {})

    # Nihai fonksiyonu çağır (api_key parametresi OLMADAN)
    recommended_books = recommendations_logic_vol2.get_recommendations_with_weighted_scoring(
        preferred_genres,
        final_limit=12,
        excluded_tags=list(final_excluded_tags),
        tag_weights=character_weights
    )

    return render_template('recommendations.html', reader_type=user_reader_type, books=recommended_books)


@main.route('/save_book', methods=['POST'])
@login_required
def save_book():
    book_id = request.form.get('book_id')
    title = request.form.get('title')
    author = request.form.get('author')
    thumbnail = request.form.get('thumbnail')

    # Kitabın daha önce kaydedilip edilmediğini kontrol et
    existing_book = SavedBook.query.filter_by(book_id=book_id, user_id=current_user.id).first()
    if existing_book:
        flash('This book is already in your list.')
    else:
        saved_book = SavedBook(
            book_id=book_id,
            title=title,
            author=author,
            thumbnail=thumbnail,
            owner=current_user
        )
        db.session.add(saved_book)
        db.session.commit()
        flash(f'"{title}" has been added to your reading list!')

    # Kullanıcıyı geldiği sayfaya geri yönlendir
    return redirect(request.referrer or url_for('main.recommendations'))


# app/routes.py dosyasının sonuna eklenecek kod

@main.route('/discover')
def discover_types():
    """Tüm okuyucu tiplerini, açıklamalarını ve görsellerini listeleyen bir sayfa oluşturur."""

    # config.py'den okuyucu tipi açıklamalarını alıyoruz.
    descriptions = current_app.config['READER_TYPE_DESCRIPTIONS']

    # Şablonda daha kolay kullanmak için veriyi yeniden yapılandıralım.
    reader_types_list = []
    for type_key, description in descriptions.items():
        reader_types_list.append({
            'key': type_key,
            # Ekranda daha güzel görünmesi için alt çizgileri boşlukla değiştirip baş harfleri büyütüyoruz.
            'name': type_key.replace('_', ' ').title(),
            'description': description,
            # Her tip için görsel dosyasının adını oluşturuyoruz (örn: the_contemplator.jpg)
            'image_file': f"{type_key}.jpg"
        })

    return render_template('discover.html', reader_types=reader_types_list)
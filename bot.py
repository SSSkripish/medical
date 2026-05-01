import os
import logging
import json
import random
import threading
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ======================== НАСТРОЙКИ ========================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("TELEGRAM_TOKEN не установлен в переменных окружения!")
    exit(1)

# Хранилища
user_language = {}
active_tests = {}
active_games = {}
SUBSCRIBERS_FILE = "subscribers.json"

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_subscribers(data):
    with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ======================== БАЗА СЛОВ ДЛЯ РАССЫЛКИ И ИГР ========================
WORDS_DB = [
    {"term": "Musculus", "translation_ru": "Мышца", "translation_en": "Muscle", "example_ru": "Musculus biceps brachii", "example_en": "Musculus biceps brachii"},
    {"term": "Nervus", "translation_ru": "Нерв", "translation_en": "Nerve", "example_ru": "Nervus opticus", "example_en": "Nervus opticus"},
    {"term": "Os", "translation_ru": "Кость", "translation_en": "Bone", "example_ru": "Os femoris", "example_en": "Os femoris"},
    {"term": "Arteria", "translation_ru": "Артерия", "translation_en": "Artery", "example_ru": "Arteria carotis", "example_en": "Arteria carotis"},
    {"term": "Vena", "translation_ru": "Вена", "translation_en": "Vein", "example_ru": "Vena cava", "example_en": "Vena cava"},
    {"term": "Ligamentum", "translation_ru": "Связка", "translation_en": "Ligament", "example_ru": "Ligamentum cruciatum", "example_en": "Ligamentum cruciatum"},
    {"term": "Cranium", "translation_ru": "Череп", "translation_en": "Skull", "example_ru": "Cranium cerebrale", "example_en": "Cranium cerebrale"},
    {"term": "Thorax", "translation_ru": "Грудная клетка", "translation_en": "Thorax", "example_ru": "Thorax apertura", "example_en": "Thorax apertura"},
    {"term": "Ventriculus", "translation_ru": "Желудочек", "translation_en": "Ventricle", "example_ru": "Ventriculus sinister", "example_en": "Ventriculus sinister"},
    {"term": "Columna vertebralis", "translation_ru": "Позвоночный столб", "translation_en": "Spinal column", "example_ru": "Columna vertebralis", "example_en": "Columna vertebralis"},
    {"term": "Hepar", "translation_ru": "Печень", "translation_en": "Liver", "example_ru": "Hepar", "example_en": "Hepar"},
    {"term": "Ren", "translation_ru": "Почка", "translation_en": "Kidney", "example_ru": "Ren", "example_en": "Ren"},
    {"term": "Pulmo", "translation_ru": "Лёгкое", "translation_en": "Lung", "example_ru": "Pulmo dexter", "example_en": "Pulmo dexter"},
    {"term": "Cor", "translation_ru": "Сердце", "translation_en": "Heart", "example_ru": "Cor", "example_en": "Cor"},
    {"term": "Cerebrum", "translation_ru": "Головной мозг", "translation_en": "Brain", "example_ru": "Cerebrum", "example_en": "Cerebrum"}
]

# ======================== ТЕКСТЫ ИНТЕРФЕЙСА ========================
TEXTS = {
    'ru': {
        'start': "🇷🇺 Добро пожаловать в справочник по медицинской латыни!\n\nВыберите раздел:",
        'language': "🌐 Выберите язык",
        'lang_set': "Язык установлен на русский",
        'handbook': "📚 Справочник",
        'tests': "📝 Тесты",
        'games': "🎮 Игры",
        'daily': "📧 Ежедневная рассылка",
        'about': "ℹ️ О нас",
        'subscribe': "✅ Подписаться",
        'unsubscribe': "❌ Отписаться",
        'set_time': "⏰ Настроить время",
        'subscribed': "Вы подписались на ежедневную рассылку!",
        'unsubscribed': "Вы отписались от рассылки.",
        'time_set': "Время рассылки установлено на {time}:00",
        'back': "◀️ Назад",
        'youtube_title': "📺 YouTube-каналы по латыни",
        'youtube_links': [
            "• Медицинская латынь — https://youtube.com/@medicallatin",
            "• Латынь просто — https://youtube.com/@latynprosto",
            "• Анатомия 3D — https://youtube.com/@anatomy3d"
        ],
        'literature_title': "📚 Учебники",
        'literature_links': [
            "• Чернявский М.Н. — Латинский язык и основы медицинской терминологии",
            "• Городкова Ю.И. — Латинский язык для медицинских вузов",
            "• Кондратьев Д.К. — Латинский язык для медицинских колледжей"
        ],
        'apps_title': "📱 Приложения",
        'apps_ios_list': ["• Medical Latin", "• Anatomy Latin", "• LatinRx"],
        'apps_android_list': ["• Medical Latin Quiz", "• Latin for Med Students"],
        'medical_title': "🩺 Пособия по медицинской латыни",
        'medical_links': [
            "• Чернявский М.Н. – «Латинский язык и основы медицинской терминологии»",
            "• Городкова Ю.И. – «Латинский язык для медицинских вузов»"
        ],
        'maps_links': [
            "• Анатомия человека 3D — https://anatomy3d.com",
            "• Скелет человека — https://www.biodigital.com"
        ],
        'about_text': "👨‍⚕️ Проектная работа ученика 10 класса Абдуллаева Эмиля\n\n📩 Связь: @OfficialSeptember",
        'tips': "💡 Советы по изучению:\n1. Учите терминоэлементы\n2. Тренируйте рецепты\n3. Используйте Anki\n4. Повторяйте каждый день",
        'test_level': "Выберите уровень сложности:",
        'test_easy': "🟢 Лёгкий",
        'test_medium': "🟡 Средний",
        'test_hard': "🔴 Сложный",
        'test_complete': "✅ Тест завершён!\nПравильных ответов: {score} из {total} ({percent}%)",
        'game_start': "🎲 Игра «Угадай термин»\nУ вас 3 жизни. Ответьте на 5 вопросов.\n\nНажмите «Начать игру»",
        'game_question': "❤️ Жизней: {lives}/3\n❓ Вопрос {current}/5\n\n{term}?",
        'game_correct': "✅ Верно! +1 балл",
        'game_wrong': "❌ Неверно. Правильный ответ: {answer}\n❤️ -1 жизнь",
        'game_win': "🏆 Победа! Вы ответили на {score}/5 вопросов",
        'game_lose': "💀 Вы проиграли. Правильных ответов: {score}/5",
        'game_button': "🎮 Начать игру",
        'daily_term': "📅 Ежедневный термин\n\n{term} — {translation}\n\nПример: {example}"
    },
    'en': {
        'start': "🇬🇧 Welcome to Medical Latin reference!\n\nChoose a section:",
        'language': "🌐 Select language",
        'lang_set': "Language set to English",
        'handbook': "📚 Handbook",
        'tests': "📝 Tests",
        'games': "🎮 Games",
        'daily': "📧 Daily newsletter",
        'about': "ℹ️ About",
        'subscribe': "✅ Subscribe",
        'unsubscribe': "❌ Unsubscribe",
        'set_time': "⏰ Set time",
        'subscribed': "You subscribed to daily newsletter!",
        'unsubscribed': "You unsubscribed.",
        'time_set': "Delivery time set to {time}:00",
        'back': "◀️ Back",
        'youtube_title': "📺 YouTube channels",
        'youtube_links': ["• Medical Latin — https://youtube.com/@medicallatin"],
        'literature_title': "📚 Textbooks",
        'literature_links': ["• Chernyavsky M.N. — Latin & Medical Terminology"],
        'apps_title': "📱 Apps",
        'apps_ios_list': ["• Medical Latin", "• Anatomy Latin"],
        'apps_android_list': ["• Medical Latin Quiz"],
        'medical_title': "🩺 Medical Latin resources",
        'medical_links': ["• Chernyavsky M.N. — Latin & Medical Terminology"],
        'maps_links': ["• Anatomy 3D — https://anatomy3d.com"],
        'about_text': "👨‍⚕️ Project by Emil Abdullaev, grade 10\n\n📩 Contact: @OfficialSeptember",
        'tips': "💡 Tips:\n1. Learn term elements\n2. Practice prescriptions\n3. Use spaced repetition",
        'test_level': "Choose difficulty:",
        'test_easy': "🟢 Easy",
        'test_medium': "🟡 Medium",
        'test_hard': "🔴 Hard",
        'test_complete': "✅ Test completed!\nScore: {score}/{total} ({percent}%)",
        'game_start': "🎲 Game 'Guess the term'\n3 lives, 5 questions.\n\nPress 'Start game'",
        'game_question': "❤️ Lives: {lives}/3\n❓ Q{current}/5\n\n{term}?",
        'game_correct': "✅ Correct!",
        'game_wrong': "❌ Wrong. Answer: {answer}\n❤️ -1 life",
        'game_win': "🏆 You win! Score: {score}/5",
        'game_lose': "💀 Game over. Score: {score}/5",
        'game_button': "🎮 Start game",
        'daily_term': "📅 Daily term\n\n{term} — {translation}\n\nExample: {example}"
    }
}

# ======================== ТЕСТЫ ========================
TESTS = {
    'easy': {
        'ru': [
            {"q": "Как переводится 'Musculus'?", "opt": ["Кость", "Мышца", "Нерв", "Связка"], "a": 1},
            {"q": "Что означает 'Os'?", "opt": ["Кость", "Рот", "Глаз", "Ухо"], "a": 0},
            {"q": "Как переводится 'Arteria'?", "opt": ["Вена", "Артерия", "Нерв", "Капилляр"], "a": 1}
        ],
        'en': [
            {"q": "What is 'Musculus'?", "opt": ["Bone", "Muscle", "Nerve", "Ligament"], "a": 1},
            {"q": "What does 'Os' mean?", "opt": ["Bone", "Mouth", "Eye", "Ear"], "a": 0},
            {"q": "What is 'Arteria'?", "opt": ["Vein", "Artery", "Nerve", "Capillary"], "a": 1}
        ]
    }
}

def get_text(user_id, key, **kwargs):
    lang = user_language.get(user_id, 'ru')
    text = TEXTS.get(lang, TEXTS['ru']).get(key, '')
    if kwargs:
        text = text.format(**kwargs)
    return text

# ======================== КЛАВИАТУРЫ ========================
def main_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(user_id, 'handbook'), callback_data='handbook')],
        [InlineKeyboardButton(get_text(user_id, 'tests'), callback_data='test_menu')],
        [InlineKeyboardButton(get_text(user_id, 'games'), callback_data='game_menu')],
        [InlineKeyboardButton(get_text(user_id, 'daily'), callback_data='daily_menu')],
        [InlineKeyboardButton(get_text(user_id, 'about'), callback_data='about')],
        [InlineKeyboardButton(get_text(user_id, 'language'), callback_data='language')]
    ])

def handbook_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 YouTube", callback_data='youtube')],
        [InlineKeyboardButton("📖 Литература", callback_data='literature')],
        [InlineKeyboardButton("📱 Приложения", callback_data='apps')],
        [InlineKeyboardButton("🩺 Пособия", callback_data='medical')],
        [InlineKeyboardButton("🗺️ 3D карты", callback_data='maps')],
        [InlineKeyboardButton(get_text(user_id, 'back'), callback_data='menu')]
    ])

def test_level_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(user_id, 'test_easy'), callback_data='test_easy')],
        [InlineKeyboardButton(get_text(user_id, 'test_medium'), callback_data='test_medium')],
        [InlineKeyboardButton(get_text(user_id, 'test_hard'), callback_data='test_hard')],
        [InlineKeyboardButton(get_text(user_id, 'back'), callback_data='menu')]
    ])

def game_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(user_id, 'game_button'), callback_data='game_start')],
        [InlineKeyboardButton(get_text(user_id, 'back'), callback_data='menu')]
    ])

def daily_keyboard(user_id):
    subs = load_subscribers()
    is_sub = str(user_id) in subs
    btn = get_text(user_id, 'unsubscribe') if is_sub else get_text(user_id, 'subscribe')
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn, callback_data='sub')],
        [InlineKeyboardButton(get_text(user_id, 'set_time'), callback_data='set_time')],
        [InlineKeyboardButton(get_text(user_id, 'back'), callback_data='menu')]
    ])

def time_keyboard():
    buttons = []
    for h in [9,10,11,12,13,14,15,16,17,18,19,20]:
        buttons.append([InlineKeyboardButton(f"{h}:00", callback_data=f'time_{h}')])
    buttons.append([InlineKeyboardButton("Назад", callback_data='daily_menu')])
    return InlineKeyboardMarkup(buttons)

def back_keyboard(user_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text(user_id, 'back'), callback_data='handbook')]])

def menu_keyboard(user_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data='menu')]])

def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("English", callback_data='lang_en')],
        [InlineKeyboardButton("Назад", callback_data='menu')]
    ])

def question_keyboard(answers):
    kb = [[InlineKeyboardButton(a, callback_data=f'ans_{i}')] for i,a in enumerate(answers)]
    return InlineKeyboardMarkup(kb)

def game_question_keyboard(options, lives, cur, term):
    kb = [[InlineKeyboardButton(o, callback_data=f'game_ans_{i}_{cur}_{lives}_{term}')] for i,o in enumerate(options)]
    return InlineKeyboardMarkup(kb)

# ======================== ОБРАБОТЧИКИ ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_language:
        user_language[uid] = 'ru'
    await update.message.reply_text(get_text(uid, 'start'), reply_markup=main_keyboard(uid))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    # ---------- ОТВЕТЫ НА ТЕСТ ----------
    if data.startswith('ans_'):
        if uid not in active_tests:
            await query.edit_message_text("Начните тест заново", reply_markup=menu_keyboard(uid))
            return
        test = active_tests[uid]
        ans = int(data.split('_')[1])
        if ans == test['q'][test['i']]['a']:
            test['score'] += 1
        test['i'] += 1
        if test['i'] < len(test['q']):
            q = test['q'][test['i']]
            await query.edit_message_text(f"Вопрос {test['i']+1}/{len(test['q'])}\n\n{q['q']}", reply_markup=question_keyboard(q['opt']))
        else:
            percent = int(test['score']/len(test['q'])*100)
            await query.edit_message_text(get_text(uid, 'test_complete', score=test['score'], total=len(test['q']), percent=percent), reply_markup=menu_keyboard(uid))
            del active_tests[uid]
        return

    # ---------- ОТВЕТЫ НА ИГРУ ----------
    if data.startswith('game_ans_'):
        parts = data.split('_')
        ans_i = int(parts[2])
        cur = int(parts[3])
        lives = int(parts[4])
        if uid not in active_games:
            await query.edit_message_text("Начните игру заново", reply_markup=game_keyboard(uid))
            return
        game = active_games[uid]
        q = game['q'][cur]
        if ans_i == q['correct']:
            game['score'] += 1
            feedback = get_text(uid, 'game_correct')
        else:
            lives -= 1
            game['lives'] = lives
            correct = q['options'][q['correct']]
            feedback = get_text(uid, 'game_wrong', answer=correct)
        game['i'] += 1
        if game['i'] >= len(game['q']):
            msg = get_text(uid, 'game_win', score=game['score'])
            await query.edit_message_text(msg, reply_markup=game_keyboard(uid))
            del active_games[uid]
        elif lives <= 0:
            msg = get_text(uid, 'game_lose', score=game['score'])
            await query.edit_message_text(msg, reply_markup=game_keyboard(uid))
            del active_games[uid]
        else:
            nxt = game['q'][game['i']]
            msg = get_text(uid, 'game_question', lives=lives, current=game['i']+1, term=nxt['term'])
            await query.edit_message_text(f"{feedback}\n\n{msg}", reply_markup=game_question_keyboard(nxt['options'], lives, game['i'], nxt['term']))
        return

    # ---------- НАВИГАЦИЯ ----------
    if data == 'menu':
        if uid in active_tests: del active_tests[uid]
        if uid in active_games: del active_games[uid]
        await query.edit_message_text(get_text(uid, 'start'), reply_markup=main_keyboard(uid))
    elif data == 'handbook':
        await query.edit_message_text("📚 Справочник", reply_markup=handbook_keyboard(uid))
    elif data == 'language':
        await query.edit_message_text("🌐 Выберите язык:", reply_markup=language_keyboard())
    elif data.startswith('lang_'):
        code = data.split('_')[1]
        if code in ['ru','en']:
            user_language[uid] = code
        await query.edit_message_text(get_text(uid, 'lang_set'), reply_markup=main_keyboard(uid))
    elif data == 'youtube':
        t = get_text(uid, 'youtube_title')
        links = "\n".join(TEXTS[user_language.get(uid,'ru')]['youtube_links'])
        await query.edit_message_text(f"{t}\n\n{links}", reply_markup=back_keyboard(uid))
    elif data == 'literature':
        t = get_text(uid, 'literature_title')
        links = "\n".join(TEXTS[user_language.get(uid,'ru')]['literature_links'])
        await query.edit_message_text(f"{t}\n\n{links}", reply_markup=back_keyboard(uid))
    elif data == 'apps':
        t = get_text(uid, 'apps_title')
        ios = "\n".join(TEXTS[user_language.get(uid,'ru')]['apps_ios_list'])
        android = "\n".join(TEXTS[user_language.get(uid,'ru')]['apps_android_list'])
        await query.edit_message_text(f"{t}\n\n🍏 App Store:\n{ios}\n\n🤖 Play Market:\n{android}", reply_markup=back_keyboard(uid))
    elif data == 'medical':
        t = get_text(uid, 'medical_title')
        items = "\n".join(TEXTS[user_language.get(uid,'ru')]['medical_links'])
        await query.edit_message_text(f"{t}\n\n{items}", reply_markup=back_keyboard(uid))
    elif data == 'maps':
        items = "\n".join(TEXTS[user_language.get(uid,'ru')]['maps_links'])
        await query.edit_message_text(f"🗺️ 3D атласы:\n\n{items}", reply_markup=back_keyboard(uid))
    elif data == 'about':
        await query.edit_message_text(get_text(uid, 'about_text'), reply_markup=menu_keyboard(uid))
    elif data == 'tips':
        await query.edit_message_text(get_text(uid, 'tips'), reply_markup=menu_keyboard(uid))

    # ---------- ТЕСТЫ ----------
    elif data == 'test_menu':
        await query.edit_message_text(get_text(uid, 'test_level'), reply_markup=test_level_keyboard(uid))
    elif data in ['test_easy', 'test_medium', 'test_hard']:
        level = data.split('_')[1]
        lang = user_language.get(uid, 'ru')
        qlist = TESTS.get(level, {}).get(lang, TESTS['easy']['ru'])
        active_tests[uid] = {'q': qlist, 'i': 0, 'score': 0}
        first = qlist[0]
        await query.edit_message_text(f"Вопрос 1/{len(qlist)}\n\n{first['q']}", reply_markup=question_keyboard(first['opt']))

    # ---------- ИГРЫ ----------
    elif data == 'game_menu':
        await query.edit_message_text(get_text(uid, 'game_start'), reply_markup=game_keyboard(uid))
    elif data == 'game_start':
        # выбираем 5 случайных слов
        sample = random.sample(WORDS_DB, 5)
        questions = []
        for w in sample:
            trans = w['translation_ru'] if user_language.get(uid,'ru')=='ru' else w['translation_en']
            # 3 случайных неправильных ответа
            others = [x['translation_ru'] if user_language.get(uid,'ru')=='ru' else x['translation_en'] for x in WORDS_DB if x['term'] != w['term']]
            wrong = random.sample(others, 3)
            opts = [trans] + wrong
            random.shuffle(opts)
            correct = opts.index(trans)
            questions.append({'term': w['term'], 'options': opts, 'correct': correct})
        active_games[uid] = {'q': questions, 'i': 0, 'score': 0, 'lives': 3}
        first = questions[0]
        msg = get_text(uid, 'game_question', lives=3, current=1, term=first['term'])
        await query.edit_message_text(msg, reply_markup=game_question_keyboard(first['options'], 3, 0, first['term']))

    # ---------- РАССЫЛКА ----------
    elif data == 'daily_menu':
        await query.edit_message_text(get_text(uid, 'daily'), reply_markup=daily_keyboard(uid))
    elif data == 'sub':
        subs = load_subscribers()
        uid_str = str(uid)
        if uid_str in subs:
            del subs[uid_str]
            msg = get_text(uid, 'unsubscribed')
        else:
            subs[uid_str] = 10  # время по умолчанию 10:00
            msg = get_text(uid, 'subscribed')
        save_subscribers(subs)
        await query.edit_message_text(msg, reply_markup=daily_keyboard(uid))
    elif data == 'set_time':
        await query.edit_message_text("Выберите час рассылки (по вашему часовому поясу):", reply_markup=time_keyboard())
    elif data.startswith('time_'):
        hour = int(data.split('_')[1])
        subs = load_subscribers()
        subs[str(uid)] = hour
        save_subscribers(subs)
        await query.edit_message_text(get_text(uid, 'time_set', time=hour), reply_markup=daily_keyboard(uid))

# ======================== ФОНОВАЯ РАССЫЛКА (ПОТОК) ========================
def daily_sender():
    while True:
        now = datetime.now()
        current_hour = now.hour
        subs = load_subscribers()
        if subs:
            # Берём случайное слово
            word = random.choice(WORDS_DB)
            for uid_str, hour in subs.items():
                if hour == current_hour:
                    uid = int(uid_str)
                    lang = user_language.get(uid, 'ru')
                    trans = word['translation_ru'] if lang == 'ru' else word['translation_en']
                    example = word['example_ru'] if lang == 'ru' else word['example_en']
                    text = get_text(uid, 'daily_term', term=word['term'], translation=trans, example=example)
                    # Отправка через requests (синхронно)
                    import requests
                    try:
                        requests.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', json={'chat_id': uid, 'text': text})
                        logger.info(f"Отправлено подписчику {uid}")
                    except Exception as e:
                        logger.error(f"Ошибка отправки {uid}: {e}")
        time.sleep(60)  # проверяем каждую минуту

# ======================== ЗАПУСК ========================
def main():
    # Запускаем поток рассылки
    thread = threading.Thread(target=daily_sender, daemon=True)
    thread.start()
    # Запускаем polling
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    logger.info("Бот запущен в режиме polling")
    app.run_polling()

if __name__ == '__main__':
    main()

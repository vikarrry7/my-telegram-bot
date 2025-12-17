import time
import requests
import random
from datetime import datetime, timedelta
import re
import wikipedia
import logging
import os
import base64
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import CallbackContext
import tempfile

TELEGRAM_TOKEN = "8230051824:AAH8k81yxhlUNTO-th6SoNMXbXwENYdlmao"  
CLARIFAI_API_KEY = "d10ada4daed04f01abd76e8f8d88b381"  

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Меню пиццерии
PIZZA_MENU = {
    "маргарита": {"price": 10, "desc": "Классическая пицца с томатами и моцареллой", "cooking_time": 15},
    "пепперони": {"price": 12, "desc": "Острая пицца с пепперони и сыром", "cooking_time": 18},
    "гавайская": {"price": 11, "desc": "С ананасами и ветчиной", "cooking_time": 16},
    "вегетарианская": {"price": 9, "desc": "С овощами и грибами", "cooking_time": 14},
    "сырная": {"price": 13, "desc": "Четыре вида сыра", "cooking_time": 17},
    "мясная": {"price": 14, "desc": "Ассорти из мясных деликатесов", "cooking_time": 20},
    "грибная": {"price": 10, "desc": "С лесными грибами", "cooking_time": 15},
    "карбонара": {"price": 13, "desc": "С беконом и соусом карбонара", "cooking_time": 18}
}

TOPPINGS_MENU = {
    "сыр": {"price": 1, "desc": "Дополнительный сыр", "category": "сыры"},
    "моцарелла": {"price": 1.5, "desc": "Сыр моцарелла", "category": "сыры"},
    "пармезан": {"price": 2, "desc": "Сыр пармезан", "category": "сыры"},
    "пепперони": {"price": 2, "desc": "Дополнительные пепперони", "category": "мясо"},
    "грибы": {"price": 1.5, "desc": "Свежие шампиньоны", "category": "овощи"},
    "оливки": {"price": 1, "desc": "Маслины", "category": "овощи"},
    "курица": {"price": 2.5, "desc": "Куриное филе", "category": "мясо"},
    "бекон": {"price": 3, "desc": "Хрустящий бекон", "category": "мясо"},
    "ветчина": {"price": 2, "desc": "Ветчина", "category": "мясо"},
    "ананасы": {"price": 1.5, "desc": "Свежие ананасы", "category": "овощи"},
    "перец": {"price": 1, "desc": "Сладкий перец", "category": "овощи"},
    "лук": {"price": 0.5, "desc": "Красный лук", "category": "овощи"},
    "томаты": {"price": 1, "desc": "Помидоры черри", "category": "овощи"},
    "соус": {"price": 0.5, "desc": "Дополнительный соус", "category": "соусы"},
    "острый соус": {"price": 0.5, "desc": "Острый соус", "category": "соусы"}
}

DESSERTS_MENU = {
    "тирамису": {"price": 6, "desc": "Классический итальянский десерт", "weight": "150г"},
    "чизкейк": {"price": 5, "desc": "Нью-йоркский чизкейк", "weight": "120г"},
    "мороженое": {"price": 4, "desc": "Ванильное мороженое", "weight": "100г", "flavors": ["ванильное", "шоколадное", "клубничное"]},
    "пончики": {"price": 3, "desc": "Сладкие пончики с сахарной пудрой", "weight": "80г", "quantity": 3},
    "печенье": {"price": 2, "desc": "Домашнее шоколадное печенье", "weight": "100г", "quantity": 5},
    "пирог": {"price": 8, "desc": "Яблочный пирог", "weight": "250г"},
    "булочка": {"price": 2.5, "desc": "Сдобная булочка с корицей", "weight": "100г"}
}

DRINK_MENU = {
    "кола": {"sizes": {"0.33л": 2, "0.5л": 3, "1л": 4}, "type": "газировка", "temp": "холодный"},
    "пепси": {"sizes": {"0.33л": 2, "0.5л": 3, "1л": 4}, "type": "газировка", "temp": "холодный"},
    "фанта": {"sizes": {"0.33л": 2, "0.5л": 3, "1л": 4}, "type": "газировка", "temp": "холодный"},
    "спрайт": {"sizes": {"0.33л": 2, "0.5л": 3, "1л": 4}, "type": "газировка", "temp": "холодный"},
    "вода": {"sizes": {"0.5л": 1, "1л": 2, "1.5л": 3}, "type": "без газа", "temp": "холодный"},
    "сок": {"sizes": {"0.2л": 3, "0.3л": 4, "1л": 5}, "type": "апельсиновый", "temp": "холодный", "flavors": ["апельсин", "яблоко", "виноград"]},
    "чай": {"sizes": {"чашка": 2, "чайник": 5}, "type": "горячий напиток", "temp": "горячий", "flavors": ["черный", "зеленый", "фруктовый"]},
    "кофе": {"sizes": {"эспрессо": 3, "американо": 4, "капучино": 5, "латте": 6}, "type": "горячий напиток", "temp": "горячий"}
}

# База знаний для энциклопедии
RUSSIAN_DESCRIPTIONS = {
    'хомяк': "Хомяк — небольшое млекопитающее из подсемейства хомяковых. Известны своими защечными мешками, в которых переносят пищу. Популярны в качестве домашних питомцев. Наиболее распространенный вид — сирийский хомяк. Активны в основном ночью.",
    'ежик': "Ёжик (лат. Erinaceus) — млекопитающее из семейства ежовых. Известны своими иголки, которые на самом деле являются видоизмененными волосами. Питаются насекомыми, червями, иногда мелкими позвоночными и фруктами. Активны в основном ночью, на зиму впадают в спячку.",
    'собака': "Собака (лат. Canis lupus familiaris) — домашнее животное, одно из наиболее популярных животных-компаньонов. Первое одомашненное животное, был одомашнен примерно 15 000 лет назад. Существует множество пород собак, которые различаются по размерам, масти, сложению и поведение.",
    'кошка': "Кошка (лат. Felis catus) — домашнее животное, одно из наиболее популярных «животных-компаньонов». Была одомашнена около 10 000 лет назад на Ближнем Востоке. Кошки являются хищниками и сохранили многие черты своих диких предков.",
    'слон': "Слон — самое крупное современное наземное животное. Отличается хоботом, бивнями и большими ушами. Существует три вида слонов: африканский саванный слон, африканский лесной слон и азиатский слон. Слоны живут семейными группами во главе со старшей самкой.",
    'дельфин': "Дельфины — морские млекопитающие из отряда китообразных. Известны своим высоким интеллектом, игривым поведением и способностью к эхолокации. Спят дельфины особым образом: у них спит только одно полушарие мозга, чтобы они могли продолжать дышать и контролировать свое положение в воде.",
    'лев': "Лев (лат. Panthera leo) — хищное млекопитающее рода пантер. Второй по величине после тигра представитель семейства кошачьих в мире. Единственные кошачьи, живущие в прайдах. Самцы отличаются гривой.",
    'тигр': "Тигр (лат. Panthera tigris) — самый крупный и один из самых узнаваемых видов кошачьих. Отличается яркой оранжевой шерстью с черными полосами. Находится под угрозом исчезновения. Обитает в Азии.",
    'млекопитающее': "Млекопитающие — класс позвоночных животных, основной отличительной особенностью которых является вскармливание детёнышей молоком. Другие характерные черты: волосяной покров, теплокровность, наличие диафрагмы и развитой коры головного мозга.",
    'ии': "Искусственный интеллект (ИИ) — это технология создания компьютерных систем, способных выполнять задачи, требующие человеческого интеллекта: распознавание образов, принятие решений, обучение, понимание естественного языка. ИИ используется в медицине, транспорте, финансах и многих других областях.",
    'вопросительный знак': "Вопросительный знак (?) — знак препинания, ставится обычно в конце предложения для выражения вопроса или сомнения. Встречается в печатных книгах с XVI века, однако для выражения вопроса он закрепляется значительно позже, лишь в XVIII веке.",
}

# Глобальные переменные состояний
user_states = {}
user_data = {}
user_context = {}


def extract_intent_simple(text):
    """Упрощенное определение намерения пользователя (без spaCy)"""
    text_lower = text.lower()
    
    # Проверка голода
    hungry_words = ['голоден', 'голодна', 'хочу есть', 'проголодался', 'проголодалась', 
                   'hungry', "i'm hungry", 'want to eat', 'starving']
    if any(word in text_lower for word in hungry_words):
        return 'hungry'
    
    # Проверка напитков
    drink_keywords = ['cola', 'pepsi', 'fanta', 'sprite', 'water', 'juice', 'tea', 'coffee',
                     'кола', 'пепси', 'фанта', 'спрайт', 'вода', 'сок', 'чай', 'кофе']
    for drink in drink_keywords:
        if drink in text_lower:
            return f'order_{drink}'
    
    # Проверка пиццы
    pizza_keywords = ['pizza', 'пицц', 'пиццу', 'пицца']
    if any(word in text_lower for word in pizza_keywords):
        return 'orderPizza'
    
    # Проверка десертов
    dessert_keywords = ['dessert', 'десерт', 'сладкое', 'мороженое', 'чизкейк', 'тирамису']
    if any(word in text_lower for word in dessert_keywords):
        return 'orderDessert'
    
    # Проверка топпингов
    topping_keywords = ['topping', 'добавка', 'топпинг', 'сыр', 'грибы', 'оливки']
    if any(word in text_lower for word in topping_keywords) and any(word in text_lower for word in ['добавь', 'добавить']):
        return 'addTopping'
    
    # Если есть слова "хочу", "давай", "закажи"
    want_words = ['хочу', 'давай', 'закажи', 'want', 'order', 'give me']
    if any(word in text_lower for word in want_words):
        return 'wantSomething'
    
    return None

def extract_drink_info(text):
    """Извлекает информацию о напитке из текста"""
    text_lower = text.lower()
    
    all_drinks = list(DRINK_MENU.keys())
    
    drink_name = None
    for drink in all_drinks:
        if drink in text_lower:
            drink_name = drink
            break
    
    if not drink_name:
        for drink in all_drinks:
            for word in text_lower.split():
                if drink.startswith(word) or word.startswith(drink):
                    drink_name = drink
                    break
            if drink_name:
                break
    
    size = None
    flavor = None
    
    if drink_name and drink_name in DRINK_MENU:
        sizes = DRINK_MENU[drink_name]['sizes']
        
        for size_option in sizes.keys():
            clean_text = text_lower.replace('.', ' ').replace(',', ' ').replace('л', ' л')
            if size_option in clean_text or size_option.replace('л', '') in clean_text:
                size = size_option
                break
        
        if not size:
            numbers = re.findall(r'\d+\.?\d*', text_lower)
            for num in numbers:
                possible_sizes = [f"{num}л", f"{num} л", f"{num}"]
                for possible_size in possible_sizes:
                    if possible_size in sizes:
                        size = possible_size
                        break
                if size:
                    break
        
        if 'flavors' in DRINK_MENU[drink_name]:
            flavors = DRINK_MENU[drink_name]['flavors']
            for flav in flavors:
                if flav in text_lower:
                    flavor = flav
                    break
    
    return drink_name, size, flavor

def get_greeting():
    """Случайное приветствие"""
    greetings = [
        "Приветствую! 👋",
        "Добро пожаловать! 😊",
        "Рад вас видеть! 🌟",
        "Здравствуйте! 🎉",
        "Привет! Готов помочь с заказом! 🍕",
        "С возвращением! 😄"
    ]
    return random.choice(greetings)

def get_hungry_response():
    """Ответ на 'я голоден'"""
    responses = [
        "Похоже, пора перекусить! 😋 Что бы вы хотели заказать?",
        "Отличный аппетит - залог здоровья! 🍽️ Могу предложить пиццу или что-то ещё?",
        "Голод - не тётка! 🍕 Давайте выберем что-нибудь вкусненькое!",
        "Понял, вы голодны! 🌮 Что из нашего меню вас интересует?",
        "Время подкрепиться! 🍔 Чем могу помочь с заказом?"
    ]
    return random.choice(responses)

def format_pizza_menu():
    """Форматирует меню пицц"""
    menu_text = "🍕 *НАШЕ МЕНЮ ПИЦЦ:*\n\n"
    for name, details in PIZZA_MENU.items():
        menu_text += f"• *{name.capitalize()}* - ${details['price']} (готовится {details['cooking_time']} мин)\n"
        menu_text += f"  _{details['desc']}_\n\n"
    menu_text += "Просто напишите, какую хотите заказать!"
    return menu_text

def format_toppings_menu():
    """Форматирует меню топпингов"""
    menu_text = "🥓 *ДОПОЛНИТЕЛЬНЫЕ ТОППИНГИ:*\n\n"
    
    categories = {}
    for name, details in TOPPINGS_MENU.items():
        category = details['category']
        if category not in categories:
            categories[category] = []
        categories[category].append((name, details))
    
    for category, items in categories.items():
        menu_text += f"*{category.upper()}:*\n"
        for name, details in items:
            menu_text += f"• {name.capitalize()} - ${details['price']} ({details['desc']})\n"
        menu_text += "\n"
    
    menu_text += "Можно добавить несколько топпингов. Напишите через запятую!"
    return menu_text

def format_desserts_menu():
    """Форматирует меню десертов"""
    menu_text = "🍭 *НАШИ ДЕСЕРТЫ:*\n\n"
    for name, details in DESSERTS_MENU.items():
        menu_text += f"• *{name.capitalize()}* - ${details['price']}"
        if 'weight' in details:
            menu_text += f" ({details['weight']})"
        menu_text += f"\n  _{details['desc']}_\n"
        
        if 'flavors' in details:
            menu_text += f"  Варианты: {', '.join(details['flavors'])}\n"
        elif 'quantity' in details:
            menu_text += f"  В порции: {details['quantity']} шт\n"
        
        menu_text += "\n"
    
    menu_text += "Хотите завершить трапезу сладким? 😋"
    return menu_text

def format_drink_menu():
    """Форматирует меню напитков"""
    menu_text = "🍷 *НАШИ НАПИТКИ:*\n\n"
    for name, details in DRINK_MENU.items():
        sizes_text = ", ".join([f"{size} (${price})" for size, price in details['sizes'].items()])
        menu_text += f"• *{name.capitalize()}* ({details['type']}, {details['temp']}): {sizes_text}\n"
        
        if 'flavors' in details:
            menu_text += f"  Вкусы: {', '.join(details['flavors'])}\n"
        
        menu_text += "\n"
    
    menu_text += "Напишите 'хочу колу', 'давай пепси' или просто 'кола 0.5л'"
    return menu_text

def search_wikipedia(query, lang='en'):
    """Ищет информацию в Википедии"""
    try:
        if query == "time":
            return f"Текущее время: {datetime.now().strftime('%H:%M')}"
        
        if query == "1617 number":
            return "1617 — натуральное число. 1617 год — невисокосный год, начинающийся в воскресенье по григорианскому календарю."
        
        if query == "photo question":
            return "Отправьте мне фото, и я проанализирую его содержимое с помощью компьютерного зрения."
        
        if query == "dolphin sleep":
            if lang == 'ru':
                return "Дельфины спят особым образом: у них спит только одно полушарие мозга, а второе бодрствует. Это позволяет им продолжать дышать и контролировать свое положение в воде. Такой сон называется однополушарным медленноволновым сном."
            else:
                return "Dolphins sleep with only one brain hemisphere at a time in slow-wave sleep. The other hemisphere remains awake to allow them to continue breathing and maintain awareness of their environment."
        
        if query.startswith("specific:"):
            animal = query.split(":")[1]
            if animal == "mammal":
                return "По фото видно, что это млекопитающее. Для определения точного вида нужны более детальные признаки. Млекопитающие отличаются наличием шерсти, вскармливанием детенышей молоком и теплокровностью."
            elif animal in RUSSIAN_DESCRIPTIONS:
                return RUSSIAN_DESCRIPTIONS[animal]
            else:
                return f"На фото определен объект: '{animal}'. Это общая категория. Для более точной информации можно уточнить: 'Что это за {animal}?'"
        
        if lang == 'ru' and query in RUSSIAN_DESCRIPTIONS:
            return RUSSIAN_DESCRIPTIONS[query]
        
        wikipedia.set_lang(lang)
        
        try:
            result = wikipedia.summary(query, sentences=3)
            return result
        except wikipedia.exceptions.DisambiguationError as e:
            if e.options:
                try:
                    result = wikipedia.summary(e.options[0], sentences=2)
                    return f"{result}\n\n(Также см. другие варианты)"
                except:
                    pass
            return f"Найдено несколько вариантов для '{query}'. Уточните запрос."
        except wikipedia.exceptions.PageError:
            return f"Информация по запросу '{query}' не найдена в Википедии."
            
    except Exception as e:
        logger.error(f"Ошибка Wikipedia: {e}")
        return "Произошла ошибка при поиске информации."

def analyze_image_clarifai(filename):
    """Анализирует изображение через Clarifai API"""
    try:
        if not os.path.exists(filename):
            return "Файл не найден", []
        
        with open(filename, 'rb') as f:
            image_data = f.read()
        
        api_key = CLARIFAI_API_KEY
        if not api_key:
            return "API ключ Clarifai не задан", []
        
        url = "https://api.clarifai.com/v2/models/general-image-recognition/versions/aa7f35c01e0642fda5cf400f543e7c40/outputs"
        
        headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json"
        }
        
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        
        data = {
            "inputs": [
                {
                    "data": {
                        "image": {
                            "base64": encoded_image
                        }
                    }
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            concepts = result['outputs'][0]['data']['concepts']
            
            filtered_concepts = [c for c in concepts if c['value'] > 0.4]
            filtered_concepts.sort(key=lambda x: x['value'], reverse=True)
            
            if filtered_concepts:
                main_concept = filtered_concepts[0]['name'].lower()
                all_concepts = [c['name'].lower() for c in filtered_concepts[:5]]
                
                logger.info(f"Распознано: {main_concept} (другие: {all_concepts[1:]})")
                return main_concept, all_concepts
            else:
                return "неизвестный объект", []
                
        else:
            return f"ошибка {response.status_code}", []
            
    except Exception as e:
        logger.error(f"Ошибка анализа изображения: {e}")
        return "ошибка анализа", []


async def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user_id = update.message.from_user.id
    user_context[user_id] = {'last_photo_object': None, 'all_detected_objects': []}
    
    welcome_text = """
    
    🍕 *Заказ еды:*
    • Я голоден / I'm hungry
    • Хочу пиццу пепперони
    • Давай колу 0.5л
    • /menu - показать меню
    
    📚 *Энциклопедия:*
    • Кто такие хомяки?
    • Расскажи о слонах
    • Как спят дельфины?
    • Что такое ИИ?
    
    📷 *Анализ фото:*
    Отправьте фото для распознавания объектов
    
    🔧 *Другие команды:*
    • /help - помощь
    • /debug - отладочная информация
    
    🐹 *Пишите что хотите - бот поймет!*
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    logger.info(f"Пользователь {user_id} начал диалог")

async def help_command(update: Update, context: CallbackContext):
    """Обработчик команды /help"""
    help_text = """
    🆘 *ПОМОЩЬ ПО КОМАНДАМ*
    
    🍕 *Заказ еды:*
    Просто напишите что хотите:
    • "Я голоден" или "I'm hungry"
    • "Хочу пиццу маргарита"
    • "Пепперони с сыром"
    • "Кола 0.5л" или "Кофе латте"
    • "Тирамису на десерт"
    
    📚 *Вопросы:*
    Спросите о чем угодно:
    • "Кто такие дельфины?"
    • "Что такое искусственный интеллект?"
    • "Расскажи о кошках"
    • "Как спят дельфины?"
    
    📷 *Фотографии:*
    Отправьте фото любого объекта
    
    ⚙️ *Технические команды:*
    • /menu - меню пиццерии
    • /debug - отладочная информация
    • /start - начать заново
    
    💡 *Примеры фраз:*
    • "пепперони"
    • "хочу колу 0.5л"
    • "давай пиццу и кофе"
    • "что такое хомяк?"
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def menu_command(update: Update, context: CallbackContext):
    """Команда /menu для показа меню"""
    await update.message.reply_text(format_pizza_menu(), parse_mode='Markdown')
    time.sleep(0.5)
    await update.message.reply_text(format_toppings_menu(), parse_mode='Markdown')
    time.sleep(0.5)
    await update.message.reply_text(format_desserts_menu(), parse_mode='Markdown')
    time.sleep(0.5)
    await update.message.reply_text(format_drink_menu(), parse_mode='Markdown')

async def debug_command(update: Update, context: CallbackContext):
    """Команда /debug для отладки"""
    user_id = update.message.from_user.id
    
    debug_text = "🐛 *ОТЛАДОЧНАЯ ИНФОРМАЦИЯ*\n\n"
    debug_text += f"*Пользователь:* {user_id}\n"
    debug_text += f"*Время:* {datetime.now().strftime('%H:%M:%S')}\n"
    debug_text += f"*Состояние заказа:* {user_states.get(user_id, 'не начат')}\n"
    debug_text += f"*Контекст энциклопедии:* {user_context.get(user_id, 'нет')}\n\n"
    
    debug_text += "*Тестовые фразы:*\n"
    test_phrases = [
        "I want a pizza",
        "Я голоден",
        "Хочу колу",
        "Давай пепси 0.5л",
        "Show me desserts",
        "Order a cola",
        "Добавь сыр к пицце",
        "Хочу пепперони и тирамису",
        "кофе",
        "сок яблочный"
    ]
    
    for phrase in test_phrases:
        intent = extract_intent_simple(phrase)
        debug_text += f"`{phrase}` → `{intent}`\n"
    
    await update.message.reply_text(debug_text, parse_mode='Markdown')

async def handle_text_message(update: Update, context: CallbackContext):
    """Обработчик текстовых сообщений"""
    user_id = update.message.from_user.id
    user_text = update.message.text
    
    print(f"\n📨 ПОЛЬЗОВАТЕЛЬ [{user_id}]: {user_text}")
    print(f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}")
    
    # Инициализация контекста если нужно
    if user_id not in user_context:
        user_context[user_id] = {'last_photo_object': None, 'all_detected_objects': []}
    
    # Проверяем, не относится ли сообщение к заказу еды
    intent = extract_intent_simple(user_text)
    
    if intent in ['hungry', 'orderPizza', 'orderDessert', 'addTopping', 'wantSomething'] or (intent and intent.startswith('order_')):
        
        print(f"🍕 Обнаружено намерение: {intent}")
        
        # Обработка заказа еды
        if intent == 'hungry':
            await update.message.reply_text(get_hungry_response(), parse_mode='Markdown')
            user_states[user_id] = 'ORDERING'
            user_data[user_id] = {}
            
        elif intent == 'orderPizza' or any(word in user_text.lower() for word in ['пицц', 'пиццу', 'пицца', 'pizza']):
            user_data[user_id] = {'intent': 'orderPizza'}
            user_states[user_id] = 'ADD_INFO_PIZZA'
            
            response = (
                "🐹 *Отлично! Вы хотите заказать пиццу!* 🍕\n\n"
                f"{format_pizza_menu()}\n\n"
                "*Просто напишите название пиццы, которую хотите:*\n"
                "(например: 'пепперони', 'маргарита', 'гавайская')"
            )
            await update.message.reply_text(response, parse_mode='Markdown')
            
        elif intent and intent.startswith('order_'):
            drink_keyword = intent[6:]
            if drink_keyword in DRINK_MENU:
                await update.message.reply_text(
                    f"🥤 *Хотите {drink_keyword}!*\n\n"
                    f"Напишите какой размер:\n"
                    f"{', '.join(DRINK_MENU[drink_keyword]['sizes'].keys())}",
                    parse_mode='Markdown'
                )
                user_states[user_id] = 'ADD_INFO_DRINK_SIZE'
                user_data[user_id] = {'drink_type': drink_keyword}
            else:
                await update.message.reply_text("Не понял какой напиток вы хотите. Используйте /menu чтобы посмотреть меню напитков.")
            
        elif intent == 'orderDessert':
            await update.message.reply_text(format_desserts_menu(), parse_mode='Markdown')
            user_states[user_id] = 'ADD_INFO_DESSERT'
            user_data[user_id] = {'intent': 'orderDessert'}
            
        else:
            await update.message.reply_text(
                "Попробуйте сказать:\n"
                "• 'Я голоден' или 'Хочу есть'\n"
                "• 'Хочу пиццу' или просто 'пепперони'\n"
                "• 'Давай колу' или 'хочу колу 0.5л'\n"
                "• 'Покажи десерты'\n"
                "• Или используйте /menu",
                parse_mode='Markdown'
            )
            
        return
    
    # Если это не заказ еды, то обрабатываем как энциклопедический запрос
    text_lower = user_text.lower()
    
    # Простая проверка русских символов для определения языка
    ru_count = len(re.findall(r'[а-яА-ЯёЁ]', user_text))
    en_count = len(re.findall(r'[a-zA-Z]', user_text))
    lang = 'ru' if ru_count > en_count else 'en'
    
    print(f"🌐 Язык: {lang.upper()}")
    
    # Простой извлечение ключевой фразы
    key_phrase = None
    
    if 'время' in text_lower or 'time' in text_lower:
        key_phrase = "time"
    elif '1617' in text_lower:
        key_phrase = "1617 number"
    elif 'вопросительный знак' in text_lower or ('?' in user_text and 'что такое' in text_lower):
        key_phrase = "вопросительный знак"
    elif 'как спят дельфины' in text_lower or 'dolphins sleep' in text_lower:
        key_phrase = "dolphin sleep"
    elif 'кто на фото' in text_lower or 'что на фото' in text_lower:
        key_phrase = "photo question"
    elif 'хомяк' in text_lower:
        key_phrase = "хомяк"
    elif 'ежик' in text_lower or 'ёжик' in text_lower:
        key_phrase = "ежик"
    elif 'собака' in text_lower:
        key_phrase = "собака"
    elif 'кошка' in text_lower or 'кот' in text_lower:
        key_phrase = "кошка"
    elif 'слон' in text_lower:
        key_phrase = "слон"
    elif 'дельфин' in text_lower:
        key_phrase = "дельфин"
    elif 'лев' in text_lower:
        key_phrase = "лев"
    elif 'тигр' in text_lower:
        key_phrase = "тигр"
    elif 'млекопитающ' in text_lower:
        key_phrase = "млекопитающее"
    elif 'ии' in text_lower or 'искусственный интеллект' in text_lower:
        key_phrase = "ии"
    
    if not key_phrase:
        # Если не нашли ключевую фразу, ищем в русских описаниях
        for phrase in RUSSIAN_DESCRIPTIONS.keys():
            if phrase in text_lower:
                key_phrase = phrase
                break
    
    if not key_phrase:
        await update.message.reply_text("Не понял ваш запрос. Пожалуйста, уточните вопрос.")
        print(f"❌ Не удалось извлечь ключевую фразу")
        return
    
    print(f"🔑 Ключевая фраза: '{key_phrase}'")
    
    if key_phrase == "time":
        current_time = datetime.now().strftime("%H:%M")
        await update.message.reply_text(f"⏰ Текущее время: {current_time}")
        print(f"⏰ Ответ: {current_time}")
        return
    
    search_lang = 'ru' if lang == 'ru' else 'en'
    
    search_indicator = f"🔍 *Ищу:* {key_phrase}"
    if key_phrase.startswith("specific:"):
        animal = key_phrase.split(":")[1]
        search_indicator = f"🔍 *Уточняю информацию о:* {animal}"
    
    await update.message.reply_text(search_indicator, parse_mode='Markdown')
    
    result = search_wikipedia(key_phrase, search_lang)
    
    print(f"📖 Результат: {result[:100]}...")
    
    await update.message.reply_text(result, parse_mode='Markdown')

async def handle_photo_message(update: Update, context: CallbackContext):
    """Обработчик фотографий"""
    user_id = update.message.from_user.id
    
    print(f"\n📸 ПОЛЬЗОВАТЕЛЬ [{user_id}]: отправил фото")
    print(f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}")
    
    await update.message.reply_text("📸 *Анализирую изображение...*", parse_mode='Markdown')
    
    temp_dir = Path(tempfile.gettempdir()) / "bot_images"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        filename = temp_dir / f"photo_{user_id}_{datetime.now().strftime('%H%M%S')}.jpg"
        
        print(f"💾 Скачиваю фото: {filename}")
        await photo_file.download_to_drive(filename)
        
        file_size = os.path.getsize(filename) / 1024
        print(f"📊 Размер файла: {file_size:.1f} KB")
        
        print("🤖 Анализ через Clarifai...")
        main_object, all_objects = analyze_image_clarifai(str(filename))
        
        print(f"✅ Распознано: {main_object}")
        if all_objects:
            print(f"📋 Все объекты: {', '.join(all_objects)}")
        
        try:
            os.remove(filename)
            print(f"🗑️ Файл удален")
        except:
            pass
        
        if main_object.startswith("ошибка"):
            await update.message.reply_text(f"❌ {main_object}")
            print(f"❌ Ошибка распознавания")
            return
        
        if main_object == "неизвестный объект":
            await update.message.reply_text("🤔 Не удалось распознать объекты на фото. Попробуйте другое изображение с более четким объектом.")
            print(f"🤔 Неизвестный объект")
            return
        
        user_context[user_id]['last_photo_object'] = main_object
        user_context[user_id]['all_detected_objects'] = all_objects
        
        if main_object in RUSSIAN_DESCRIPTIONS:
            response_text = f"🖼️ *На фото распознан:* {main_object}\n\n{RUSSIAN_DESCRIPTIONS[main_object]}"
        else:
            wikipedia.set_lang('ru')
            try:
                wiki_result = wikipedia.summary(main_object, sentences=2)
                response_text = f"🖼️ *На фото распознан:* {main_object}\n\n{wiki_result}"
            except:
                response_text = f"🖼️ *На фото распознан:* {main_object}\n\nЭто объект категории '{main_object}'. Для получения подробной информации задайте уточняющий вопрос."
        
        if len(all_objects) > 1:
            other_objects = all_objects[1:min(4, len(all_objects))]
            response_text += f"\n\n👁️ *Также на фото:* {', '.join(other_objects)}"
        
        response_text += f"\n\n💡 *Можно уточнить:*\n• «Какое именно это {main_object}?»\n• «Расскажи подробнее»\n• «Что это за {main_object}?»"
        
        print(f"📤 Отправляю ответ")
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при обработке изображения")
        logger.error(f"Ошибка обработки фото: {e}")

async def error_handler(update: Update, context: CallbackContext):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    try:
        await update.message.reply_text(f"❌ Произошла ошибка: {context.error}")
    except:
        pass


def main():
    """Запуск бота"""
    
    print("\n Журнал работы:")
    
    # Проверяем токен
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "8230051824:AAH8k81yxhlUNTO-th6SoNMXbXwENYdlmao":
        print("Замените TELEGRAM_TOKEN в файле bot_light.py на свой токен")
    
    try:
        # Создаем Application (python-telegram-bot==22.5)
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("menu", menu_command))
        application.add_handler(CommandHandler("debug", debug_command))
        
        # Обработчики сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        print("✅ Бот запущен успешно!")
        print("📱 Команды бота:")
        print("   /start - начать работу")
        print("   /help - помощь по командам")
        print("   /menu - меню пиццерии")
        print("   /debug - отладочная информация")
        print("\n🐹 Примеры фраз для бота:")
        print("   • 'Я голоден'")
        print("   • 'Хочу пиццу пепперони'")
        print("   • 'Давай колу 0.5л'")
        print("   • 'Кто такие дельфины?'")
        print("\n⏹️ Для остановки: Ctrl+C")
        print("-" * 40)
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        print(f"\n КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == "__main__":
    main()

import os
import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from excel_handler import TariffHandler
from ocr_processor import ClaudeProcessor

# Токен бота (будет задан через переменные окружения)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация обработчиков
tariff_handler = TariffHandler()
claude_processor = ClaudeProcessor()

# Хранение контекста пользователей
user_contexts = {}

class UserContext:
    def __init__(self):
        self.vehicle_data = {}
        self.waiting_for = None  # 'engine_volume', 'brand', 'model'
        self.conversation_state = 'idle'  # 'idle', 'collecting_data', 'confirming'
        self.media_group_photos = []
        
    def reset(self):
        self.vehicle_data = {}
        self.waiting_for = None
        self.conversation_state = 'idle'
        self.media_group_photos = []

def get_user_context(user_id: int) -> UserContext:
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext()
    return user_contexts[user_id]

@dp.message(Command('start'))
async def start_command(message: types.Message):
    """Команда /start"""
    welcome_text = """
🚗 Привет! Я помогу рассчитать стоимость ОСЦПВ (автогражданки).

💬 Просто напиши мне:
• "BMW X3 2000 см³" 
• "Toyota Camry 1800"
• Или пришли фото техпаспорта

🔍 Я умею понимать обычную речь - пиши как удобно!

Что будем рассчитывать?
"""
    context = get_user_context(message.from_user.id)
    context.reset()
    await message.answer(welcome_text)

@dp.message(Command('help'))
async def help_command(message: types.Message):
    """Команда /help"""
    help_text = """
ℹ️ Как пользоваться ботом:

💭 Пиши естественно:
• "хочу рассчитать для БМВ Х3"
• "объем двигателя 1998"
• "это дизель 2.0 литра"

📸 Или пришли фото техпаспорта - я сам все найду

🏷️ Покрытие ОСЦПВ:
• Жизнь и здоровье: до 5 000 000 грн
• Имущество: до 1 250 000 грн

Просто начни писать - я пойму! 😊
"""
    await message.answer(help_text)

@dp.message(lambda message: message.media_group_id)
async def process_media_group(message: types.Message):
    """Обработка группы фотографий"""
    context = get_user_context(message.from_user.id)
    
    # Собираем фото из медиагруппы
    if not hasattr(context, 'media_group_buffer'):
        context.media_group_buffer = []
    
    context.media_group_buffer.append(message.photo[-1])
    
    # Ждем 2 секунды, чтобы собрать все фото
    await asyncio.sleep(2)
    
    if len(context.media_group_buffer) > 0:
        await process_multiple_photos(message, context.media_group_buffer)
        context.media_group_buffer = []

@dp.message(lambda message: message.content_type == 'photo')
async def process_single_photo(message: types.Message):
    """Обработка одного фото"""
    context = get_user_context(message.from_user.id)
    processing_msg = await message.answer("🔍 Анализирую документ...")
    
    try:
        # Скачиваем фото
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        file_data = await bot.download_file(file_info.file_path)
        
        # Анализируем через Claude
        result = await claude_processor.analyze_document(file_data.read())
        
        if "error" in result:
            await processing_msg.edit_text(f"😔 {result['error']}\n\nПопробуй написать данные текстом или пришли более четкое фото.")
            return
        
        # Сохраняем данные
        context.vehicle_data.update(result)
        context.conversation_state = 'collecting_data'
        
        # Показываем что нашли и проверяем что нужно еще
        response = format_recognized_data(result)
        missing = get_missing_critical_data(result)
        
        if missing:
            response += f"\n\n❓ {missing}"
            context.waiting_for = get_next_required_field(result)
        else:
            # Все данные есть, рассчитываем
            response += "\n\n" + calculate_and_format_result(context.vehicle_data)
            context.reset()
        
        await processing_msg.edit_text(response)
        
    except Exception as e:
        await processing_msg.edit_text(f"😔 Что-то пошло не так: {str(e)}\n\nПопробуй еще раз или напиши данные текстом.")

async def process_multiple_photos(message: types.Message, photos: list):
    """Обработка нескольких фото"""
    context = get_user_context(message.from_user.id)
    processing_msg = await message.answer("🔍 Анализирую документы...")
    
    try:
        # Скачиваем все фото
        images = []
        for photo in photos:
            file_info = await bot.get_file(photo.file_id)
            file_data = await bot.download_file(file_info.file_path)
            images.append(file_data.read())
        
        # Анализируем через Claude
        result = await claude_processor.analyze_multiple_images(images)
        
        if "error" in result:
            await processing_msg.edit_text(f"😔 {result['error']}\n\nПопробуй написать данные текстом.")
            return
        
        # Сохраняем данные
        context.vehicle_data.update(result)
        context.conversation_state = 'collecting_data'
        
        # Показываем результат
        response = format_recognized_data(result)
        missing = get_missing_critical_data(result)
        
        if missing:
            response += f"\n\n❓ {missing}"
            context.waiting_for = get_next_required_field(result)
        else:
            response += "\n\n" + calculate_and_format_result(context.vehicle_data)
            context.reset()
        
        await processing_msg.edit_text(response)
        
    except Exception as e:
        await processing_msg.edit_text(f"😔 Ошибка обработки: {str(e)}")

@dp.message()
async def process_text_message(message: types.Message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    context = get_user_context(user_id)
    text = message.text.strip()
    
    # Проверяем на вежливые фразы и благодарности
    if is_polite_response(text):
        await handle_polite_response(message, context, text)
        return
    
    # Проверяем на команды начала нового расчета
    if is_new_calculation_request(text):
        context.reset()
        await message.answer("🚗 Отлично! Какой автомобиль будем рассчитывать?")
        return
    
    # Основная логика обработки
    if context.conversation_state == 'idle':
        # Начинаем новый расчет
        await start_new_calculation(message, context, text)
    else:
        # Продолжаем сбор данных
        await continue_data_collection(message, context, text)

async def start_new_calculation(message: types.Message, context: UserContext, text: str):
    """Начинаем новый расчет"""
    # Парсим входящий текст
    parsed_data = claude_processor.parse_text_input(text)
    context.vehicle_data.update({k: v for k, v in parsed_data.items() if v})
    context.conversation_state = 'collecting_data'
    
    # Проверяем что получили
    if parsed_data.get('engine_volume'):
        # Есть объем - можем рассчитывать
        result = calculate_and_format_result(context.vehicle_data)
        await message.answer(result)
        context.reset()
    else:
        # Нужны дополнительные данные
        response = format_recognized_data(context.vehicle_data)
        missing = get_missing_critical_data(context.vehicle_data)
        response += f"\n\n❓ {missing}"
        context.waiting_for = 'engine_volume'
        await message.answer(response)

async def continue_data_collection(message: types.Message, context: UserContext, text: str):
    """Продолжаем сбор данных"""
    # Извлекаем новые данные из сообщения
    context.vehicle_data = claude_processor.extract_missing_data(context.vehicle_data, text)
    
    # Проверяем что теперь есть
    if context.vehicle_data.get('engine_volume'):
        # Достаточно данных для расчета
        result = calculate_and_format_result(context.vehicle_data)
        await message.answer(result)
        context.reset()
    else:
        # Все еще нужен объем двигателя
        response = "🤔 Понял"
        if context.vehicle_data.get('brand') or context.vehicle_data.get('model'):
            response += f", {format_current_data(context.vehicle_data)}"
        response += ".\n\n❓ Какой объем двигателя в см³?"
        await message.answer(response)

def is_polite_response(text: str) -> bool:
    """Проверяет на вежливые ответы"""
    polite_words = ['спасибо', 'благодарю', 'дякую', 'ок', 'хорошо', 'отлично', 'понятно', 'ясно', 'да', 'нет']
    return any(word in text.lower() for word in polite_words)

async def handle_polite_response(message: types.Message, context: UserContext, text: str):
    """Обрабатывает вежливые ответы"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['спасибо', 'благодарю', 'дякую']):
        await message.answer("😊 Пожалуйста! Обращайся, если нужен еще расчет.")
        context.reset()
    elif any(word in text_lower for word in ['ок', 'хорошо', 'отлично', 'понятно', 'ясно']):
        if context.waiting_for:
            await message.answer("👍 Жду нужные данные!")
        else:
            await message.answer("😊 Что будем рассчитывать?")
    elif 'да' in text_lower:
        await message.answer("👍 Продолжаем!")
    elif 'нет' in text_lower:
        await message.answer("🤔 Что именно не так? Давай исправим!")

def is_new_calculation_request(text: str) -> bool:
    """Проверяет запрос нового расчета"""
    new_calc_words = ['новый', 'еще', 'другой', 'рассчитать', 'расчет', 'другая машина', 'другое авто']
    return any(word in text.lower() for word in new_calc_words)

def format_recognized_data(data: dict) -> str:
    """Форматирует распознанные данные"""
    parts = []
    if data.get('brand'):
        parts.append(data['brand'])
    if data.get('model'):
        parts.append(data['model'])
    if data.get('year'):
        parts.append(f"{data['year']} года")
    
    if parts:
        result = f"🔍 Понял: {' '.join(parts)}"
        if data.get('engine_volume'):
            result += f", {data['engine_volume']} см³"
        return result
    elif data.get('engine_volume'):
        return f"🔍 Объем двигателя: {data['engine_volume']} см³"
    else:
        return "🔍 Анализирую данные..."

def format_current_data(data: dict) -> str:
    """Форматирует текущие данные"""
    parts = []
    if data.get('brand'):
        parts.append(data['brand'])
    if data.get('model'):
        parts.append(data['model'])
    return ' '.join(parts) if parts else "автомобиль"

def get_missing_critical_data(data: dict) -> str:
    """Определяет какие критичные данные отсутствуют"""
    if not data.get('engine_volume'):
        return "Какой объем двигателя в см³?"
    return ""

def get_next_required_field(data: dict) -> str:
    """Определяет следующее требуемое поле"""
    if not data.get('engine_volume'):
        return 'engine_volume'
    return None

def calculate_and_format_result(vehicle_data: dict) -> str:
    """Рассчитывает и форматирует результат"""
    try:
        engine_volume = vehicle_data.get('engine_volume')
        if not engine_volume:
            return "❌ Не хватает данных для расчета. Укажи объем двигателя."
        
        # Определяем категорию
        category = tariff_handler.get_car_category(engine_volume)
        price = tariff_handler.get_price(category, age_over_30=True)
        
        if not price:
            return "❌ Не удалось определить тариф для данного объема двигателя."
        
        # Форматируем название автомобиля
        brand = vehicle_data.get('brand', 'Автомобиль')
        model = vehicle_data.get('model', '')
        year = vehicle_data.get('year', '')
        
        # Преобразуем объем в литры
        volume_liters = f"{float(engine_volume)/1000:.3f} л"
        
        vehicle_name = f"{brand} {model} {year}".strip()
        vehicle_name += f", {volume_liters} бензин"
        
        result = f"""✅ Ціна автоцивілки (ОСЦПВ) для {vehicle_name}:
🩺 Покриття: життя і здоров'я потерпілих до 5 000 000 грн
🚗 Покриття: майно потерпілих до 1 250 000 грн
👤 Діє для водіїв віком: більше 30 років
💰 Ціна: {price} грн"""
        
        return result
        
    except Exception as e:
        return f"❌ Ошибка расчета: {str(e)}"

# Главная функция для Vercel
def handler(request, context=None):
    """Главная функция для Vercel"""
    import asyncio
    import json
    
    try:
        # Получаем тело запроса
        if hasattr(request, 'get_json'):
            # Flask-style request
            body = request.get_json()
        elif hasattr(request, 'json'):
            # FastAPI-style request
            body = request.json
        else:
            # Raw request
            if hasattr(request, 'body'):
                body_str = request.body
            else:
                body_str = request
            
            if isinstance(body_str, str):
                body = json.loads(body_str)
            else:
                body = body_str
        
        # Создаем Update объект
        update = types.Update(**body)
        
        # Запускаем обработку
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(dp.feed_update(bot, update))
        loop.close()
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "ok"})
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }

# Для совместимости с разными платформами
app = handler

# Для локального тестирования
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        await dp.start_polling(bot)
    
    asyncio.run(main())

import os
import re
import json
import asyncio
import aiohttp
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

class WebhookHandler(BaseHTTPRequestHandler):
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN', '')
        
        # Тарифы
        self.tariffs = {
            'B1': {'name': 'до 1600 см³', 'price': 1959},
            'B2': {'name': '1601-2000 см³', 'price': 2527},
            'B3': {'name': '2001-3000 см³', 'price': 2585},
            'B4': {'name': 'свыше 3000 см³', 'price': 3349}
        }
        
        self.car_brands = [
            'BMW', 'MERCEDES', 'AUDI', 'VOLKSWAGEN', 'TOYOTA', 'HONDA', 'NISSAN',
            'HYUNDAI', 'KIA', 'FORD', 'CHEVROLET', 'OPEL', 'PEUGEOT', 'RENAULT',
            'LEXUS', 'DAEWOO', 'MAZDA', 'SUBARU', 'MITSUBISHI', 'LADA'
        ]
    
    def get_category(self, engine_volume):
        try:
            volume = int(engine_volume)
            if volume <= 1600:
                return 'B1'
            elif volume <= 2000:
                return 'B2'
            elif volume <= 3000:
                return 'B3'
            else:
                return 'B4'
        except:
            return 'B2'
    
    def parse_text(self, text):
        text = text.upper().strip()
        result = {'brand': None, 'model': None, 'engine_volume': None}
        
        # Поиск объема двигателя
        volume_patterns = [
            r'(\d{3,4})\s*(?:СМ|CM|КУБОВ|КУБ)',
            r'(\d{1,2})[.,](\d{3})',
            r'(\d{3,4})(?=\s|$)'
        ]
        
        for pattern in volume_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    volume = match.group(1) + match.group(2)
                else:
                    volume = match.group(1)
                
                if 500 <= int(volume) <= 8000:
                    result['engine_volume'] = volume
                    break
        
        # Поиск марки
        for brand in self.car_brands:
            if brand in text:
                result['brand'] = brand
                break
        
        return result
    
    def format_result(self, data):
        engine_volume = data.get('engine_volume')
        if not engine_volume:
            return "❓ Не указан объем двигателя. Напиши например: 'BMW X3 1998 см³'"
        
        category = self.get_category(engine_volume)
        price = self.tariffs[category]['price']
        
        brand = data.get('brand', 'Автомобиль')
        model = data.get('model', '')
        volume_liters = f"{float(engine_volume)/1000:.3f} л"
        
        vehicle_name = f"{brand} {model}".strip()
        if volume_liters:
            vehicle_name += f", {volume_liters} бензин"
        
        return f"""✅ Ціна автоцивілки (ОСЦПВ) для {vehicle_name}:
🩺 Покриття: життя і здоров'я потерпілих до 5 000 000 грн
🚗 Покриття: майно потерпілих до 1 250 000 грн
👤 Діє для водіїв віком: більше 30 років
💰 Ціна: {price} грн"""
    
    async def send_message(self, chat_id, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                return await response.json()
    
    async def process_update(self, update_data):
        try:
            message = update_data.get('message', {})
            if not message:
                return
            
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            if text == '/start':
                response = """🚗 Привет! Я помогу рассчитать ОСЦПВ.

💬 Напиши данные автомобиля:
• "BMW X3 1998 см³"
• "Toyota Camry 1800"

Что рассчитываем?"""
            
            elif text == '/help':
                response = """ℹ️ Как использовать:

💭 Пиши естественно:
• "BMW X3 объем 2000"
• "хочу для Тойоты, 1800 кубов"

Бот понимает обычную речь! 😊"""
            
            else:
                parsed = self.parse_text(text)
                
                if parsed['engine_volume']:
                    response = self.format_result(parsed)
                elif any(word in text.lower() for word in ['спасибо', 'дякую']):
                    response = "😊 Пожалуйста! Обращайтесь для новых расчетов."
                else:
                    if parsed['brand']:
                        response = f"🔍 Понял: {parsed['brand']}\n\n❓ Какой объем двигателя в см³?"
                    else:
                        response = "🤔 Не понял. Напиши например: 'BMW X3 1998 см³'"
            
            await self.send_message(chat_id, response)
            
        except Exception as e:
            print(f"Ошибка: {e}")

# Глобальный экземпляр
webhook_handler = WebhookHandler()

def handler(request, response):
    """Главная функция для Vercel API"""
    try:
        # Получаем тело запроса
        body = request.get('body', '{}')
        if isinstance(body, str):
            update_data = json.loads(body)
        else:
            update_data = body
        
        # Обрабатываем асинхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(webhook_handler.process_update(update_data))
        loop.close()
        
        return response.status(200).json({"status": "ok"})
        
    except Exception as e:
        print(f"Handler error: {e}")
        return response.status(500).json({"error": str(e)})

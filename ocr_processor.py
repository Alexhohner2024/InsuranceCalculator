import base64
import re
import json
import os
from typing import Optional, Dict, Any

# Временно закомментируем Anthropic до решения проблем с версией
# from anthropic import Anthropic

class ClaudeProcessor:
    def __init__(self):
        # Временно отключаем Claude API
        self.client = None
        print("Claude API временно отключен - используем только текстовый парсинг")
        
        # Известные марки автомобилей для валидации
        self.car_brands = [
            'BMW', 'MERCEDES', 'AUDI', 'VOLKSWAGEN', 'TOYOTA', 'HONDA', 'NISSAN',
            'HYUNDAI', 'KIA', 'FORD', 'CHEVROLET', 'OPEL', 'PEUGEOT', 'RENAULT',
            'CITROEN', 'FIAT', 'SKODA', 'SEAT', 'MAZDA', 'SUBARU', 'MITSUBISHI',
            'LEXUS', 'INFINITI', 'ACURA', 'VOLVO', 'SAAB', 'JAGUAR', 'LAND ROVER',
            'PORSCHE', 'MINI', 'ALFA ROMEO', 'LADA', 'VAZ', 'GAZ', 'UAZ', 'ZAZ',
            'DAEWOO', 'SUZUKI', 'ISUZU', 'DACIA', 'LANCIA', 'CHERY', 'GEELY'
        ]
    
    def encode_image(self, image_bytes: bytes) -> str:
        """Кодирует изображение в base64"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    async def analyze_document(self, image_bytes: bytes) -> Dict[str, Any]:
        """Временно отключен анализ фото - используем только текст"""
        return {
            "error": "Анализ фото временно недоступен. Пожалуйста, введите данные текстом: 'BMW X3 1998 см³'"
        }
    
    async def analyze_multiple_images(self, images: list) -> Dict[str, Any]:
        """Анализ нескольких изображений - временно отключен"""
        return {
            "error": "Анализ фото временно недоступен. Введите данные текстом: 'марка модель объем_двигателя'"
        }
    
    def parse_text_input(self, text: str) -> Dict[str, Any]:
        """Парсит текстовый ввод пользователя"""
        text = text.upper().strip()
        result = {
            "brand": None,
            "model": None,
            "year": None,
            "engine_volume": None,
            "source": "text_input"
        }
        
        # Поиск объема двигателя
        volume_patterns = [
            r'(\d{3,4})\s*(?:СМ|CM|КУБОВ|КУБ)',  # 1998 см³, 2000 кубов
            r'(\d{1,2})[.,](\d{3})\s*(?:Л|L)',    # 1.998 л, 2,000 л
            r'(\d{3,4})\s*(?:СС|CC)',             # 1998 сс
            r'(\d{3,4})(?=\s|$)'                  # просто цифры 1998
        ]
        
        for pattern in volume_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:  # для паттерна с точкой
                    volume = match.group(1) + match.group(2)
                else:
                    volume = match.group(1)
                
                # Проверяем, что это разумный объем двигателя
                if 500 <= int(volume) <= 8000:
                    result["engine_volume"] = volume
                    break
        
        # Поиск марки автомобиля
        for brand in self.car_brands:
            if brand in text:
                result["brand"] = brand
                # Ищем модель после марки
                brand_index = text.find(brand)
                text_after_brand = text[brand_index + len(brand):].strip()
                model_match = re.search(r'^[А-ЯA-Z0-9\-]+', text_after_brand)
                if model_match:
                    potential_model = model_match.group()
                    # Исключаем года и объемы
                    if not re.match(r'^\d{3,4}$', potential_model):
                        result["model"] = potential_model
                break
        
        # Поиск года
        year_match = re.search(r'\b(19[8-9]\d|20[0-2]\d)\b', text)
        if year_match:
            result["year"] = year_match.group(1)
        
        return result
    
    def extract_missing_data(self, current_data: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Извлекает недостающие данные из сообщения пользователя"""
        message_data = self.parse_text_input(user_message)
        
        # Обновляем текущие данные новыми
        for key, value in message_data.items():
            if value and (not current_data.get(key) or key == "engine_volume"):
                current_data[key] = value
        
        return current_data

import base64
import re
import json
from anthropic import Anthropic
import os
from typing import Optional, Dict, Any

class ClaudeProcessor:
    def __init__(self):
        # Инициализация Claude API
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            # Не вызываем ошибку при инициализации, проверим позже
            self.client = None
        else:
            try:
                self.client = Anthropic(api_key=api_key)
            except Exception as e:
                print(f"Ошибка инициализации Anthropic: {e}")
                self.client = None
        
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
        """Анализирует документ через Claude API"""
        if not self.client:
            return {"error": "Claude API не инициализирован. Проверьте ANTHROPIC_API_KEY."}
        
        try:
            # Кодируем изображение
            base64_image = self.encode_image(image_bytes)
            
            # Создаем промпт для анализа техпаспорта
            prompt = """
Проанализируй украинский техпаспорт на изображении и извлеки данные о транспортном средстве.

Верни результат в формате JSON с полями:
{
  "brand": "марка автомобиля (например BMW, TOYOTA)",
  "model": "модель (например X3, Camry)", 
  "year": "год выпуска (4 цифры)",
  "engine_volume": "объем двигателя в см³ (только цифры, например 1998)",
  "confidence": "уверенность в правильности данных от 0 до 100"
}

Важные моменты:
- Ищи объем двигателя рядом с полями P.1, Capacity, "см³", "см3"
- Марка может быть в полях D.1, Make, Марка
- Модель в полях D.2, Type, Тип
- Год в полях B.2, Year, Рік випуску
- Если какое-то поле не найдено, укажи null
- Объем двигателя критично важен для расчета страховки

Верни только JSON, без дополнительного текста.
            """
            
            # Отправляем запрос к Claude
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # Парсим ответ
            response_text = response.content[0].text.strip()
            
            # Извлекаем JSON из ответа
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                return {"error": "Не удалось получить структурированный ответ от API"}
                
        except json.JSONDecodeError as e:
            return {"error": f"Ошибка парсинга JSON: {str(e)}"}
        except Exception as e:
            return {"error": f"Ошибка API: {str(e)}"}
    
    async def analyze_multiple_images(self, images: list) -> Dict[str, Any]:
        """Анализ нескольких изображений (обе стороны техпаспорта)"""
        all_data = {}
        best_confidence = 0
        
        for i, image_bytes in enumerate(images):
            result = await self.analyze_document(image_bytes)
            
            if "error" not in result:
                confidence = result.get("confidence", 0)
                if confidence > best_confidence:
                    all_data = result
                    best_confidence = confidence
                else:
                    # Дополняем данные из других фото
                    for key, value in result.items():
                        if key != "confidence" and value and not all_data.get(key):
                            all_data[key] = value
        
        return all_data if all_data else {"error": "Не удалось извлечь данные ни с одного изображения"}
    
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

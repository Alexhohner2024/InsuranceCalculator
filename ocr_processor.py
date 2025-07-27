
import cv2
import pytesseract
import re
from PIL import Image
import numpy as np

class OCRProcessor:
    def __init__(self):
        # Настройки Tesseract для украинского и русского языков
        self.tesseract_config = '--oem 3 --psm 6 -l ukr+rus+eng'
        
        # Известные марки автомобилей для валидации
        self.car_brands = [
            'BMW', 'MERCEDES', 'AUDI', 'VOLKSWAGEN', 'TOYOTA', 'HONDA', 'NISSAN',
            'HYUNDAI', 'KIA', 'FORD', 'CHEVROLET', 'OPEL', 'PEUGEOT', 'RENAULT',
            'CITROEN', 'FIAT', 'SKODA', 'SEAT', 'MAZDA', 'SUBARU', 'MITSUBISHI',
            'LEXUS', 'INFINITI', 'ACURA', 'VOLVO', 'SAAB', 'JAGUAR', 'LAND ROVER',
            'PORSCHE', 'MINI', 'ALFA ROMEO', 'LADA', 'VAZ', 'GAZ', 'UAZ', 'ZAZ',
            'DAEWOO', 'SUZUKI', 'ISUZU', 'DACIA', 'LANCIA'
        ]
    
    def preprocess_image(self, image_bytes):
        """Предобработка изображения для улучшения OCR"""
        try:
            # Конвертируем bytes в numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Конвертируем в серый
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Увеличиваем контрастность
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Убираем шум
            denoised = cv2.medianBlur(enhanced, 3)
            
            return denoised
        except Exception as e:
            print(f"Ошибка предобработки: {e}")
            return None
    
    def extract_text(self, image_bytes):
        """Извлекает текст из изображения"""
        try:
            processed_img = self.preprocess_image(image_bytes)
            if processed_img is None:
                return ""
            
            # OCR распознавание
            text = pytesseract.image_to_string(processed_img, config=self.tesseract_config)
            return text.upper()  # Приводим к верхнему регистру для удобства
        except Exception as e:
            print(f"Ошибка OCR: {e}")
            return ""
    
    def extract_vehicle_data(self, text):
        """Извлекает данные о ТС из распознанного текста"""
        data = {
            'brand': None,
            'model': None,
            'year': None,
            'engine_volume': None,
            'fuel_type': None
        }
        
        # Поиск года (4 цифры от 1990 до 2025)
        year_match = re.search(r'\b(19[9][0-9]|20[0-2][0-9])\b', text)
        if year_match:
            data['year'] = year_match.group(1)
        
        # Поиск объема двигателя
        # Варианты: "1998", "1.998", "1,998" + "см3" или рядом с "P.1"
        engine_patterns = [
            r'(\d{3,4})\s*СМ',  # 1998 СМ
            r'(\d{1,2})[.,](\d{3})\s*СМ',  # 1.998 СМ или 1,998 СМ
            r'P\.1\s*(\d{3,4})',  # P.1 1998
            r'CAPACITY.*?(\d{3,4})',  # после слова CAPACITY
            r'(\d{3,4})\s*CM'  # английский вариант
        ]
        
        for pattern in engine_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:  # для паттерна с точкой/запятой
                    data['engine_volume'] = match.group(1) + match.group(2)
                else:
                    data['engine_volume'] = match.group(1)
                break
        
        # Поиск марки автомобиля
        for brand in self.car_brands:
            if brand in text:
                data['brand'] = brand
                break
        
        # Поиск модели (после марки или в определенных полях)
        if data['brand']:
            # Ищем текст после марки
            brand_index = text.find(data['brand'])
            if brand_index != -1:
                text_after_brand = text[brand_index + len(data['brand']):brand_index + len(data['brand']) + 50]
                model_match = re.search(r'([A-Z0-9]{2,15})', text_after_brand.strip())
                if model_match:
                    potential_model = model_match.group(1)
                    # Исключаем года и объемы
                    if not re.match(r'^(19|20)\d{2}$', potential_model) and not re.match(r'^\d{3,4}$', potential_model):
                        data['model'] = potential_model
        
        # Поиск типа топлива
        fuel_patterns = [
            r'БЕНЗИН', r'DIESEL', r'ДИЗЕЛЬ', r'ЕЛЕКТРО', r'ELECTRIC', r'ГАЗ', r'LPG'
        ]
        for pattern in fuel_patterns:
            if re.search(pattern, text):
                if 'БЕНЗИН' in pattern or 'PETROL' in pattern:
                    data['fuel_type'] = 'бензин'
                elif 'ДИЗЕЛЬ' in pattern or 'DIESEL' in pattern:
                    data['fuel_type'] = 'дизель'
                elif 'ЕЛЕКТРО' in pattern or 'ELECTRIC' in pattern:
                    data['fuel_type'] = 'электро'
                elif 'ГАЗ' in pattern or 'LPG' in pattern:
                    data['fuel_type'] = 'газ'
                break
        
        return data
    
    def process_document_photo(self, image_bytes):
        """Основная функция обработки фото документа"""
        try:
            # Извлекаем текст
            text = self.extract_text(image_bytes)
            if not text:
                return None, "Не удалось распознать текст с изображения"
            
            # Извлекаем данные о ТС
            vehicle_data = self.extract_vehicle_data(text)
            
            # Проверяем, что получили хотя бы минимальные данные
            if not vehicle_data['engine_volume'] and not vehicle_data['brand']:
                return None, "Не удалось извлечь данные о транспортном средстве. Попробуйте загрузить более четкое фото."
            
            return vehicle_data, None
            
        except Exception as e:
            return None, f"Ошибка обработки изображения: {str(e)}"
    
    def validate_data(self, data):
        """Валидация извлеченных данных"""
        errors = []
        
        if data['year']:
            year = int(data['year'])
            if year < 1990 or year > 2025:
                errors.append("Некорректный год выпуска")
        
        if data['engine_volume']:
            try:
                volume = int(data['engine_volume'])
                if volume < 50 or volume > 10000:
                    errors.append("Некорректный объем двигателя")
            except:
                errors.append("Некорректный формат объема двигателя")
        
        return errors

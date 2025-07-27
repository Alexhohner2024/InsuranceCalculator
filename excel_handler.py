
import pandas as pd
import os

class TariffHandler:
    def __init__(self):
        self.tariffs = {
            # Легковые автомобили
            'B1': {'name': 'до 1600 см³, в т.ч. гибриды', '30plus': 1959, 'noLimit': 2176},
            'B2': {'name': '1601-2000 см³, в т.ч. гибриды', '30plus': 2527, 'noLimit': 2807},
            'B3': {'name': '2001-3000 см³, в т.ч. гибриды', '30plus': 2585, 'noLimit': 2873},
            'B4': {'name': 'более 3001 см³, в т.ч. гибриды', '30plus': 3349, 'noLimit': 3721},
            'B5': {'name': 'исключительно с ДВС, кроме гибридных', '30plus': 3330, 'noLimit': 3700},
            
            # Автобусы и пассажирский транспорт
            'D1': {'name': 'до 20 чел.', '30plus': 5464, 'noLimit': 6071},
            'D2': {'name': 'более 20 чел.', '30plus': 6855, 'noLimit': 7616},
            'D3': {'name': 'трамваи', '30plus': 6855, 'noLimit': 7616},
            'D4': {'name': 'троллейбусы', '30plus': 6855, 'noLimit': 7616},
            
            # Грузовые автомобили
            'C0': {'name': 'грузовые до 2,4т', '30plus': 2703, 'noLimit': 3003},
            'C1': {'name': 'грузовые свыше 2,4т, грузоподъемность до 2т', '30plus': 4113, 'noLimit': 4570},
            'C2': {'name': 'грузоподъемность свыше 2т', '30plus': 5660, 'noLimit': 6289},
            
            # Мотоциклы
            'A1': {'name': 'мотоциклы до 300 см³, до 5 кВт', '30plus': 745, 'noLimit': 827},
            'A2': {'name': 'мотоциклы свыше 300 см³, багги, квадроциклы', '30plus': 1371, 'noLimit': 1524},
            
            # Сельхозтехника
            'G1': {'name': 'тракторы', '30plus': 3134, 'noLimit': 3482},
            'G2': {'name': 'с/х техника', '30plus': 3917, 'noLimit': 4352},
            'G3': {'name': 'прицепы к с/х технике и тракторам', '30plus': 980, 'noLimit': 1088},
            
            # Спецтехника
            'H1': {'name': 'ТС специального назначения', '30plus': 3917, 'noLimit': 4352},
            'H2': {'name': 'дорожно-строительная техника', '30plus': 3917, 'noLimit': 4352},
            'H3': {'name': 'военная техника', '30plus': 3917, 'noLimit': 4352},
            
            # Прицепы
            'F': {'name': 'прицепы к легковым ТС', '30plus': 666, 'noLimit': 740},
            'E': {'name': 'прицепы к грузовым ТС', '30plus': 980, 'noLimit': 1088}
        }
    
    def get_car_category(self, engine_volume):
        """Определяет категорию легкового автомобиля по объему двигателя"""
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
            return 'B2'  # по умолчанию
    
    def get_price(self, category, age_over_30=True):
        """Получает цену для категории и возраста водителя"""
        if category not in self.tariffs:
            return None
        
        price_type = '30plus' if age_over_30 else 'noLimit'
        return self.tariffs[category][price_type]
    
    def get_all_categories(self):
        """Возвращает список всех доступных категорий"""
        return list(self.tariffs.keys())
    
    def search_category_by_name(self, vehicle_type):
        """Поиск категории по типу ТС"""
        vehicle_type = vehicle_type.lower()
        
        # Легковые
        if any(word in vehicle_type for word in ['легков', 'автомобил', 'седан', 'хэтчбек', 'универсал', 'купе']):
            return 'AUTO'  # требует определения по объему
        
        # Грузовые
        elif any(word in vehicle_type for word in ['грузов', 'фургон', 'грузовик']):
            return 'C1'  # по умолчанию средний грузовик
        
        # Автобусы
        elif any(word in vehicle_type for word in ['автобус', 'микроавтобус']):
            return 'D1'  # по умолчанию малый автобус
        
        # Мотоциклы
        elif any(word in vehicle_type for word in ['мотоцикл', 'скутер', 'мопед']):
            return 'A1'  # по умолчанию малый мотоцикл
        
        # Спецтехника
        elif any(word in vehicle_type for word in ['трактор']):
            return 'G1'
        elif any(word in vehicle_type for word in ['экскаватор', 'бульдозер', 'кран']):
            return 'H2'
        
        # Прицепы
        elif any(word in vehicle_type for word in ['прицеп']):
            return 'F'  # легковой прицеп по умолчанию
        
        return 'B2'  # легковой по умолчанию

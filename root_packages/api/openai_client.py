import openai
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class UserPreferences:
    location: Optional[Dict[str, float]] = None
    category: Optional[str] = None
    price_range: Optional[str] = None
    time_preference: Optional[str] = None
    activity_type: Optional[str] = None
    specific_requirements: List[str] = None


class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.conversation_history = []

    async def generate_question(self, user_preferences: UserPreferences, conversation_history: List[Dict]) -> str:
        system_prompt = """Ты - умный ассистент в стиле игры Акинатор, который помогает пользователям найти интересные места в городе через 2ГИС.
        
        Твоя задача:
        1. Задавать наводящие вопросы для выяснения предпочтений пользователя
        2. Учитывать уже собранную информацию о предпочтениях
        3. Постепенно уточнять детали: тип заведения, ценовой сегмент, атмосферу, время посещения
        4. Задавать не более 1-2 вопросов за раз
        5. Говорить на русском языке в дружелюбном тоне
        
        Когда соберешь достаточно информации (3-4 критерия), предложи пользователю найти места.
        
        Текущие предпочтения пользователя:
        - Местоположение: {location}
        - Категория: {category}
        - Ценовой диапазон: {price_range}
        - Время: {time_preference}
        - Тип активности: {activity_type}
        - Особые требования: {specific_requirements}
        """
        
        messages = [
            {"role": "system", "content": system_prompt.format(
                location=user_preferences.location,
                category=user_preferences.category,
                price_range=user_preferences.price_range,
                time_preference=user_preferences.time_preference,
                activity_type=user_preferences.activity_type,
                specific_requirements=user_preferences.specific_requirements
            )}
        ]
        
        messages.extend(conversation_history)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.8
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating question: {e}")
            return "Не могу сформулировать вопрос. Попробуйте еще раз."

    async def analyze_user_response(self, user_message: str, current_preferences: UserPreferences) -> UserPreferences:
        system_prompt = """Проанализируй ответ пользователя и извлеки информацию о его предпочтениях для поиска мест.
        
        Возвращай ТОЛЬКО JSON со следующими полями:
        {
            "category": "ресторан|кафе|развлечения|спорт|культура|шоппинг|красота|услуги|другое",
            "price_range": "бюджетно|средний|премиум",
            "activity_type": "еда|развлечения|спорт|культура|шоппинг|отдых|другое",
            "time_preference": "утром|днем|вечером|ночью|выходные|будни",
            "specific_requirements": ["список", "особых", "требований"]
        }
        
        Включай только те поля, которые можно точно определить из ответа пользователя.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Обновляем только те поля, которые были определены
            updated_preferences = UserPreferences(
                location=current_preferences.location,
                category=result.get("category", current_preferences.category),
                price_range=result.get("price_range", current_preferences.price_range),
                time_preference=result.get("time_preference", current_preferences.time_preference),
                activity_type=result.get("activity_type", current_preferences.activity_type),
                specific_requirements=(current_preferences.specific_requirements or []) + 
                                    result.get("specific_requirements", [])
            )
            
            return updated_preferences
            
        except Exception as e:
            logging.error(f"Error analyzing user response: {e}")
            return current_preferences

    async def should_start_search(self, preferences: UserPreferences) -> bool:
        filled_fields = sum([
            bool(preferences.category),
            bool(preferences.price_range),
            bool(preferences.activity_type),
            bool(preferences.time_preference),
            bool(preferences.specific_requirements)
        ])
        
        return filled_fields >= 3

    async def generate_search_refinement_question(self, search_results: List[Dict], user_feedback: str) -> str:
        system_prompt = """Пользователь посмотрел результаты поиска мест и дал обратную связь. 
        Помоги ему уточнить поиск, задав наводящий вопрос для корректировки критериев.
        
        Ответь кратко и дружелюбно на русском языке."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Обратная связь пользователя: {user_feedback}"}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating refinement question: {e}")
            return "Что именно вам не подходит в предложенных местах?" 
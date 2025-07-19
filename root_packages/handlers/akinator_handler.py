from aiogram import types
from aiogram.dispatcher.dispatcher import Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from root_packages.api import OpenAIClient, GISClient
from root_packages.state import state_manager
from settings import settings


dp = Dispatcher()
openai_client = OpenAIClient(api_key=settings.openai.api_key, model=settings.openai.model)
gis_client = GISClient(settings.gis.api_key)


@dp.message(CommandStart())
async def start_akinator(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    
    # Очищаем предыдущую сессию и создаем новую
    state_manager.clear_session(user_id)
    state_manager.set_session_state(user_id, "collecting_preferences")
    
    welcome_text = f"""🎲 Привет, {user_name}! Добро пожаловать в Акинатор мест!

Я помогу тебе найти идеальное место для посещения в городе. Буду задавать вопросы о твоих предпочтениях, а затем предложу варианты из справочника 2ГИС.

Поделись своим местоположением, чтобы найти места рядом с тобой! 📍"""
    
    # Кнопка для запроса местоположения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Поделиться местоположением", callback_data="request_location")],
        [InlineKeyboardButton(text="🚀 Начать без геолокации", callback_data="start_without_location")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "request_location")
async def request_location(callback: types.CallbackQuery):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    
    location_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить местоположение", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.edit_text(
        "Отправь мне свое местоположение, нажав на кнопку ниже:",
        reply_markup=location_keyboard
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "start_without_location")
async def start_without_location(callback: types.CallbackQuery):
    await ask_first_question(callback.message, callback.from_user.id)
    await callback.answer()


@dp.message(lambda message: message.location is not None)
async def handle_location(message: types.Message):
    user_id = message.from_user.id
    location = message.location
    
    # Сохраняем местоположение
    state_manager.set_location(user_id, location.latitude, location.longitude)
    
    # Убираем клавиатуру с геолокацией
    from aiogram.types import ReplyKeyboardRemove
    await message.answer(
        f"📍 Отлично! Местоположение сохранено: {location.latitude:.4f}, {location.longitude:.4f}",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await ask_first_question(message, user_id)


async def ask_first_question(message: types.Message, user_id: int):
    session = state_manager.get_or_create_session(user_id)
    
    try:
        question = await openai_client.generate_question(
            session.preferences,
            state_manager.get_conversation_history(user_id, limit=10)
        )
        
        state_manager.add_message(user_id, "assistant", question)
        await message.answer(question)
        
    except Exception as e:
        logging.error(f"Error generating first question: {e}")
        await message.answer("Что бы ты хотел найти? Ресторан, развлечения, магазины или что-то еще?")


@dp.message(lambda message: message.text and not message.text.startswith('/'))
async def handle_user_response(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    
    session = state_manager.get_or_create_session(user_id)
    current_state = state_manager.get_session_state(user_id)
    
    if current_state not in ["collecting_preferences", "refining"]:
        return
    
    # Добавляем сообщение пользователя в историю
    state_manager.add_message(user_id, "user", user_text)
    
    try:
        # Анализируем ответ пользователя и обновляем предпочтения
        updated_preferences = await openai_client.analyze_user_response(
            user_text, 
            session.preferences
        )
        state_manager.update_preferences(user_id, updated_preferences)
        
        # Проверяем, достаточно ли информации для поиска
        should_search = await openai_client.should_start_search(updated_preferences)
        
        if should_search:
            # Предлагаем начать поиск
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Искать места", callback_data="start_search")],
                [InlineKeyboardButton(text="❓ Еще вопросы", callback_data="more_questions")]
            ])
            
            await message.answer(
                "У меня достаточно информации! Хочешь начать поиск или предпочитаешь ответить на еще несколько вопросов?",
                reply_markup=keyboard
            )
        else:
            # Задаем следующий вопрос
            question = await openai_client.generate_question(
                updated_preferences,
                state_manager.get_conversation_history(user_id, limit=10)
            )
            
            state_manager.add_message(user_id, "assistant", question)
            await message.answer(question)
            
    except Exception as e:
        logging.error(f"Error handling user response: {e}")
        await message.answer("Извини, произошла ошибка. Можешь повторить?")


@dp.callback_query(lambda c: c.data == "start_search")
async def start_search(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    session = state_manager.get_or_create_session(user_id)
    
    state_manager.set_session_state(user_id, "searching")
    
    await callback.message.edit_text("🔍 Ищу подходящие места...")
    await callback.answer()
    
    try:
        # Выполняем поиск
        places = await gis_client.search_places(
            session.preferences,
            session.current_location,
            radius=5000,
            limit=5
        )
        
        if places:
            state_manager.update_search_results(user_id, places)
            await show_search_results(callback.message, places, user_id)
        else:
            await callback.message.answer(
                "😔 К сожалению, не удалось найти подходящие места. Попробуй изменить критерии поиска."
            )
            state_manager.set_session_state(user_id, "collecting_preferences")
            
    except Exception as e:
        logging.error(f"Error during search: {e}")
        await callback.message.answer("Произошла ошибка при поиске. Попробуй еще раз.")


@dp.callback_query(lambda c: c.data == "more_questions")
async def more_questions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    session = state_manager.get_or_create_session(user_id)
    
    try:
        question = await openai_client.generate_question(
            session.preferences,
            state_manager.get_conversation_history(user_id, limit=10)
        )
        
        state_manager.add_message(user_id, "assistant", question)
        await callback.message.edit_text(question)
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error generating more questions: {e}")
        await callback.message.edit_text("Расскажи подробнее о своих предпочтениях!")
        await callback.answer()


async def show_search_results(message: types.Message, places, user_id: int):
    if not places:
        await message.answer("Места не найдены.")
        return
    
    results_text = "🎯 Вот что я нашел для тебя:\n\n"
    
    for i, place in enumerate(places[:5], 1):
        results_text += f"{i}. {gis_client.format_place_for_user(place)}\n"
    
    # Кнопки для взаимодействия с результатами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Отлично!", callback_data="results_good")],
        [InlineKeyboardButton(text="👎 Не подходит", callback_data="results_bad")],
        [InlineKeyboardButton(text="🔄 Новый поиск", callback_data="new_search")]
    ])
    
    await message.answer(results_text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "results_good")
async def results_good(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎉 Отлично! Надеюсь, тебе понравится выбранное место!\n\n"
        "Хочешь найти еще что-то? Используй /start для нового поиска."
    )
    state_manager.clear_session(callback.from_user.id)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "results_bad") 
async def results_bad(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state_manager.set_session_state(user_id, "refining")
    
    await callback.message.edit_text(
        "Понятно! Что именно тебе не подходит в предложенных местах? "
        "Расскажи подробнее, чтобы я мог скорректировать поиск."
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "new_search")
async def new_search(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state_manager.clear_session(user_id)
    state_manager.set_session_state(user_id, "collecting_preferences")
    
    await callback.message.edit_text(
        "🔄 Начинаем новый поиск! Что ты хочешь найти?"
    )
    await callback.answer()


@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = """🤖 <b>Помощь по Акинатору мест</b>

Я помогаю найти интересные места в городе через диалог:

🎯 <b>Как это работает:</b>
1. Запусти /start
2. Поделись местоположением (опционально)
3. Отвечай на мои вопросы о предпочтениях
4. Получи персональные рекомендации мест

📍 <b>Команды:</b>
/start - Начать новый поиск
/help - Показать эту справку

🔍 <b>Что я учитываю:</b>
• Тип заведения (ресторан, развлечения, магазины)
• Ценовой сегмент
• Время посещения
• Твое местоположение
• Особые пожелания

Просто общайся со мной естественно - я пойму! 😊"""

    await message.answer(help_text)


# Обработка ошибок
@dp.error()
async def error_handler(event, exception):
    logging.error(f"An error occurred: {exception}")
    if hasattr(event, 'message') and event.message:
        await event.message.answer("Произошла ошибка. Попробуйте еще раз или используйте /start для перезапуска.")

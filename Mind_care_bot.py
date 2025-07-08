import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в переменных окружения")

bot = Bot(token=BOT_TOKEN)


MOODS = ['😊 Отлично', '🙂 Хорошо', '😐 Нормальное', '😞 Плохо', '💀 Ужасно']
ACTIVITIES = ['💦 Попил воды', '🚶‍ Вышел на прогулку', '🎭 Занимался саморозвитием', '👫 Уделил время родным', '😌 Отдыхал']

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class UserStates(StatesGroup):
    waiting_for_mood = State()
    waiting_for_reason = State()
    waiting_for_activity = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=m)] for m in MOODS],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    user = message.from_user
    name = user.username or user.first_name or "друг"
    await message.answer(
        f"Привет, {name}! Какое у тебя сегодня настроение?",
        reply_markup=kb
    )
    await state.set_state(UserStates.waiting_for_mood)

@dp.message(UserStates.waiting_for_mood)
async def mood_chosen(message: types.Message, state: FSMContext):
    """Обработчик выбора настроения"""
    mood = message.text
    if mood not in MOODS:
        await message.answer('Пожалуйста, выбери настроение из списка.')
        return
    
    # Сохраняем настроение
    await state.update_data(mood=mood)
    
    # Если настроение плохое, спрашиваем причину
    if mood in ['😞 Плохо', '💀 Ужасно']:
        await message.answer('Почему у тебя плохое настроение?', reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserStates.waiting_for_reason)
        return
    
    # Иначе спрашиваем про активность
    activity_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=a)] for a in ACTIVITIES],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        f'Твоё настроение: {mood}. Отлично! А чем ты занимался сегодня?',
        reply_markup=activity_kb
    )
    await state.set_state(UserStates.waiting_for_activity)

@dp.message(UserStates.waiting_for_reason)
async def reason_received(message: types.Message, state: FSMContext):
    """Обработчик причины плохого настроения"""
    reason = message.text
    user_data = await state.get_data()
    mood = user_data.get('mood', 'Не указано')
    
    # Спрашиваем про активность
    activity_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=a)] for a in ACTIVITIES],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        f"Спасибо, что поделился. Надеюсь, твое настроение улучшится!\n"
        f"А чем ты занимался сегодня?",
        reply_markup=activity_kb
    )
    
    # Сохраняем данные о настроении
    await save_mood_data(message.from_user, mood, reason)
    await state.set_state(UserStates.waiting_for_activity)

@dp.message(UserStates.waiting_for_activity)
async def activity_chosen(message: types.Message, state: FSMContext):
    """Обработчик выбора активности"""
    activity = message.text
    if activity not in ACTIVITIES:
        await message.answer('Пожалуйста, выбери занятие из списка.')
        return
    
    user_data = await state.get_data()
    mood = user_data.get('mood', 'Не указано')
    
    await message.answer(
        f"Отлично! Ты сегодня:\n"
        f"- Настроение: {mood}\n"
        f"- Занятие: {activity}\n"
        f"Хорошего дня!",
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    # Сохраняем данные об активности
    await save_activity_data(message.from_user, activity)
    await state.clear()

@dp.message(Command("week"))
async def week_stats(message: types.Message):
    user = message.from_user.username or message.from_user.first_name or "аноним"
    try:
        with open('mood_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        await message.answer('Нет данных для статистики.')
        return
    week_ago = datetime.now() - timedelta(days=7)
    user_entries = []
    for entry in data:
        if entry.get('user') == user:
            date_str = entry.get('date', '')
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    continue
            if date_obj >= week_ago:
                user_entries.append(entry)
    if not user_entries:
        await message.answer('За последнюю неделю у вас нет записей о настроении.')
        return
    mood_count = {}
    for entry in user_entries:
        mood = entry.get('mood', 'Не указано')
        mood_count[mood] = mood_count.get(mood, 0) + 1
    stat_text = '\n'.join([f"{mood}: {count}" for mood, count in mood_count.items()])
    await message.answer(f'Ваша статистика за неделю:\n{stat_text}')

async def save_mood_data(user: types.User, mood: str, reason: str = None):
    """Сохраняет данные о настроении в JSON файл"""
    entry = {
        'user': user.username or user.first_name or str(user.id),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'mood': mood,
        'reason': reason
    }
    
    try:
        with open('mood_data.json', 'r+', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(entry)
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Ошибка сохранения настроения: {e}")

async def save_activity_data(user: types.User, activity: str):
    entry = {
        'user': user.username or user.first_name or str(user.id),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'activity': activity
    }
    
    try:
        with open('activity_data.json', 'r+', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(entry)
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Ошибка сохранения активности: {e}")

async def main():
    """Запуск бота"""
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка в работе бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
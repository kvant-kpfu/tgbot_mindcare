import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from aiogram.types import FSInputFile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в переменных окружения")

bot = Bot(token=BOT_TOKEN)

MOODS = ['😊 Отлично', '🙂 Хорошо', '😐 Нормальное', '😞 Плохо', '💀 Ужасно']
ACTIVITIES =  ['💦 Попил воды', '🚶‍ Вышел на прогулку', '🎭 Занимался саморозвитием', '👫 Уделил время родным', '😌 Отдыхал']
meme_photos = ["photo_memes/0758130c0ce44d103c6906f27869098b.jpg", "photo_memes/aab50f852dfb6fcd8c7dfc5eae70dffa.jpg", "photo_memes/de0d642d908d97f65e908ff1f5a7ffab.jpg",
               "photo_memes/8f8f0c042babad5c9a4d1515dd63468a.jpg", "photo_memes/306d4bd5c1be4558740ea76c0b3df847.jpg",
               "photo_memes/2137d655c5d753754a4782ec13645e88.jpg", "photo_memes/a13fe328d6f747bed4dbce2df6d18725.jpg",
               "photo_memes/b561c13dfd5b3de0da1bad09452c70cd.jpg", "photo_memes/b813b88a3c26b9f55b8c53f5c8b7ecdf.jpg"]

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
    mood = message.text
    if mood not in MOODS:
        await message.answer('Пожалуйста, выбери настроение из списка.')
        return
    await state.update_data(mood=mood)
    if mood in ['😞 Плохо', '💀 Ужасно']:
        random_meme = random.choice(meme_photos)
        if os.path.exists(random_meme):
            photo = FSInputFile(random_meme)
            await message.answer_photo(photo, caption="Держи мем, чтобы поднять настроение! 😊")
        await message.answer('Почему у тебя плохое настроение?', reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserStates.waiting_for_reason)
        return
    if mood in ['😞 Плохо', '💀 Ужасно']:
        await message.answer('Почему у тебя плохое настроение?', reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserStates.waiting_for_reason)
        return
    await save_mood_data(message.from_user, mood)
    activity_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=a)] for a in ACTIVITIES],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        f'Твоё настроение: {mood}. А чем ты занимался сегодня?',
        reply_markup=activity_kb
    )
    await state.set_state(UserStates.waiting_for_activity)

@dp.message(UserStates.waiting_for_reason)
async def reason_received(message: types.Message, state: FSMContext):
    reason = message.text
    user_data = await state.get_data()
    mood = user_data.get('mood', 'Не указано')
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
    await save_mood_data(message.from_user, mood, reason)
    await state.set_state(UserStates.waiting_for_activity)

@dp.message(UserStates.waiting_for_activity)
async def activity_chosen(message: types.Message, state: FSMContext):
    activity = message.text
    if activity not in ACTIVITIES:
        await message.answer('Пожалуйста, выбери занятие из списка.')
        return
    user_data = await state.get_data()
    mood = user_data.get('mood', 'Не указано')
    await message.answer(
        f"Ты сегодня:\n"
        f"- Настроение: {mood}\n"
        f"- Занятие: {activity}\n"
        f"Хорошего дня!",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await save_activity_data(message.from_user, activity)
    await state.clear()

@dp.message(Command("week"))
async def week_stats(message: types.Message):
    user = message.from_user.username or message.from_user.first_name or str(message.from_user.id)
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

@dp.message(Command("help"))
async def cmd_help(message: types.Message, state: FSMContext):
    help_text = (
        "Доступные команды:\n"
        "/start — начать работу с ботом\n"
        "/week — статистика настроения за неделю\n"
        "/help — список команд\n\n"
        "Просто отвечайте на вопросы бота, чтобы отслеживать своё настроение и активности.\n"
        "Если у вас плохое настроение, бот пришлёт мем для поднятия духа!"
    )
    await message.answer(help_text)

async def save_mood_data(user: types.User, mood: str, reason: str = None):
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
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка в работе бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
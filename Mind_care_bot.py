import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import os
from datetime import datetime
from dotenv import load_dotenv
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))

MOODS = ['Отличное', 'Хорошее', 'Нормальное', 'Плохое', 'Ужасное']

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class MoodStates(StatesGroup):
    waiting_for_mood = State()
    waiting_for_reason = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=m)] for m in MOODS],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    user = message.from_user
    name = user.username
    await message.answer(f"Привет, {name}, какое у тебя сегодня настроение?", reply_markup=kb)
    await state.set_state(MoodStates.waiting_for_mood)

@dp.message(MoodStates.waiting_for_mood)
async def mood_chosen(message: types.Message, state: FSMContext):
    mood = message.text
    if mood not in MOODS:
        await message.answer('Пожалуйста, выбери настроение из списка.')
        return
    if mood in ['Плохое', 'Ужасное']:
        await state.update_data(mood=mood)
        await message.answer('Почему у тебя плохое настроение?')
        await state.set_state(MoodStates.waiting_for_reason)
        return
    await message.answer(f'Твоё настроение на сегодня: {mood}. Спасибо!')
    await state.clear()

@dp.message(MoodStates.waiting_for_reason)
async def reason_received(message: types.Message, state: FSMContext):
    reason = message.text
    user = message.from_user.username
    date = datetime.now().strftime('%Y-%m-%d')
    data_state = await state.get_data()
    mood = data_state.get('mood', 'Плохое')
    entry = {
        'user': user,
        'date': date,
        'mood': mood,
        'reason': reason
    }
    try:
        with open('mood_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []
    data.append(entry)
    with open('mood_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    await message.answer(f'Спасибо, что поделился. Надеюсь, твое настроение улучшится!')
    await state.clear()

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
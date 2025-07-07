import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import os
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
    await message.answer(f'Твоё настроение на сегодня: {mood}. Спасибо!')
    await state.clear()

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
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
token = '7366099686:AAHHj6jSH4Ny7iUWbc_saC62KSI-t-95-xI'
bot = Bot(token)

MOODS =  ["😊 Отлично", "🙂 Хорошо", "😐 Такое себе", "😞 Плохо", "💀 Ужасно"]
doing = ['Попил воды', 'Вышел на прогулку', 'Занимался саморозвитием', 'Уделил время родным', 'Отдыхал']

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
    await message.answer(
        f"Привет, {name}, какое у тебя сегодня настроение?",
        reply_markup=kb
    )
    await state.set_state(MoodStates.waiting_for_mood)

@dp.message(MoodStates.waiting_for_mood)
async def mood_chosen(message: types.Message, state: FSMContext):
    mood = message.text
    activity_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=i)] for i in doing],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    if mood not in MOODS:
        await message.answer('Пожалуйста, выбери настроение из списка.')
        return
    await message.answer(f'Твоё настроение на сегодня: {mood}.')
    await message.answer("Чем ты занимался сегодня?",reply_markup=activity_kb )
    await state.clear()







@dp.message(MoodStates.waiting_for_mood)
async def case_chosen(message: types.Message, state: FSMContext):
    case = message.text
    if case not in doing:
        await message.answer('Пожалуйста, выбери занятие из списка.', reply_markup = activity_kb)
        return
    await message.answer(f'Твоё занятие на сегодня: {case}.')
    await state.clear()

async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
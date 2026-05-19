import asyncio
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# --- Конфигурация ---
TOKEN = "8947405422:AAEbDwBLYlSpEi7xFBGJcpXXoUs6SMNylTU"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Состояния ---
class QuizState(StatesGroup):
    exercise_type = State()
    waiting_ex_answer = State()
    test_progress = State() # (current_question, score)

# --- Данные (Контент) ---
RULE_TEXT = (
    "<b>📚 Правило: НЕ с причастиями</b>\n\n"
    "<b>ПИШЕТСЯ РАЗДЕЛЬНО:</b>\n"
    "1. С краткими причастиями (<i>не выучен, не открыта</i>).\n"
    "2. Если есть зависимые слова (<i>еще не прочитанная мною книга</i>).\n"
    "3. Если есть противопоставление с союзом А (<i>не законченная, а начатая работа</i>).\n\n"
    "<b>ПИШЕТСЯ СЛИТНО:</b>\n"
    "1. Если без НЕ не употребляется (<i>негодующий</i>).\n"
    "2. Если нет зависимых слов и противопоставления (<i>непрочитанная книга</i>).\n"
    "3. С наречиями меры и степени (очень, крайне и т.д. — они не являются зависимыми словами)."
)

EXERCISES = [
    {"type": "choice", "q": "Как пишется: (не)годующий взгляд?", "a": "слитно", "correct": "негодующий"},
    {"type": "insert", "q": "Вставь 'не' правильно: Книга ... прочитана.", "a": "не", "correct": "не прочитана"},
    {"type": "fix", "q": "Исправь ошибку: Не выученное к сроку задание.", "a": "невыученное", "correct": "невыученное"},
    {"type": "choice", "q": "Как пишется: (не)замеченная ошибка?", "a": "слитно", "correct": "незамеченная"},
    {"type": "insert", "q": "Вставь 'не': Работа ... закончена.", "a": "не", "correct": "не закончена"},
]

TEST_QUESTIONS = [
    {"q": "В каком случае 'не' пишется раздельно?", "o": ["Краткое причастие", "Нет зависимых слов", "Без 'не' не употребляется"], "correct": 0},
    {"q": "(Не)заселенное здание — как пишется?", "o": ["Слитно", "Раздельно"], "correct": 0},
    {"q": "Выберите раздельное написание:", "o": ["Невыполненная работа", "Никем не замеченная ошибка", "Негодующий человек"], "correct": 1},
    {"q": "Как пишется 'не' с краткими причастиями?", "o": ["Всегда слитно", "Всегда раздельно", "Зависит от смысла"], "correct": 1},
    {"q": "(Не)прочитанная мною книга:", "o": ["Слитно", "Раздельно"], "correct": 1},
    {"q": "Есть противопоставление с 'а':", "o": ["Пишем слитно", "Пишем раздельно"], "correct": 1},
    {"q": "Ошибка (не)исправлена:", "o": ["Слитно", "Раздельно"], "correct": 1},
]

# --- Клавиатуры ---
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📖 Изучить правило")
    kb.button(text="🎯 Выполнить упражнения")
    kb.button(text="📝 Пройти тест")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

# --- Хендлеры ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я — бот для изучения правила «Не с причастиями».\nВыбери действие:",
        reply_markup=main_menu()
    )

@dp.message(F.text == "📖 Изучить правило")
async def show_rule(message: types.Message):
    await message.answer(RULE_TEXT, parse_mode="HTML")

# --- Логика упражнений ---
@dp.message(F.text == "🎯 Выполнить упражнения")
async def start_exercise(message: types.Message, state: FSMContext):
    ex = random.choice(EXERCISES)
    await state.update_data(current_ex=ex)
    
    msg = f"<b>Задание:</b>\n{ex['q']}"
    if ex['type'] == "choice":
        msg += "\n\n(Напиши 'слитно' или 'раздельно')"
    elif ex['type'] == "insert":
        msg += "\n\n(Напиши слово с частицей 'не')"
    
    await message.answer(msg, parse_mode="HTML")
    await state.set_state(QuizState.waiting_ex_answer)

@dp.message(QuizState.waiting_ex_answer)
async def check_exercise(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ex = data['current_ex']
    user_ans = message.text.lower().strip()
    
    if user_ans == ex['a'] or user_ans == ex['correct']:
        await message.answer("✅ Правильно!")
    else:
        await message.answer(f"❌ Ошибка. Правильный вариант: {ex['correct']}")
    
    await state.clear()
    await message.answer("Хочешь еще? Нажми кнопку упражнений снова.", reply_markup=main_menu())

# --- Логика теста ---
@dp.message(F.text == "📝 Пройти тест")
async def start_test(message: types.Message, state: FSMContext):
    await state.update_data(test_idx=0, score=0)
    await send_test_question(message, 0)
    await state.set_state(QuizState.test_progress)

async def send_test_question(message: types.Message, idx: int):
    q = TEST_QUESTIONS[idx]
    kb = InlineKeyboardBuilder()
    for i, option in enumerate(q['o']):
        kb.button(text=option, callback_data=f"ans_{idx}_{i}")
    kb.adjust(1)
    await message.answer(f"Вопрос {idx+1}/7: {q['q']}", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("ans_"))
async def handle_test_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'test_idx' not in data: return

    q_idx = int(callback.data.split("_")[1])
    ans_idx = int(callback.data.split("_")[2])
    
    score = data['score']
    if ans_idx == TEST_QUESTIONS[q_idx]['correct']:
        score += 1
    
    next_idx = q_idx + 1
    await state.update_data(test_idx=next_idx, score=score)
    
    await callback.answer()
    
    if next_idx < len(TEST_QUESTIONS):
        await send_test_question(callback.message, next_idx)
    else:
        await callback.message.answer(f"🏁 Тест завершен!\nТвой результат: {score} из 7.")
        await state.clear()

# --- Запуск ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
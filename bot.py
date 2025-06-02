
import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

games = {}
cards_data = {
    "profession": ["инженер", "повар", "учитель", "солдат", "врач", "фермер", "химик"],
    "biology": ["мужчина, 35 лет", "женщина, 28 лет", "мужчина, 45 лет", "женщина, 22 года"],
    "health": ["здоров", "астма", "диабет", "аллергия", "плоскостопие"],
    "hobby": ["шахматы", "садоводство", "рыбалка", "спорт", "настольные игры"],
    "baggage": ["рюкзак с инструментами", "еда на 3 дня", "фотоальбом", "радио", "кот"],
    "fact": ["бывший заключённый", "волонтёр", "никогда не врал", "участвовал в экспедиции"],
    "condition": ["может поменяться ролями", "имеет право спасти одного изгнанного"]
}

class Player:
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name
        self.cards = {}

    def assign_random_cards(self):
        for category, options in cards_data.items():
            self.cards[category] = random.choice(options)

@dp.message_handler(commands=['start'])
async def start_cmd(message: Message):
    await message.answer("Добро пожаловать в Бункер-Бот!
/newgame — создать игру
/join — присоединиться
/begin — начать раздачу ролей")

@dp.message_handler(commands=['newgame'])
async def new_game(message: Message):
    chat_id = message.chat.id
    games[chat_id] = {"players": {}, "started": False}
    await message.answer("Создана новая игра. Игроки могут присоединяться с помощью /join")

@dp.message_handler(commands=['join'])
async def join_game(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    name = message.from_user.full_name

    if chat_id not in games:
        await message.answer("Сначала создайте игру с помощью /newgame")
        return

    game = games[chat_id]
    if game["started"]:
        await message.answer("Игра уже началась")
        return

    if user_id not in game["players"]:
        game["players"][user_id] = Player(user_id, name)
        await message.answer(f"{name} присоединился к игре!")
    else:
        await message.answer("Вы уже в игре.")

@dp.message_handler(commands=['begin'])
async def begin_game(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        await message.answer("Игра не создана.")
        return

    game = games[chat_id]
    if game["started"]:
        await message.answer("Игра уже идёт.")
        return

    game["started"] = True
    await message.answer("Игра начинается! Раздаю роли в личные сообщения...")

    for player in game["players"].values():
        player.assign_random_cards()
        card_text = "
".join([f"{k.capitalize()}: {v}" for k, v in player.cards.items()])
        try:
            await bot.send_message(player.user_id, f"🎴 Ваш персонаж:
{card_text}")
        except:
            await message.answer(f"❗ Не удалось отправить карточки {player.name}. Он должен сначала написать что-нибудь боту в личку.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

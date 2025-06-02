
import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
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
card_order = ["profession", "biology", "health", "hobby", "baggage", "fact"]

class Player:
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name
        self.cards = {}
        self.revealed = []
        self.is_out = False

    def assign_random_cards(self):
        for category, options in cards_data.items():
            self.cards[category] = random.choice(options)

    def reveal_next(self, round_num):
        if round_num < len(card_order):
            field = card_order[round_num]
            self.revealed.append(field)
            return field, self.cards[field]
        return None, None

@dp.message_handler(commands=['start'])
async def start_cmd(message: Message):
    await message.answer("Добро пожаловать в Бункер-Бот!
/newgame — создать игру
/join — присоединиться
/begin — начать раздачу ролей
/round — начать раунд
/vote — голосование")

@dp.message_handler(commands=['newgame'])
async def new_game(message: Message):
    chat_id = message.chat.id
    games[chat_id] = {
        "players": {},
        "started": False,
        "round": 0,
        "votes": {},
        "history": []
    }
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

@dp.message_handler(commands=['round'])
async def next_round(message: Message):
    chat_id = message.chat.id
    if chat_id not in games or not games[chat_id]["started"]:
        await message.answer("Сначала начните игру с /begin")
        return

    game = games[chat_id]
    round_num = game["round"]
    game["round"] += 1

    msg = f"🔄 Раунд {round_num + 1}: Игроки раскрывают по одной карте..."
    await message.answer(msg)

    for player in game["players"].values():
        if player.is_out:
            continue
        field, value = player.reveal_next(round_num)
        if field:
            await message.answer(f"📣 {player.name} раскрывает:
{field.capitalize()}: {value}")
        else:
            await message.answer(f"{player.name} больше нечего раскрывать.")

@dp.message_handler(commands=['vote'])
async def vote_start(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        await message.answer("Нет активной игры.")
        return

    game = games[chat_id]
    active_players = [p for p in game["players"].values() if not p.is_out]

    if len(active_players) <= 1:
        await message.answer("Недостаточно игроков для голосования.")
        return

    msg = "🗳 Голосование! Напишите /v [имя] — за кого вы голосуете (пример: /v Анна)"
    game["votes"] = {}
    game["history"].append(f"Раунд {game['round']}: старт голосования")
    await message.answer(msg)

@dp.message_handler(lambda message: message.text.startswith("/v "))
async def receive_vote(message: Message):
    chat_id = message.chat.id
    voter = message.from_user.full_name
    vote_target = message.text[3:].strip().lower()

    game = games[chat_id]
    players = game["players"]

    for p in players.values():
        if p.name.lower().startswith(vote_target) and not p.is_out:
            game["votes"][voter] = p.user_id
            await message.answer(f"{voter} проголосовал за {p.name}")
            return

    await message.answer("Такого игрока нет или он уже изгнан.")

@dp.message_handler(commands=['results'])
async def vote_results(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        await message.answer("Нет активной игры.")
        return

    game = games[chat_id]
    if not game["votes"]:
        await message.answer("Голосов пока нет.")
        return

    tally = {}
    for voter, voted_id in game["votes"].items():
        tally[voted_id] = tally.get(voted_id, 0) + 1

    max_votes = max(tally.values())
    eliminated = [uid for uid, count in tally.items() if count == max_votes]

    if len(eliminated) == 1:
        out_id = eliminated[0]
    else:
        out_id = random.choice(eliminated)

    game["players"][out_id].is_out = True
    out_name = game["players"][out_id].name
    await message.answer(f"🚪 {out_name} изгнан из бункера!")

    game["votes"] = {}


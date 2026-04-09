import asyncio
import re
import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import Message

# === ВСТАВЬ СЮДА ТОКЕН СВОЕГО БОТА ===
BOT_TOKEN = "8212158556:AAFys-MskaxkNPNV4VgbEh9kXz2CY-YNmVI"
# =====================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения данных: {user_id: {"url": url, "last_views": int, "task": asyncio.Task}}
active_tasks = {}

# Функция для конвертации просмотров (например: 1.2K -> 1200)
def parse_views(views_str):
    views_str = views_str.replace(' ', '')
    if 'K' in views_str:
        return int(float(views_str.replace('K', '')) * 1000)
    if 'M' in views_str:
        return int(float(views_str.replace('M', '')) * 1000000)
    return int(views_str)

# Парсер просмотров с веб-страницы Telegram
async def fetch_views(url):
    # Очищаем ссылку и делаем её ссылкой на виджет для удобного парсинга
    clean_url = url.split("?")[0]
    embed_url = f"{clean_url}?embed=1"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(embed_url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                # Ищем элемент с просмотрами
                views_span = soup.find('span', class_='tgme_widget_message_views')
                if views_span:
                    return parse_views(views_span.text)
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
    return None

# Фоновая задача для проверки просмотров
async def check_views_loop(user_id: int, url: str):
    while True:
        await asyncio.sleep(300) # Ждем 5 минут (300 секунд)
        
        current_views = await fetch_views(url)
        if current_views is None:
            continue
            
        last_views = active_tasks[user_id]["last_views"]
        
        # Если просмотры выросли
        if current_views > last_views:
            diff = current_views - last_views
            active_tasks[user_id]["last_views"] = current_views
            
            try:
                await bot.send_message(
                    user_id, 
                    f"👀 <b>{diff} новых просмотров!</b>\n"
                    f"📈 Всего просмотров: {current_views}\n"
                    f"🔗 Пост: {url}",
                    parse_mode="HTML"
                )
            except Exception:
                break # Если бот заблокирован пользователем

@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "Привет! Пришли мне ссылку на пост в <b>публичном</b> Telegram-канале "
        "(например: https://t.me/telegram/123), и я буду каждые 5 минут проверять просмотры.",
        parse_mode="HTML"
    )

@dp.message(F.text.startswith("https://t.me/"))
async def handle_link(message: Message):
    url = message.text.strip()
    user_id = message.from_user.id
    
    # Отменяем предыдущую задачу, если она была
    if user_id in active_tasks and active_tasks[user_id]["task"]:
        active_tasks[user_id]["task"].cancel()
        
    initial_views = await fetch_views(url)
    
    if initial_views is None:
        await message.answer("❌ Не удалось получить просмотры. Убедись, что канал публичный и ссылка правильная.")
        return
        
    await message.answer(f"✅ Отслеживание запущено!\nТекущие просмотры: <b>{initial_views}</b>.\nЯ напишу, когда они увеличатся.", parse_mode="HTML")
    
    # Запускаем фоновый цикл для этого пользователя
    task = asyncio.create_task(check_views_loop(user_id, url))
    
    active_tasks[user_id] = {
        "url": url,
        "last_views": initial_views,
        "task": task
    }

@dp.message()
async def unknown_text(message: Message):
    await message.answer("Просто пришли мне ссылку на пост в формате https://t.me/канал/номер_поста")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

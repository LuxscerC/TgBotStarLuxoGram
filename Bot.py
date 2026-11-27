import asyncio
import json
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
SITE_URL = os.environ.get("SITE_URL", "https://starluxogram.site/")

try:
    DATA_DIR = Path(__file__).resolve().parent / "data"
except NameError:
    DATA_DIR = Path.cwd() / "data"
DATA_DIR.mkdir(exist_ok=True)
THEMES_FILE = DATA_DIR / "themes.json"

storage_lock = asyncio.Lock()
PREFIXES = ("/", ".", "!")


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def get_themes() -> dict:
    async with storage_lock:
        data = _read_json(THEMES_FILE)
        if "themes" not in data:
            data = {"next_id": 1, "themes": {}}
        return data


async def save_themes(data: dict) -> None:
    async with storage_lock:
        _write_json(THEMES_FILE, data)


class PrefixCommand(BaseFilter):
    def __init__(self, *commands: str):
        self.commands = {c.lower() for c in commands}

    async def __call__(self, message: Message) -> bool | dict:
        if not message.text:
            return False
        text = message.text.strip()
        if not text:
            return False
        prefix = None
        for p in PREFIXES:
            if text.startswith(p):
                prefix = p
                break
        if not prefix:
            return False
        body = text[len(prefix):].strip()
        if not body:
            return False
        parts = body.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]
        if cmd not in self.commands:
            return False
        args = parts[1] if len(parts) > 1 else ""
        return {"command": cmd, "args": args}


router = Router()

SITE_TEXT = f"🖥 Наш сайт: {SITE_URL}"


@router.message(PrefixCommand("start"))
async def cmd_start(message: Message, command: str, args: str):
    await message.answer("👋Приветствую!\nЭтот бот – перенос сайта «ЛюксоГрам. /help для полного достцпа команд.»")


@router.message(PrefixCommand("help"))
async def cmd_help(message: Message, command: str, args: str):
    await message.answer("Все команды:\n .Темы – список тем.\n .Создать тему название суть.")


@router.message(PrefixCommand("site", "сайт"))
async def cmd_site(message: Message, command: str, args: str):
    await message.answer(SITE_TEXT)


@router.message(PrefixCommand("createtheme", "создатьтему", "создать_тему"))
async def cmd_createtheme(message: Message, command: str, args: str):
    parts = args.split(maxsplit=1)
    if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
        await message.answer(
            "Использование: /createtheme название суть_темы\n"
            "Пример: /createtheme Программирование Обсуждение языков, библиотек и проектов."
        )
        return

    title = parts[0].strip()
    description = parts[1].strip()
    creator_id = message.from_user.id
    creator_username = message.from_user.username

    themes_data = await get_themes()
    theme_id = str(themes_data["next_id"])
    themes_data["themes"][theme_id] = {
        "title": title,
        "description": description,
        "creator_id": creator_id,
        "creator_username": creator_username,
    }
    themes_data["next_id"] += 1
    await save_themes(themes_data)

    username_str = f"@{creator_username}" if creator_username else "без юзернейма"
    await message.answer(
        f"✅ Тема создана!\n"
        f"ID: {theme_id}\n"
        f"Название: {title}\n"
        f"Суть: {description}\n"
        f"Создатель: {username_str} (ID: {creator_id})"
    )


@router.message(PrefixCommand("themes", "темы"))
async def cmd_themes(message: Message, command: str, args: str):
    themes_data = await get_themes()
    themes = themes_data.get("themes", {})

    if not themes:
        await message.answer("📋 Пока нет ни одной темы.")
        return

    lines = ["📋 Список тем:\n"]
    for tid, info in sorted(themes.items(), key=lambda x: int(x[0])):
        creator_id = info.get("creator_id", "—")
        username = info.get("creator_username")
        if username:
            creator = f"@{username} (ID: {creator_id})"
        else:
            creator = f"ID: {creator_id}"
        lines.append(f"🆔 ID: {tid}")
        lines.append(f"📌 Название: {info['title']}")
        lines.append(f"📝 Суть: {info['description']}")
        lines.append(f"👤 Создатель: {creator}")
        lines.append("")

    await message.answer("\n".join(lines))


@router.message(PrefixCommand("deletetheme", "удалитьтему", "удалить_тему", "removetheme"))
async def cmd_deletetheme(message: Message, command: str, args: str):
    if message.from_user.id != OWNER_ID:
        await message.answer("Вы не можете выполнить эту команду.")
        return

    theme_id = args.strip()
    if not theme_id:
        await message.answer("Использование: /deletetheme айди_темы")
        return

    themes_data = await get_themes()
    if theme_id not in themes_data.get("themes", {}):
        await message.answer("❌ Тема с таким ID не найдена.")
        return

    del themes_data["themes"][theme_id]
    await save_themes(themes_data)
    await message.answer(f"✅ Тема с ID {theme_id} удалена.")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения.")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

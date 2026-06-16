"""
Запросы к бесплатным публичным API без ключей:
- котики (thecatapi.com)
- собаки (dog.ceo)
- мемы (meme-api.com)
- гифки-реакции (nekos.best)

А также выбор случайного файла из локальной папки media/.
"""

import random
from pathlib import Path

import aiohttp

GIF_CATEGORIES = [
    "hug", "pat", "wave", "cuddle", "poke",
    "tickle", "baka", "smile", "wink", "dance",
]

MEDIA_DIR = Path("media")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}


async def fetch_cat_url(session: aiohttp.ClientSession) -> str:
    async with session.get("https://api.thecatapi.com/v1/images/search") as resp:
        data = await resp.json()
        return data[0]["url"]


async def fetch_dog_url(session: aiohttp.ClientSession) -> str:
    async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
        data = await resp.json()
        return data["message"]


async def fetch_meme(session: aiohttp.ClientSession) -> tuple[str, str]:
    async with session.get("https://meme-api.com/gimme") as resp:
        data = await resp.json()
        return data["url"], data.get("title", "")


async def fetch_gif(session: aiohttp.ClientSession) -> tuple[str, str]:
    category = random.choice(GIF_CATEGORIES)
    async with session.get(f"https://nekos.best/api/v2/{category}") as resp:
        data = await resp.json()
        result = data["results"][0]
        return result["url"], category


def get_random_local_file() -> Path | None:
    """Возвращает случайный файл из папки media/, либо None если её нет или она пуста."""
    if not MEDIA_DIR.exists():
        return None
    files = [f for f in MEDIA_DIR.iterdir() if f.is_file()]
    if not files:
        return None
    return random.choice(files)


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS

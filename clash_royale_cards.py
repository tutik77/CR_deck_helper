import json
import os
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.clashroyale.com/v1"


def _get_api_token() -> str:
    """
    Берёт токен Clash Royale API из переменной окружения CLASH_ROYALE_API_TOKEN.

    Для локальной разработки удобно хранить его в файле `.env` в корне проекта:

        CLASH_ROYALE_API_TOKEN=ваш_реальный_токен
    """
    # Ищем .env, поднимаясь на пару уровней вверх от этого файла
    current = Path(__file__).resolve()
    for _ in range(3):
        env_path = current.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            break
        current = current.parent

    token = os.getenv("CLASH_ROYALE_API_TOKEN")
    if not token:
        raise RuntimeError(
            "CLASH_ROYALE_API_TOKEN не найден. "
            "Создайте файл .env в корне проекта и добавьте туда строку\n"
            "CLASH_ROYALE_API_TOKEN=ваш_токен_сюда"
        )
    return token


def get_player_data(player_tag: str) -> dict | None:
    encoded_tag = urllib.parse.quote(player_tag)
    url = f"{BASE_URL}/players/{encoded_tag}"

    headers = {
        "Authorization": f"Bearer {_get_api_token()}",
        "Accept": "application/json",
    }

    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        print(f"Ошибка запроса: {resp.status_code} {resp.text}")
        return None

    return resp.json()


def save_player_cards_to_file(player_data: dict, output_dir: Path | None = None) -> Path:
    player_name = player_data.get("name", "Unknown")
    player_tag = player_data.get("tag", "")
    cards = player_data.get("cards", [])

    if not cards:
        print("Карты не найдены в ответе API.")

    if output_dir is None:
        output_dir = Path(".")

    safe_tag = player_tag.replace("#", "").replace(" ", "")
    filename = output_dir / f"player_cards_{safe_tag or 'unknown'}.json"

    data_to_save = {
        "player_name": player_name,
        "player_tag": player_tag,
        "cards": cards,
    }

    content = json.dumps(data_to_save, ensure_ascii=False, indent=2)
    filename.write_text(content, encoding="utf-8")

    return filename


def main() -> None:
    player_tag = input("Введите тег игрока (например, #ABC123XYZ): ").strip()
    if not player_tag:
        print("Тег игрока не указан.")
        return

    player_data = get_player_data(player_tag)
    if not player_data:
        return

    output_path = save_player_cards_to_file(player_data)
    print(f"Информация о картах сохранена в файл: {output_path}")


if __name__ == "__main__":
    main()
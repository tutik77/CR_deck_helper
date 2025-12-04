import os

import requests
from django.core.management.base import BaseCommand, CommandError

from app.models import Card


BASE_URL = "https://api.clashroyale.com/v1"


class Command(BaseCommand):
    help = "Импортирует все карты из официального Clash Royale API в таблицу Card"

    def handle(self, *args, **options):
        token = os.getenv("CLASH_ROYALE_API_TOKEN")
        if not token:
            raise CommandError(
                "Переменная окружения CLASH_ROYALE_API_TOKEN не установлена. "
                "Добавь её в .env в корне проекта."
            )

        url = f"{BASE_URL}/cards"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        self.stdout.write(f"Запрашиваю список карт из {url} ...")
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise CommandError(
                f"Ошибка запроса к API: {resp.status_code} {resp.text}"
            )

        data = resp.json()
        items = data.get("items", [])
        self.stdout.write(f"Найдено карт: {len(items)}")

        created = 0
        updated = 0

        for item in items:
            api_id = item.get("id")
            name = item.get("name")
            if api_id is None or not name:
                continue

            icon_urls = item.get("iconUrls") or {}
            defaults = {
                "name": name,
                "max_level": item.get("maxLevel"),
                "max_evolution_level": item.get("maxEvolutionLevel"),
                "max_star_level": item.get("maxStarLevel"),
                "icon_url": icon_urls.get("medium") or "",
            }

            obj, created_flag = Card.objects.update_or_create(
                api_id=api_id,
                defaults=defaults,
            )
            if created_flag:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Создано карт: {created}, обновлено: {updated}."
            )
        )



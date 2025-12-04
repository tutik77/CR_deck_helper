import re
from typing import Any, Dict, List

import bs4  # type: ignore
import requests
from django.core.management.base import BaseCommand

from app.models import Card, Deck, DeckCard


DEFAULT_URL = "https://statsroyale.com/ru/decks/popular?type=path-of-legends"


def parse_decks_from_html(html: str) -> List[Dict[str, Any]]:
    """
    Возвращает список колод из HTML StatsRoyale.

    Каждая колода:
    {
        "card_ids": ["26000024", ... 8 шт. ...],
        "elixir": 3.0 | None,
        "win_rate": 78.9 | None,
        "avg_crowns": 1.3 | None,
    }
    """
    soup = bs4.BeautifulSoup(html, "html.parser")

    decks: List[Dict[str, Any]] = []

    for box in soup.select("div.content-box"):
        link = box.select_one('a[href^="clashroyale://copyDeck?deck="]')
        if not link:
            continue

        href = link.get("href", "")
        m = re.search(r"deck=([^&]+)", href)
        if not m:
            continue

        deck_str = m.group(1)
        card_ids = [cid for cid in deck_str.split(";") if cid]
        if len(card_ids) != 8:
            continue

        def _extract_number_by_img(src_fragment: str) -> float | None:
            img = box.select_one(f'img[src*="{src_fragment}"]')
            if not img:
                return None
            parent_div = img.find_parent("div")
            if not parent_div:
                return None
            text_divs = parent_div.select("div")
            if not text_divs:
                return None
            raw = text_divs[-1].get_text(strip=True)
            raw = raw.replace("%", "").replace(",", ".").strip()
            try:
                return float(raw)
            except ValueError:
                return None

        elixir = _extract_number_by_img("images/elixir.png")
        win_rate = _extract_number_by_img("images/battle.png")
        avg_crowns = _extract_number_by_img("images/crown-blue.png")

        decks.append(
            {
                "card_ids": card_ids,
                "elixir": elixir,
                "win_rate": win_rate,
                "avg_crowns": avg_crowns,
            }
        )

    return decks


class Command(BaseCommand):
    help = (
        "Импортирует популярные колоды со StatsRoyale в таблицы Deck/DeckCard. "
        "По умолчанию берёт Path of Legends, можно переопределить URL через --url."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            default=DEFAULT_URL,
            help=(
                "URL страницы StatsRoyale с колодами. "
                "По умолчанию: популярные колоды Path of Legends."
            ),
        )
        parser.add_argument(
            "--file",
            type=str,
            default="",
            help=(
                "Путь до заранее сохранённого HTML-файла (например, page.html). "
                "Если указан, страница не будет скачиваться по сети, а будет "
                "использован этот файл."
            ),
        )
        parser.add_argument(
            "--mode",
            type=str,
            default="path-of-legends",
            help="Значение поля Deck.mode для импортируемых колод.",
        )

    def handle(self, *args, **options):
        url = options["url"]
        file_path = options["file"]

        # 1. Получаем HTML либо из файла, либо по сети
        if file_path:
            self.stdout.write(f"Читаю HTML из файла: {file_path}")
            try:
                from pathlib import Path

                html = Path(file_path).read_text(encoding="utf-8")
            except OSError as exc:
                raise RuntimeError(f"Не удалось прочитать файл {file_path}: {exc}") from exc
        else:
            self.stdout.write(f"Скачиваю страницу с колодами: {url}")
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (royale-helper)"},
                timeout=20,
            )
            resp.raise_for_status()
            html = resp.text

        mode = options["mode"]

        decks_data = parse_decks_from_html(html)
        self.stdout.write(f"Найдено колод в HTML: {len(decks_data)}")

        created_decks = 0
        skipped_decks = 0

        for deck_data in decks_data:
            card_ids = deck_data["card_ids"]
            # Проверяем, что все карты уже есть в таблице Card
            cards: List[Card] = []
            missing_card = False
            for cid in card_ids:
                try:
                    card = Card.objects.get(api_id=int(cid))
                except (Card.DoesNotExist, ValueError):
                    missing_card = True
                    break
                else:
                    cards.append(card)

            if missing_card:
                skipped_decks += 1
                continue

            deck = Deck.objects.create(
                mode=mode,
                avg_elixir=deck_data["elixir"],
                win_rate=deck_data["win_rate"],
                avg_crowns=deck_data["avg_crowns"],
            )

            for position, card in enumerate(cards):
                DeckCard.objects.create(
                    deck=deck,
                    card=card,
                    position=position,
                )

            created_decks += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Создано колод: {created_decks}, пропущено (из-за отсутствующих карт): {skipped_decks}."
            )
        )



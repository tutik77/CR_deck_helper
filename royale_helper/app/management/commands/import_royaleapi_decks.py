from typing import Any, Dict, List

import re

import requests
from bs4 import BeautifulSoup  # type: ignore
from django.core.management.base import BaseCommand

from app.models import Card, Deck, DeckCard


DEFAULT_URL = (
    "https://royaleapi.com/decks/popular"
    "?time=1d&sort=rating&size=30&players=PvP"
    "&min_elixir=1&max_elixir=9&evo=None"
    "&min_cycle_elixir=4&max_cycle_elixir=28"
    "&mode=detail&type=Ranked&global_exclude=false"
)


def parse_decks_from_html(html: str) -> List[Dict[str, Any]]:
    """
    Парсит HTML страницы популярных колод RoyaleAPI и возвращает список колод.

    Каждая колода представлена словарём:
    {
        "card_names": ["Goblin Cage", "Royal Recruits", ... 8 шт. ...],
        "avg_elixir": 4.1 | None,
    }
    """
    soup = BeautifulSoup(html, "html.parser")
    decks: List[Dict[str, Any]] = []

    # Ищем элементы, где встречается текст 'Avg Elixir'
    for avg_label in soup.find_all(
        string=lambda s: isinstance(s, str) and "Avg Elixir" in s
    ):
        container = avg_label.find_parent("section") or avg_label.find_parent("div")
        if not container:
            continue

        texts = [t.strip() for t in container.stripped_strings if t.strip()]

        # Находим индекс "Avg Elixir"
        try:
            idx = texts.index("Avg Elixir")
        except ValueError:
            continue

        candidates = texts[:idx]

        def looks_like_number(s: str) -> bool:
            return bool(re.fullmatch(r"[0-9]+(\.[0-9]+)?", s.replace(",", ".")))

        bad_tokens = {
            "Deck Stats",
            "4-Card Cycle",
            "Rating",
            "Usage",
            "Wins",
            "Draws",
            "Losses",
        }

        filtered: List[str] = []
        for t in candidates:
            if t in bad_tokens:
                continue
            if looks_like_number(t):
                continue
            if t.endswith("%"):
                continue
            filtered.append(t)

        seen: set[str] = set()
        cards_reversed: List[str] = []
        for t in reversed(filtered):
            if t in seen:
                continue
            seen.add(t)
            cards_reversed.append(t)
            if len(cards_reversed) == 8:
                break

        if len(cards_reversed) != 8:
            continue

        card_names = list(reversed(cards_reversed))

        # Средний эликсир: ищем первое число после "Avg Elixir"
        avg_elixir = None
        for i, txt in enumerate(texts[idx:], start=idx):
            if txt == "Avg Elixir":
                continue
            normalized = txt.replace(",", ".").strip()
            try:
                avg_elixir = float(normalized)
                break
            except ValueError:
                continue

        decks.append(
            {
                "card_names": card_names,
                "avg_elixir": avg_elixir,
            }
        )

    return decks


class Command(BaseCommand):
    help = (
        "Импортирует популярные колоды с RoyaleAPI в таблицы Deck/DeckCard. "
        "Использует HTML, отданный сервером (без сохранения файла)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            default=DEFAULT_URL,
            help="URL страницы RoyaleAPI с популярными колодами.",
        )
        parser.add_argument(
            "--mode",
            type=str,
            default="ranked",
            help="Значение поля Deck.mode для импортируемых колод.",
        )

    def handle(self, *args, **options):
        url = options["url"]
        mode = options["mode"]

        self.stdout.write(f"Скачиваю страницу RoyaleAPI: {url}")
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (royale-helper)",
                "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            },
            timeout=25,
        )
        resp.raise_for_status()
        html = resp.text

        markers = ["Best Clash Royale Decks", "Popular Decks", "Deck Stats"]
        found = [m for m in markers if m in html]
        if not found:
            self.stdout.write(
                self.style.WARNING(
                    "В HTML не найдены ожидаемые маркеры ('Best Clash Royale Decks' / "
                    "'Popular Decks' / 'Deck Stats'). Структура страницы могла измениться."
                )
            )

        decks_data = parse_decks_from_html(html)
        self.stdout.write(f"Найдено колод в HTML: {len(decks_data)}")

        created_decks = 0
        skipped_decks = 0

        for deck_data in decks_data:
            card_names = deck_data["card_names"]

            # Маппинг имён на объекты Card по name (без учёта регистра)
            cards: List[Card] = []
            missing_card = False
            for name in card_names:
                card = Card.objects.filter(name__iexact=name).first()
                if not card:
                    missing_card = True
                    break
                cards.append(card)

            if missing_card:
                skipped_decks += 1
                continue

            deck = Deck.objects.create(
                mode=mode,
                avg_elixir=deck_data["avg_elixir"],
                win_rate=None,
                avg_crowns=None,
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



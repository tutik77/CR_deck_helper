import json
import re

import requests
from bs4 import BeautifulSoup

URL = (
    "https://royaleapi.com/decks/popular"
    "?time=1d&sort=rating&size=30&players=PvP"
    "&min_elixir=1&max_elixir=9&evo=None"
    "&min_cycle_elixir=4&max_cycle_elixir=28"
    "&mode=detail&type=Ranked&global_exclude=false"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (royale-helper-test)",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
}


def fetch_html() -> str:
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    html = resp.text

    # Быстрая проверка, что HTML нормальный и содержит ожидаемые маркеры
    markers = ["Best Clash Royale Decks", "Popular Decks", "Deck Stats"]
    found = [m for m in markers if m in html]
    if not found:
        print("⚠ В HTML не найдены ожидаемые маркеры ('Best Clash Royale Decks' / 'Popular Decks' / 'Deck Stats').")
    else:
        print(f"✅ В HTML найдены маркеры: {', '.join(found)}")

    # Сохраняем HTML на диск для ручной проверки при необходимости
    with open("royaleapi_page.html", "w", encoding="utf-8") as f:
        f.write(html)

    return html


def parse_decks_from_html(html: str):
    """
    Более надёжный парсер: использует JSON-LD блок с метаданными,
    который RoyaleAPI кладёт в <script type="application/ld+json">.

    В этом блоке есть список ItemList с элементами:
    {
      "@type": "ListItem",
      "position": 1,
      "item": {
         "name": "...",
         "url": "https://royaleapi.com/decks/stats/card1,card2,..."
      }
    }

    Мы достаём name и список card_slugs из последнего сегмента URL.
    """
    soup = BeautifulSoup(html, "html.parser")
    decks: list[dict[str, object]] = []

    script = soup.find("script", {"type": "application/ld+json"})
    if not script or not script.string:
        return []

    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return []

    # mainEntity может быть в dict или в одном из элементов списка
    main_entities = None
    if isinstance(data, dict):
        main_entities = data.get("mainEntity")
    elif isinstance(data, list):
        for obj in data:
            if isinstance(obj, dict) and "mainEntity" in obj:
                main_entities = obj.get("mainEntity")
                break

    if not main_entities:
        return []

    # main_entities может быть dict или list
    item_lists = []
    if isinstance(main_entities, dict):
        item_lists = [main_entities]
    elif isinstance(main_entities, list):
        item_lists = [e for e in main_entities if isinstance(e, dict)]

    for entity in item_lists:
        if entity.get("@type") != "ItemList":
            continue
        elements = entity.get("itemListElement") or []
        for elem in elements:
            if not isinstance(elem, dict):
                continue
            item = elem.get("item") or {}
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            url = item.get("url")
            if not (isinstance(name, str) and isinstance(url, str)):
                continue

            # Последний сегмент URL: card1,card2,...
            slug_part = url.rstrip("/").split("/")[-1]
            card_slugs = [s for s in slug_part.split(",") if s]
            if len(card_slugs) != 8:
                continue

            decks.append(
                {
                    "name": name,
                    "card_slugs": card_slugs,
                }
            )

    return decks


def main() -> None:
    html = fetch_html()
    decks = parse_decks_from_html(html)
    print(f"Найдено колод: {len(decks)}")
    for i, deck in enumerate(decks[:5], start=1):
        print(f"\nКолода #{i}: {deck['name']}")
        print("  card_slugs:", ", ".join(deck["card_slugs"]))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()



import re
from pathlib import Path
from typing import Any, Dict, List

import bs4  # type: ignore


URL_HINT = "https://statsroyale.com/ru/decks/popular?type=path-of-legends"


def parse_decks_from_html(html: str) -> List[Dict[str, Any]]:
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


def parse_decks_from_file(path: str | Path) -> List[Dict[str, Any]]:
    content = Path(path).read_text(encoding="utf-8")
    return parse_decks_from_html(content)


def main() -> None:
    html_path = Path("page.html")
    if not html_path.exists():
        print(
            f"Файл {html_path} не найден. "
            f"Сохрани HTML со страницы {URL_HINT} как 'page.html' рядом со скриптом."
        )
        return

    decks = parse_decks_from_file(html_path)
    print(f"Найдено колод: {len(decks)}")
    for i, deck in enumerate(decks, start=1):
        print(f"\nКолода #{i}")
        print("  card_ids:", ";".join(deck["card_ids"]))
        print("  elixir:", deck["elixir"])
        print("  win_rate:", deck["win_rate"])
        print("  avg_crowns:", deck["avg_crowns"])


if __name__ == "__main__":
    main()



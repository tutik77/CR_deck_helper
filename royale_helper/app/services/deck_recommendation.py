from dataclasses import dataclass
from typing import Iterable, List

from app.models import Card, Deck
from .clash_royale import PlayerProfile


@dataclass(frozen=True)
class RecommendedDeckCard:
    card: Card
    level: int | None
    effective_level: int | None


@dataclass(frozen=True)
class RecommendedDeck:
    deck: Deck
    owned_cards_count: int
    total_level: int
    cards: List[RecommendedDeckCard]


class DeckRecommender:
    def recommend(
        self,
        player: PlayerProfile,
        decks: Iterable[Deck],
        limit: int = 3,
    ) -> List[RecommendedDeck]:
        level_by_card_id = {card.id: card.level for card in player.cards}
        scored: List[RecommendedDeck] = []

        for deck in decks:
            owned = 0
            total_level = 0
            cards: List[RecommendedDeckCard] = []

            for deck_card in deck.deck_cards.all():
                card = deck_card.card
                card_level = level_by_card_id.get(card.api_id)
                effective_level: int | None = None

                if card_level is not None:
                    owned += 1
                    effective_level = card_level
                    if card.max_level:
                        effective_level = 16 - card.max_level + card_level
                    total_level += effective_level
                cards.append(
                    RecommendedDeckCard(
                        card=card,
                        level=card_level,
                        effective_level=effective_level,
                    )
                )

            if owned == 0:
                continue

            scored.append(
                RecommendedDeck(
                    deck=deck,
                    owned_cards_count=owned,
                    total_level=total_level,
                    cards=cards,
                )
            )

        scored.sort(
            key=lambda d: (
                d.owned_cards_count,
                d.total_level,
            ),
            reverse=True,
        )

        return scored[:limit]



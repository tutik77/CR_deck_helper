from typing import Any, Dict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .models import Deck
from .services import (
    ClashRoyaleAPI,
    ClashRoyaleAPIError,
    DeckRecommender,
    PlayerNotFoundError,
)


def index(request):
    return render(request, "app/index.html")


def decks(request):
    decks = Deck.objects.prefetch_related("deck_cards__card").all()
    return render(request, "app/decks.html", {"decks": decks})


@require_http_methods(["GET", "POST"])
def recommend_deck(request):
    context: Dict[str, Any] = {}
    context["debug_mode"] = settings.DEBUG or request.GET.get("debug") == "1"

    if request.method == "POST":
        player_tag = request.POST.get("player_tag", "").strip()
        context["player_tag"] = player_tag

        if not player_tag:
            context["error"] = "Введите тег игрока."
        else:
            api = None
            try:
                api = ClashRoyaleAPI()
            except ImproperlyConfigured as exc:
                context["error"] = str(exc)

            if api is not None and "error" not in context:
                recommender = DeckRecommender()
                try:
                    player = api.get_player(player_tag)
                    context["player"] = player

                    all_decks = Deck.objects.prefetch_related(
                        "deck_cards__card"
                    ).all()
                    recommendations = recommender.recommend(player, all_decks, limit=3)

                    context["recommendations"] = recommendations

                    if not recommendations:
                        context[
                            "info"
                        ] = "Для вашего профиля пока нет подходящих колод."
                except PlayerNotFoundError as exc:
                    context["error"] = str(exc)
                except ClashRoyaleAPIError as exc:
                    context["error"] = str(exc)

    return render(request, "app/recommend.html", context)


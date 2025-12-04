from django.core.management.base import BaseCommand
from django.core.management import call_command
from app.models import Card, Deck

class Command(BaseCommand):
    help = "Cleans the database and repopulates it with cards and decks."

    def handle(self, *args, **options):
        self.stdout.write("Cleaning database...")
        
        # Delete Decks first to avoid foreign key issues (though cascade should handle it)
        deleted_decks, _ = Deck.objects.all().delete()
        self.stdout.write(f"Deleted {deleted_decks} decks.")
        
        deleted_cards, _ = Card.objects.all().delete()
        self.stdout.write(f"Deleted {deleted_cards} cards.")
        
        self.stdout.write("Database cleaned. Starting repopulation...")
        
        self.stdout.write("Importing cards...")
        call_command("import_cards")
        
        self.stdout.write("Importing decks from StatsRoyale (local file)...")
        call_command("import_statsroyale_decks", file=r"..\page.html")
        
        self.stdout.write(self.style.SUCCESS("Successfully repopulated the database."))

from django.core.management.base import BaseCommand, CommandError

from knowledge.services.embeddings import rebuild_embeddings


class Command(BaseCommand):
    help = "Build or refresh semantic vectors for all active knowledge-base entries."

    def handle(self, *args, **options):
        try:
            count = rebuild_embeddings()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Built embeddings for {count} entries."))

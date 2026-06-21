import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from knowledge.models import KnowledgeBase, KnowledgeCategory


class Command(BaseCommand):
    help = "Idempotently seed the NSE knowledge base from the generated 200-entry dataset."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=Path, default=settings.REPO_ROOT / "backend" / "data" / "nse_kb_200.json")

    @transaction.atomic
    def handle(self, *args, **options):
        source = options["file"]
        if not source.exists():
            raise CommandError(f"Knowledge-base seed file not found: {source}")
        entries = json.loads(source.read_text(encoding="utf-8"))
        created = updated = 0
        for item in entries:
            category_name = item["category"].strip()
            category, _ = KnowledgeCategory.objects.get_or_create(
                name=category_name,
                defaults={"slug": slugify(category_name)},
            )
            keywords = item.get("keywords", [])
            if isinstance(keywords, list):
                keywords = ", ".join(keywords)
            _, was_created = KnowledgeBase.objects.update_or_create(
                question=item["question"].strip(),
                defaults={
                    "category": category,
                    "answer": item["answer"].strip(),
                    "tags": item.get("tags", []),
                    "keywords": keywords,
                    "difficulty": item.get("difficulty", KnowledgeBase.Difficulty.BEGINNER),
                    "is_active": True,
                },
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(entries)} entries ({created} created, {updated} updated)."))

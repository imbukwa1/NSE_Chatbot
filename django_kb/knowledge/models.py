from django.db import models


class KnowledgeCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "knowledge categories"

    def __str__(self):
        return self.name


class KnowledgeBase(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    category = models.ForeignKey(KnowledgeCategory, on_delete=models.PROTECT, related_name="entries")
    question = models.CharField(max_length=300, unique=True, db_index=True)
    answer = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    keywords = models.TextField(blank=True, help_text="Comma-separated search terms")
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.BEGINNER, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("category__name", "question")
        indexes = [models.Index(fields=("category", "is_active", "difficulty"))]

    def __str__(self):
        return self.question


class KnowledgeSynonym(models.Model):
    entry = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name="synonyms")
    phrase = models.CharField(max_length=300, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("entry", "phrase"), name="unique_entry_synonym")]

    def __str__(self):
        return self.phrase


class QueryLog(models.Model):
    query = models.TextField()
    matched_entry = models.ForeignKey(KnowledgeBase, null=True, blank=True, on_delete=models.SET_NULL, related_name="query_logs")
    strategy = models.CharField(max_length=30, default="none", db_index=True)
    confidence = models.FloatField(default=0.0)
    used_fallback = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.query[:80]

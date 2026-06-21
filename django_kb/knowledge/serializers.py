from rest_framework import serializers

from .models import KnowledgeBase


class KnowledgeSearchResultSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name")

    class Meta:
        model = KnowledgeBase
        fields = ("id", "category", "question", "answer", "tags", "difficulty")

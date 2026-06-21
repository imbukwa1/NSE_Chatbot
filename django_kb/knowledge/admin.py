from django.contrib import admin

from .models import KnowledgeBase, KnowledgeCategory, KnowledgeSynonym, QueryLog


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


class KnowledgeSynonymInline(admin.TabularInline):
    model = KnowledgeSynonym
    extra = 0


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "difficulty", "is_active", "updated_at")
    list_filter = ("category", "difficulty", "is_active")
    search_fields = ("question", "answer", "keywords")
    inlines = (KnowledgeSynonymInline,)


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ("query", "strategy", "confidence", "used_fallback", "created_at")
    list_filter = ("strategy", "used_fallback")
    search_fields = ("query",)
    readonly_fields = ("query", "matched_entry", "strategy", "confidence", "used_fallback", "created_at")


admin.site.site_header = "NSE AI Advisor Knowledge Base"

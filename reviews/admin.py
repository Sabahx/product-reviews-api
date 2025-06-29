from django.contrib import admin
from .models import Product, Review, BannedWord

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'created_at']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'visible', 'created_at', 'contains_banned_words', 'sentiment']
    list_filter = ['visible', 'rating', 'contains_banned_words', 'sentiment']
    search_fields = ['review_text', 'user__username', 'banned_words_found']
    readonly_fields = ['sentiment', 'sentiment_score', 'contains_banned_words', 'banned_words_found']

# Laith: Added BannedWord admin to manage inappropriate content filtering
@admin.register(BannedWord)
class BannedWordAdmin(admin.ModelAdmin):
    list_display = ['word', 'severity', 'created_at']
    list_filter = ['severity', 'created_at']
    search_fields = ['word']


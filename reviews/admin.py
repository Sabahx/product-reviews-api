from django.contrib import admin
from .models import Product, Review 
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'created_at']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'visible', 'created_at']
    list_filter = ['visible', 'rating']
    search_fields = ['review_text', 'user__username']


from django.contrib import admin
from .models import Product, Review, ReviewComment, BannedWord
from django.db.models import Q, Count

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'created_at']
    
    
# List of offensive words to filter
BANNED_WORDS = BannedWord.objects.all()

class OffensiveContentFilter(admin.SimpleListFilter):
    title = 'offensive content'
    parameter_name = 'offensive'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Has offensive words'),
            ('no', 'No offensive words'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            offensive_filter = Q()
            for word in BANNED_WORDS:
                offensive_filter |= Q(review_text__icontains=word)
            return queryset.filter(offensive_filter)
        elif self.value() == 'no':
            offensive_filter = Q()
            for word in BANNED_WORDS:
                offensive_filter |= Q(review_text__icontains=word)
            return queryset.exclude(offensive_filter)
        return queryset
    
class ReviewCommentInline(admin.TabularInline):
    model = ReviewComment
    extra = 0
    readonly_fields = ('user', 'text', 'created_at')
 
# Laith: Added BannedWord admin to manage inappropriate content filtering
@admin.register(BannedWord)
class BannedWordAdmin(admin.ModelAdmin):
    list_display = ['word', 'severity', 'created_at']
    list_filter = ['severity', 'created_at']
    search_fields = ['word']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating',  'sentiment', 'visible', 'has_offensive_content', 
                    'likes_count_display']
    list_filter = ['visible', 'rating', 'sentiment', 'created_at', OffensiveContentFilter]
    list_editable = ('visible',)
    search_fields = ['review_text', 'user__username', 'product__name', 'banned_words_found']
    inlines = [ReviewCommentInline]
    readonly_fields = ('sentiment', 'likes_count_display', 'created_at','sentiment_score', 'contains_banned_words', 'banned_words_found')

    fieldsets = (
        (None, {
            'fields': ('user', 'product', 'rating', 'sentiment')
        }),
        ('Review Content', {
            'fields': ('review_text', 'visible', 'likes_count_display')
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    # Custom method to display likes count in admin
    def likes_count_display(self, obj):
        return obj.likes_count()
    likes_count_display.short_description = 'Likes Count'

    # Custom method to check for offensive content
    def has_offensive_content(self, obj):
        return any(word.lower() in obj.review_text.lower() for word in BANNED_WORDS)
    has_offensive_content.boolean = True
    has_offensive_content.short_description = 'Offensive?'
    
        # Add insights to the change list view
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Get the base queryset
        qs = self.get_queryset(request)
        
        # Add insights to the context
        extra_context['hidden_count'] = qs.filter(visible=False).count()
        extra_context['low_rating_count'] = qs.filter(rating__in=[1, 2]).count()
        
        # Count offensive words in current filtered set
        offensive_filter = Q()
        for word in BANNED_WORDS:
            offensive_filter |= Q(review_text__icontains=word)
        extra_context['offensive_count'] = qs.filter(offensive_filter).count()
        
        # Sentiment distribution
        sentiment_stats = qs.values('sentiment').annotate(count=Count('sentiment'))
        extra_context['sentiment_stats'] = {stat['sentiment']: stat['count'] for stat in sentiment_stats}
        
        return super().changelist_view(request, extra_context=extra_context)
    
@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'review', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'user__username', 'review__product__name')
    readonly_fields = ('user', 'review', 'created_at')
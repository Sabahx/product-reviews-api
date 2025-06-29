from django.db import models
from django.contrib.auth.models import User
from textblob import TextBlob
from django.utils import timezone
from datetime import timedelta
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Laith: Added BannedWord model to filter inappropriate content in reviews
class BannedWord(models.Model):
    SEVERITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]
    
    word = models.CharField(max_length=100, unique=True)
    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Banned Word'
        verbose_name_plural = 'Banned Words'
        
    def __str__(self):
        return self.word

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    visible = models.BooleanField(default=False)
    #mjd
    sentiment = models.CharField(max_length=10, blank=True)
    # Laith: Added fields for banned words detection
    contains_banned_words = models.BooleanField(default=False)
    banned_words_found = models.TextField(blank=True, null=True)
    sentiment_score = models.FloatField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # تحليل العاطفة تلقائيًا
        analysis = TextBlob(self.review_text)
        polarity = analysis.sentiment.polarity
        self.sentiment_score = polarity
        
        if polarity > 0.1:
            self.sentiment = 'Positive'
        elif polarity < -0.1:
            self.sentiment = 'Negative'
        else:
            self.sentiment = 'Neutral'
            
        # Laith: Check for banned words in the review text
        banned_words = BannedWord.objects.all()
        found_words = []
        
        for banned in banned_words:
            if banned.word.lower() in self.review_text.lower():
                found_words.append(banned.word)
        
        if found_words:
            self.contains_banned_words = True
            self.banned_words_found = ', '.join(found_words)
        else:
            self.contains_banned_words = False
            self.banned_words_found = None
            
        super().save(*args, **kwargs)
        
    def likes_count(self):
        return self.interactions.filter(helpful=True).count()
    #mjd
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}"

# Advanced Features
class ReviewComment(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "comment on the review"
        verbose_name_plural = "comments on the reviews"
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.review}"
class ReviewVote(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    helpful = models.BooleanField()  # True for helpful, False for not helpful
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'user']
        verbose_name = "Vote on the review"
        verbose_name_plural = "Votes on reviews"
    
    def __str__(self):
        return f"{self.user.username} voted {'helpful' if self.helpful else 'not helpful'} for {self.review}"

#task8 
#mjd
class ReviewInteraction(models.Model):
    review = models.ForeignKey(Review, related_name='interactions', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    helpful = models.BooleanField()  # True = مفيد، False = غير مفيد
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'user')
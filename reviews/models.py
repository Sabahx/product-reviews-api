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

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    visible = models.BooleanField(default=False)
    #mjd
    sentiment = models.CharField(max_length=10, blank=True)
    def save(self, *args, **kwargs):
        # تحليل العاطفة تلقائيًا
        analysis = TextBlob(self.review_text)
        polarity = analysis.sentiment.polarity
        if polarity > 0.1:
            self.sentiment = 'Positive'
        elif polarity < -0.1:
            self.sentiment = 'Negative'
        else:
            self.sentiment = 'Neutral'
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
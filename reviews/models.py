from django.db import models
from django.contrib.auth.models import User
from textblob import TextBlob
from django.utils import timezone
from datetime import timedelta

# 🟢 نموذج يمثل المنتج الذي يُكتب عليه المراجعات
class Product(models.Model):
    name = models.CharField(max_length=255)  # اسم المنتج
    description = models.TextField()  # وصف المنتج
    price = models.DecimalField(max_digits=10, decimal_places=2)  # سعر المنتج
    created_at = models.DateTimeField(auto_now_add=True)  # تاريخ إنشاء المنتج
    image = models.ImageField(upload_to='products/', null=True, blank=True)  # صورة المنتج (اختياري)

    def __str__(self):
        return self.name

# ✅ نموذج للكلمات الممنوعة التي يتم فحصها داخل المراجعات (مع درجة خطورتها وخيار الاستبدال)
# Laith: Added BannedWord model to filter inappropriate content in reviews 
# edited by sabah 
class BannedWord(models.Model):
    SEVERITY_CHOICES = [
        (1, 'Low'),      # منخفضة
        (2, 'Medium'),   # متوسطة
        (3, 'High'),     # عالية
    ]
    word = models.CharField(max_length=100, unique=True)  # الكلمة المحظورة
    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=1)  # شدة الحظر
    replacement = models.CharField(max_length=100, default='[delet-content]')  # استبدال الكلمة
    created_at = models.DateTimeField(auto_now_add=True)  # تاريخ الإضافة

    class Meta:
        verbose_name = 'Banned Word'
        verbose_name_plural = 'Banned Words'

    def __str__(self):
        return self.word

# ✅ نموذج المراجعات المرتبطة بالمنتجات والمستخدمين
class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)  # المنتج المعني
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # المستخدم الذي كتب المراجعة
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])  # التقييم من 1 إلى 5
    review_text = models.TextField()  # نص المراجعة
    created_at = models.DateTimeField(auto_now_add=True)  # وقت الكتابة
    visible = models.BooleanField(default=False)  # هل المراجعة ظاهرة للمستخدمين أم لا (تحتاج موافقة مثلًا)
    #comments = models.ForeignKey('ReviewComment', related_name='comments', on_delete=models.CASCADE)
    # mjd task9⬇
    # views = models.ForeignKey(ReviewView, related_name='reviews', on_delete=models.CASCADE) # عدد مرات المشاهدة للمراجعة
    sentiment = models.CharField(max_length=10, blank=True)  # الحالة العاطفية: إيجابي/سلبي/محايد (تحليل آلي)

    # Laith: Added fields for banned words detection
    contains_banned_words = models.BooleanField(default=False)  # هل تحتوي على كلمات محظورة
    banned_words_found = models.TextField(blank=True, null=True)  # عرض الكلمات المحظورة التي وُجدت
    sentiment_score = models.FloatField(blank=True, null=True)  # قيمة تحليل العاطفة العددي (polarity)

    def save(self, *args, **kwargs):
        # تحليل عاطفي تلقائي باستخدام TextBlob
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
    
    @property
    def likes(self):
        return self.interactions.filter(helpful=True).count()

    @property
    def dislikes(self):
        return self.interactions.filter(helpful=False).count()
    
    def user_vote(self, user):
        try:
            return self.interactions.get(user=user).helpful
        except ReviewInteraction.DoesNotExist:
            return None

    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}"

# ✅ نموذج للتعليق على مراجعة معينة
class ReviewComment(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')  # المراجعة الهدف
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # المعلق
    text = models.TextField()  # نص التعليق
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "comment on the review"
        verbose_name_plural = "comments on the reviews"

    def __str__(self):
        return f"Comment by {self.user.username} on {self.review}"

# ✅ نموذج لتقييم المراجعة هل كانت مفيدة أو لا
class ReviewVote(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='votes')  # المراجعة الهدف
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # المستخدم المصوّت
    helpful = models.BooleanField()  # هل وجدها مفيدة (True) أم لا (False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['review', 'user']  # لا يمكن أن يصوّت نفس المستخدم على نفس المراجعة مرتين
        verbose_name = "Vote on the review"
        verbose_name_plural = "Votes on reviews"

    def __str__(self):
        return f"{self.user.username} voted {'helpful' if self.helpful else 'not helpful'} for {self.review}"

# task8 - mjd
# ✅ نظام التفاعل مع المراجعات (إعجاب أو عدم إعجاب)
class ReviewInteraction(models.Model):
    review = models.ForeignKey(Review, related_name='interactions', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    helpful = models.BooleanField()  # True = مفيد، False = غير مفيد
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'user')
    
    def __str__(self):
        return f"{self.user.username} {'liked' if self.helpful else 'disliked'} review {self.review.id}"

# ✅ إشعارات للمستخدمين (مثلاً: أحدهم علّق على مراجعتك، أو أعجب بها)
class Notification(models.Model):
    user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)  # المستخدم المستهدف بالإشعار
    message = models.TextField()  # نص الإشعار
    read = models.BooleanField(default=False)  # هل قرأ الإشعار؟
    created_at = models.DateTimeField(auto_now_add=True)
    related_review = models.ForeignKey(Review, null=True, blank=True, on_delete=models.SET_NULL)  # إن كان متعلقًا بمراجعة

    class Meta:
        ordering = ['-created_at']  # الترتيب من الأحدث إلى الأقدم

# mjd task9⬇
# ✅ نظام التبليغ عن المراجعات (مثلاً إذا كانت مسيئة أو تحتوي محتوى غير مناسب)
class ReviewReport(models.Model):
    review = models.ForeignKey(Review, related_name='reports', on_delete=models.CASCADE)  # المراجعة المبلغ عنها
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # المستخدم الذي قام بالتبليغ
    reason = models.TextField()  # سبب التبليغ
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['review', 'user']  # لا يمكن تبليغ نفس المراجعة من نفس المستخدم أكثر من مرة
        
class ReviewView(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # Null if anonymous
    ip_address = models.CharField(max_length=45, blank=True)  # Store IP for anonymous users
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'user', 'ip_address')  # Prevent duplicate views

    def __str__(self):
        return f"{self.user or self.ip_address} viewed review {self.review.id}"
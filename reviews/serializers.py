from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from django.contrib.auth import get_user_model
from .models import (
    Product,
    Review,
    ReviewReport,
    BannedWord,
    ReviewComment,
    ReviewVote,
    ReviewInteraction,
    Notification
)

User = get_user_model()  # للحصول على موديل المستخدم المخصص

# ✅ سيريالايزر لعرض تفاصيل المنتج مع تقييمه وعدد مراجعاته
class ProductSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(read_only=True)  # التقييم المتوسط (يتم احتسابه من الـ View)
    reviews_count = serializers.IntegerField(read_only=True)  # عدد المراجعات

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'average_rating', 'reviews_count']

# ✅ سيريالايزر لعرض تفاصيل المراجعة مع معلومات إضافية عنها (عدد الإعجابات، هل المستخدِم تفاعل، الخ...)
class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)  # عرض اسم المستخدم بدلاً من ID
    views = serializers.IntegerField(read_only=True)

    # حقول محسوبة إضافية
    likes = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()
    has_report = serializers.SerializerMethodField()
    user_interacted = serializers.SerializerMethodField()
    user_voted = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'product', 'user', 'rating', 'review_text',
            'created_at', 'visible', 'likes', 'dislikes', 'views',
            'has_report', 'user_interacted','user_voted'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'visible']

    # task 9 section 5 (sabah)

    def get_likes(self, obj):
        return obj.interactions.filter(helpful=True).count()  # عدد التفاعلات المفيدة

    def get_dislikes(self, obj):
        return obj.interactions.filter(helpful=False).count()  # عدد التفاعلات غير المفيدة

    def get_has_report(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.reports.filter(user=user).exists()  # هل المستخدم الحالي أبلغ عن هذه المراجعة؟
        return False

    def get_user_interacted(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.interactions.filter(user=user).exists()  # هل تفاعل المستخدم مع المراجعة؟
        return False

    def get_user_voted(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            vote = obj.votes.filter(user=user).first()
            if vote:
                return "helpful" if vote.helpful else "not_helpful"
        return None

# ✅ سيريالايزر لتسجيل مستخدم جديد
class RegisterSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}  # عدم إظهار الباسورد في الـ response

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

# ✅ سيريالايزر لتعليقات المراجعات
class ReviewCommentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # المستخدم (ID فقط)
    username = serializers.CharField(source='user.username', read_only=True)  # اسم المستخدم
    review = serializers.PrimaryKeyRelatedField(read_only=True)  # رقم المراجعة

    class Meta:
        model = ReviewComment
        fields = ['id', 'review', 'user', 'username', 'text', 'created_at']
        read_only_fields = ['id', 'user', 'review', 'created_at']

    def create(self, validated_data):
        # يتم ضبط user و review داخل الـ view نفسه
        return ReviewComment.objects.create(**validated_data)

# ✅ سيريالايزر لتقييم مفيد/غير مفيد على مراجعة
class ReviewVoteSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    review = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ReviewVote
        fields = ['id', 'review', 'user', 'username', 'helpful', 'created_at']
        read_only_fields = ['id', 'user', 'review', 'created_at']

    def validate(self, data):
        # التحقق من أن المستخدم لم يصوّت مسبقًا (التحكم الأساسي بالـ view)
        return data

    def create(self, validated_data):
        return ReviewVote.objects.create(**validated_data)

# mjd⬇
# ✅ سيريالايزر لتفاعل المستخدم مع مراجعة (مفيد / غير مفيد)
class ReviewInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewInteraction
        fields = ['id', 'review', 'user', 'helpful', 'created_at']
        read_only_fields = ['user', 'created_at']
#⬆

# ✅ سيريالايزر للكلمات الممنوعة (للإدارة)
# Laith: Added serializer for BannedWord model
class BannedWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannedWord
        fields = ['id', 'word', 'severity', 'created_at']
        read_only_fields = ['created_at']

# ✅ سيريالايزر للإشعارات
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'read', 'created_at', 'related_review']

# mjd task 9⬇
# ✅ سيريالايزر للتبليغ عن مراجعة
class ReviewReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReport
        fields = ['id', 'review', 'user', 'reason', 'created_at']
        read_only_fields = ['user', 'created_at']

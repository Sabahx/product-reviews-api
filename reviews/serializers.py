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


User = get_user_model()



class ProductSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'average_rating', 'reviews_count']

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    views = serializers.IntegerField(read_only=True)

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
    #task 9 section 5 (sabah)
    def get_likes(self, obj):
        return obj.interactions.filter(helpful=True).count()

    def get_dislikes(self, obj):
        return obj.interactions.filter(helpful=False).count()

    def get_has_report(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.reports.filter(user=user).exists()
        return False

    def get_user_interacted(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.interactions.filter(user=user).exists()
        return False
    def get_user_voted(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
          vote = obj.votes.filter(user=user).first()
          if vote:
            return "helpful" if vote.helpful else "not_helpful"
        return None


class RegisterSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    


class ReviewCommentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    review = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ReviewComment
        fields = ['id', 'review', 'user', 'username', 'text', 'created_at']
        read_only_fields = ['id', 'user', 'review', 'created_at']

    def create(self, validated_data):
        # The review and user are set in the view
        return ReviewComment.objects.create(**validated_data)


class ReviewVoteSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    review = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ReviewVote
        fields = ['id', 'review', 'user', 'username', 'helpful', 'created_at']
        read_only_fields = ['id', 'user', 'review', 'created_at']

    def validate(self, data):
        """
        Check that the user hasn't already voted on this review.
        The view handles updating existing votes, but we can add validation here if needed.
        """
        return data

    def create(self, validated_data):
        # The review and user are set in the view
        return ReviewVote.objects.create(**validated_data)

#mjd⬇
class ReviewInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewInteraction
        fields = ['id', 'review', 'user', 'helpful', 'created_at']
        read_only_fields = ['user', 'created_at']

##⬆


# Laith: Added serializer for BannedWord model
class BannedWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannedWord
        fields = ['id', 'word', 'severity', 'created_at']
        read_only_fields = ['created_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'read', 'created_at', 'related_review']

#mjd task 9⬇
class ReviewReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReport
        fields = ['id', 'review', 'user', 'reason', 'created_at']
        read_only_fields = ['user', 'created_at']


# your_app/serializers.py
from rest_framework import serializers
<<<<<<< HEAD
from .models import Product, Review, Notification
=======
from .models import Product, Review
>>>>>>> 0d4e224f4b88d804c64f252921113f09f81b3a50
from rest_framework.serializers import ModelSerializer
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import ReviewComment, ReviewVote
from django.contrib.auth import get_user_model

User = get_user_model()

<<<<<<< HEAD
=======


>>>>>>> 0d4e224f4b88d804c64f252921113f09f81b3a50
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ['product', 'user', 'rating', 'review_text', 'created_at', 'visible']
        read_only_fields = ['user', 'created_at', 'visible']

class RegisterSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
<<<<<<< HEAD
=======


>>>>>>> 0d4e224f4b88d804c64f252921113f09f81b3a50
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

<<<<<<< HEAD
=======

>>>>>>> 0d4e224f4b88d804c64f252921113f09f81b3a50
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
<<<<<<< HEAD

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['id', 'review', 'message', 'is_read', 'created_at']
=======
>>>>>>> 0d4e224f4b88d804c64f252921113f09f81b3a50

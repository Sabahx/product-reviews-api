# your_app/serializers.py
from rest_framework import serializers
from .models import Product, Review
from rest_framework.serializers import ModelSerializer
from django.contrib.auth.models import User




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

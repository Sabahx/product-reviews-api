from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Product, Review

User = get_user_model()

class ReviewSystemTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=100.00
        )
        
        # الحصول على token للمستخدمين
        self.admin_token = self.get_token('admin', 'testpass123')
        self.user1_token = self.get_token('user1', 'testpass123')
        self.user2_token = self.get_token('user2', 'testpass123')
    
    def get_token(self, username, password):
        response = self.client.post(
            '/api/token/',
            {'username': username, 'password': password},
            format='json'
        )
        return response.data['access']
    
    def test_create_review(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user1_token}')
        data = {
            'product': self.product.id,
            'rating': 5,
            'text': 'Great product!'
        }
        response = self.client.post('/api/reviews/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().text, 'Great product!')
    
    def test_cannot_modify_others_review(self):
        # إنشاء مراجعة بواسطة user1
        review = Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=4,
            text='Good product'
        )
        
        # محاولة تعديل المراجعة بواسطة user2
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user2_token}')
        data = {'text': 'Modified review'}
        response = self.client.patch(f'/api/reviews/{review.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_average_rating_calculation(self):
        # إنشاء عدة تقييمات للمنتج
        Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            text='Excellent',
            is_approved=True
        )
        Review.objects.create(
            product=self.product,
            user=self.user2,
            rating=3,
            text='Average',
            is_approved=True
        )
        
        # الحصول على تفاصيل المنتج
        response = self.client.get(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['average_rating'], 4.0)
        self.assertEqual(response.data['reviews_count'], 2)
    
    def test_admin_can_approve_reviews(self):
        # إنشاء مراجعة غير معتمدة
        review = Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            text='Excellent',
            is_approved=False
        )
        
        # الموافقة على المراجعة بواسطة المشرف
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        data = {'is_approved': True}
        response = self.client.patch(f'/api/reviews/{review.id}/approve_review/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Review.objects.get(id=review.id).is_approved)
        
        # محاولة الموافقة بواسطة مستخدم عادي
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user2_token}')
        response = self.client.patch(f'/api/reviews/{review.id}/approve_review/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_filter_reviews_by_rating(self):
        # إنشاء تقييمات مختلفة
        Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            text='Excellent',
            is_approved=True
        )
        Review.objects.create(
            product=self.product,
            user=self.user2,
            rating=3,
            text='Average',
            is_approved=True
        )
        
        # تصفية التقييمات بدرجة 5 نجوم
        response = self.client.get(f'/api/products/{self.product.id}/reviews/?rating=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['rating'], 5)
# Create your tests here.

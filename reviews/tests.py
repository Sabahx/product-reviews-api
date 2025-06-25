from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Product, Review
from django.utils import timezone
from datetime import timedelta


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
            'review_text': 'Great product!'
        }
        response = self.client.post('/api/reviews/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().review_text, 'Great product!')

    def test_cannot_modify_others_review(self):
        review = Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=4,
            review_text='Good product'
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user2_token}')
        data = {'review_text': 'Modified review'}
        response = self.client.patch(f'/api/reviews/{review.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_average_rating_calculation(self):
        Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            review_text='Excellent',
            visible=True
        )
        Review.objects.create(
            product=self.product,
            user=self.user2,
            rating=3,
            review_text='Average',
            visible=True
        )
        response = self.client.get(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['average_rating'], 4.0)
        self.assertEqual(response.data['reviews_count'], 2)

    def test_admin_can_approve_reviews(self):
        review = Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            review_text='Excellent',
            visible=False
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        data = {'visible': True}
        response = self.client.patch(f'/api/reviews/{review.id}/approve_review/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Review.objects.get(id=review.id).visible)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user2_token}')
        response = self.client.patch(f'/api/reviews/{review.id}/approve_review/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_reviews_by_rating(self):
        Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            review_text='Excellent',
            visible=True
        )
        Review.objects.create(
            product=self.product,
            user=self.user2,
            rating=3,
            review_text='Average',
            visible=True
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user1_token}')
        response = self.client.get(f'/api/reviews/?product={self.product.id}&rating=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['rating'], 5)


# Task 8 - Analytics Section Tests (Sabah)

class ReviewAnalyticsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.product1 = Product.objects.create(name="P1", description="D", price=50)
        self.product2 = Product.objects.create(name="P2", description="D", price=60)

        Review.objects.create(product=self.product1, user=self.user1, rating=5, review_text="Excellent", visible=True)
        Review.objects.create(product=self.product1, user=self.user2, rating=4, review_text="Good value", visible=True, created_at=timezone.now() - timedelta(days=10))
         # 💡 الطريقة الصحيحة لضبط created_at هي باستخدام update بعد الحفظ
        old_review = Review.objects.create(product=self.product2, user=self.user2, rating=2, review_text="Bad", visible=True)
        Review.objects.filter(pk=old_review.pk).update(created_at=timezone.now() - timedelta(days=35))

    def test_product_analytics_average(self):
        response = self.client.get(f'/api/products/{self.product1.id}/analytics/?days=30')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['review_count_last_days'], 2)
        self.assertTrue(4.0 <= response.data['average_rating_last_days'] <= 5.0)

    def test_top_reviewers(self):
        response = self.client.get('/api/analytics/top-reviewers/')
        self.assertEqual(response.status_code, 200)
        usernames = [u['username'] for u in response.data]
        self.assertIn('user1', usernames)
        self.assertIn('user2', usernames)

    def test_top_rated_products(self):
        response = self.client.get('/api/analytics/top-products/?days=30')
        self.assertEqual(response.status_code, 200)
        names = [p['product_name'] for p in response.data]
        self.assertIn('P1', names)
        self.assertNotIn('P2', names)

    def test_search_reviews_keyword(self):
        response = self.client.get('/api/analytics/search-reviews/?q=Excellent')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text'], "Excellent")

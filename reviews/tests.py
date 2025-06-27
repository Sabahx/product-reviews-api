from django.test import Client, TestCase
from django.contrib.auth.models import User
from django.urls import reverse
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
#########           ⬇⬇⬇⬇⬇⬇⬇⬇(mjd)⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from reviews.models import Product, Review, ReviewInteraction
from rest_framework import status

class ReviewInteractionTestCase(TestCase):
    def setUp(self):
    # 1. إنشاء مستخدمين
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.user3 = User.objects.create_user(username='user3', password='pass123')

        # 2. إنشاء منتج ومراجعتين
        self.product = Product.objects.create(name='Laptop', description='Good', price=5000)
        self.review1 = Review.objects.create(product=self.product, user=self.user1, rating=5, review_text='ممتاز', visible=True)
        self.review2 = Review.objects.create(product=self.product, user=self.user2, rating=2, review_text='سيء', visible=True)

        # 3. إنشاء APIClient بعد إنشاء المستخدمين
        self.client = APIClient()

        # 4. تسجيل دخول user3 عبر JWT
        response = self.client.post('/api/token/', {'username': 'user3', 'password': 'pass123'})
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)
        print("TOKEN:", self.token)

    # 1. اختبار تقييم المراجعة بأنها مفيدة أو غير مفيدة:

    def test_user_can_mark_review_as_helpful(self):
        response = self.client.post(f'/api/reviews/{self.review1.id}/interact/', {'helpful': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(ReviewInteraction.objects.filter(review=self.review1, user=self.user3, helpful=True).exists())

    def test_user_can_mark_review_as_not_helpful(self):
        response = self.client.post(f'/api/reviews/{self.review2.id}/interact/', {'helpful': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(ReviewInteraction.objects.filter(review=self.review2, user=self.user3, helpful=False).exists())

    # 2. اختبار منع التفاعل المكرر (نفس المستخدم يقيّم المراجعة مرتين):

"""    def test_user_can_update_review_interaction(self):
        self.client.post(f'/api/reviews/{self.review1.id}/interact/', {'helpful': True})
        self.client.post(f'/api/reviews/{self.review1.id}/interact/', {'helpful': False})
        ReviewInteraction.objects.create(review=self.review1, user=self.user3, helpful=True)
        interaction = ReviewInteraction.objects.get(review=self.review1, user=self.user3)
        self.assertFalse(interaction.helpful)  # تم التحديث وليس الإنشاء من جديد"""
def test_user_can_update_review_interaction(self):
    self.client.post(f'/api/reviews/{self.review1.id}/interact/', {'helpful': True})
    self.client.post(f'/api/reviews/{self.review1.id}/interact/', {'helpful': False})
    interaction = ReviewInteraction.objects.get(review=self.review1, user=self.user3)
    self.assertFalse(interaction.helpful)  # تم التحديث وليس الإنشاء من جديد"""


    # 3. اختبار عدد الإعجابات وعدم الإعجاب يظهر في Serializer:

    def test_likes_dislikes_counts(self):
        ReviewInteraction.objects.create(review=self.review1, user=self.user3, helpful=True)
        ReviewInteraction.objects.create(review=self.review1, user=self.user2, helpful=True)
        ReviewInteraction.objects.create(review=self.review1, user=self.user1, helpful=False)

        response = self.client.get(f'/api/reviews/{self.review1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['likes'], 2)
        self.assertEqual(response.data['dislikes'], 1)

    #4. اختبار أفضل مراجعة (Top Review):

    def test_top_review_endpoint(self):
        # review1: 2 likes
        ReviewInteraction.objects.create(review=self.review1, user=self.user2, helpful=True)
        ReviewInteraction.objects.create(review=self.review1, user=self.user3, helpful=True)

        # review2: 1 like
        ReviewInteraction.objects.create(review=self.review2, user=self.user1, helpful=True)

        response = self.client.get('/api/reviews/top-review/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.review1.id)
        self.assertEqual(response.data['likes'], 2)
####################################⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆

class ReviewAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@example.com'
        )
        self.client.force_login(self.admin_user)
        
        self.product = Product.objects.create(name='Test Product', price=9.99)
        self.user = User.objects.create_user(username='testuser', password='12345')
        
        # Create test reviews
        Review.objects.create(
            user=self.user,
            product=self.product,
            rating=5,
            review_text='Great product!',
            visible=True
        )
        Review.objects.create(
            user=self.user,
            product=self.product,
            rating=1,
            review_text='This is badword1 awful!',
            visible=False
        )

    def test_review_list_view(self):
        url = reverse('admin:reviews_review_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # self.assertContains(response, 'Great product!')
        self.assertContains(response, 'Test Product')   # product name
        self.assertContains(response, 'testuser')       # reviewer username
        self.assertContains(response, '5')              # rating (appears as a number)
        
    def test_offensive_filter(self):
        url = reverse('admin:reviews_review_changelist') + '?offensive=yes'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertContains(response, 'icon-yes.svg')  # indicates an offensive review
        # self.assertContains(response, 'badword1')
        # self.assertNotContains(response, 'Great product!')
        
    def test_visibility_toggle(self):
        review = Review.objects.get(rating=5)
        url = reverse('admin:reviews_review_change', args=[review.id])
        data = {
            'user': review.user.id,
            'product': review.product.id,
            'rating': review.rating,
            'review_text': review.review_text,
            'visible': False,  # Toggle visibility
            '_save': 'Save',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        updated_review = Review.objects.get(id=review.id)
        self.assertFalse(updated_review.visible)
        
    def test_insights_display(self):
        url = reverse('admin:reviews_review_changelist')
        response = self.client.get(url)
        self.assertContains(response, 'Review Insights')
        self.assertContains(response, 'Hidden Reviews')
        self.assertContains(response, 'By rating')
        self.assertContains(response, 'Offensive Content')
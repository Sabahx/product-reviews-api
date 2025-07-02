from django.test import Client, TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Product, Review, BannedWord, ReviewInteraction
from django.utils import timezone
from datetime import timedelta
import json


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

# Laith: Added test class for banned words functionality
class BannedWordsTestCase(APITestCase):
    def setUp(self):
        # Create admin user
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='user@example.com',
            password='userpassword'
        )
        
        # Create product
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=99.99
        )
        
        # Create banned words
        BannedWord.objects.create(word='inappropriate', severity=1)
        BannedWord.objects.create(word='offensive', severity=2)
        BannedWord.objects.create(word='vulgar', severity=3)
        
        # Create reviews with and without banned words
        self.clean_review = Review.objects.create(
            product=self.product,
            user=self.user,
            rating=4,
            review_text='This is a good product',
            visible=True
        )
        
        self.banned_review_low = Review.objects.create(
            product=self.product,
            user=self.user,
            rating=2,
            review_text='This is an inappropriate product',
            visible=True
        )
        
        self.banned_review_high = Review.objects.create(
            product=self.product,
            user=self.user,
            rating=1,
            review_text='This product is vulgar and offensive',
            visible=True
        )
        
        # Get tokens
        response = self.client.post('/api/token/', {
            'username': 'admin',
            'password': 'adminpassword'
        })
        self.admin_token = response.data['access']
        
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'userpassword'
        })
        self.user_token = response.data['access']
    
    def test_banned_words_detection(self):
        """Test that banned words are properly detected in reviews"""
        # Check that the banned words were properly detected during save
        self.clean_review.refresh_from_db()
        self.banned_review_low.refresh_from_db()
        self.banned_review_high.refresh_from_db()
        
        self.assertFalse(self.clean_review.contains_banned_words)
        self.assertIsNone(self.clean_review.banned_words_found)
        
        self.assertTrue(self.banned_review_low.contains_banned_words)
        self.assertEqual(self.banned_review_low.banned_words_found, 'inappropriate')
        
        self.assertTrue(self.banned_review_high.contains_banned_words)
        # The order might vary, so we check if both words are in the result
        self.assertIn('vulgar', self.banned_review_high.banned_words_found)
        self.assertIn('offensive', self.banned_review_high.banned_words_found)
    
    def test_banned_words_endpoint_admin_access(self):
        """Test that only admins can access the banned words endpoint"""
        # Admin should have access
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/admin/banned-word-reviews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should return both banned reviews
        
        # Regular user should not have access
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.get('/api/admin/banned-word-reviews/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_banned_words_filtering_by_severity(self):
        """Test filtering banned reviews by severity level"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Filter by low severity (should return only the 'inappropriate' review)
        response = self.client.get('/api/admin/banned-word-reviews/?severity=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['banned_words_found'], 'inappropriate')
        
        # Filter by high severity (should return only the review with 'vulgar')
        response = self.client.get('/api/admin/banned-word-reviews/?severity=3')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn('vulgar', response.data[0]['banned_words_found'])

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

    def test_user_can_update_review_interaction(self):
        self.client.post(f'/api/reviews/{self.review1.id}/interact/', {'helpful': True})
        self.client.post(f'/api/reviews/{self.review1.id}/interact/', {'helpful': False})
        interaction = ReviewInteraction.objects.get(review=self.review1, user=self.user3)
        self.assertFalse(interaction.helpful)  # تم التحديث وليس الإنشاء من جديد

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

# Laith: Added tests for sorting and filtering reviews
class ReviewSortingFilteringTestCase(APITestCase):
    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.user3 = User.objects.create_user(username='user3', password='pass123')
        
        # Create product
        self.product = Product.objects.create(name="Test Product", description="Test Description", price=50)
        
        # Create reviews with different ratings and dates
        # Review 1: Rating 5, newest
        self.review1 = Review.objects.create(
            product=self.product, 
            user=self.user1, 
            rating=5, 
            review_text="Excellent product!", 
            visible=True
        )
        
        # Review 2: Rating 3, older
        self.review2 = Review.objects.create(
            product=self.product, 
            user=self.user2, 
            rating=3, 
            review_text="Average product", 
            visible=True
        )
        Review.objects.filter(pk=self.review2.pk).update(created_at=timezone.now() - timedelta(days=5))
        
        # Review 3: Rating 4, oldest
        self.review3 = Review.objects.create(
            product=self.product, 
            user=self.user3, 
            rating=4, 
            review_text="Good product", 
            visible=True
        )
        Review.objects.filter(pk=self.review3.pk).update(created_at=timezone.now() - timedelta(days=10))
        
        # Create interactions to test most_interactive sorting
        # Review 1: 2 interactions
        ReviewInteraction.objects.create(review=self.review1, user=self.user2, helpful=True)
        ReviewInteraction.objects.create(review=self.review1, user=self.user3, helpful=True)
        
        # Review 3: 1 interaction
        ReviewInteraction.objects.create(review=self.review3, user=self.user1, helpful=True)

    def test_filter_by_rating(self):
        """Test filtering reviews by rating"""
        # Get only 5-star reviews
        response = self.client.get(f'/api/reviews/?product={self.product.id}&rating=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['rating'], 5)
        
        # Get only 3-star reviews
        response = self.client.get(f'/api/reviews/?product={self.product.id}&rating=3')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['rating'], 3)
        
        # Test invalid rating parameter
        response = self.client.get(f'/api/reviews/?product={self.product.id}&rating=invalid')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # Should return all reviews, ignoring invalid filter

    def test_sort_by_newest(self):
        """Test sorting reviews by creation date (newest first)"""
        response = self.client.get(f'/api/reviews/?product={self.product.id}&sort_by=newest')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # First review should be review1 (newest)
        self.assertEqual(response.data[0]['id'], self.review1.id)

    def test_sort_by_highest_rating(self):
        """Test sorting reviews by rating (highest first)"""
        response = self.client.get(f'/api/reviews/?product={self.product.id}&sort_by=highest_rating')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # First review should be review1 (rating 5)
        self.assertEqual(response.data[0]['rating'], 5)
        # Second review should be review3 (rating 4)
        self.assertEqual(response.data[1]['rating'], 4)
        # Third review should be review2 (rating 3)
        self.assertEqual(response.data[2]['rating'], 3)

    def test_sort_by_most_interactive(self):
        """Test sorting reviews by number of interactions"""
        response = self.client.get(f'/api/reviews/?product={self.product.id}&sort_by=most_interactive')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # First review should be review1 (2 interactions)
        self.assertEqual(response.data[0]['id'], self.review1.id)

    def test_combined_filter_and_sort(self):
        """Test combining filtering and sorting"""
        # Create another 5-star review that's older
        review4 = Review.objects.create(
            product=self.product, 
            user=self.user2, 
            rating=5, 
            review_text="Another excellent product!", 
            visible=True
        )
        Review.objects.filter(pk=review4.pk).update(created_at=timezone.now() - timedelta(days=15))
        
        # Filter by 5-star rating and sort by newest
        response = self.client.get(f'/api/reviews/?product={self.product.id}&rating=5&sort_by=newest')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # First review should be review1 (newer 5-star)
        self.assertEqual(response.data[0]['id'], self.review1.id)
        # Second review should be review4 (older 5-star)
        self.assertEqual(response.data[1]['id'], review4.id)

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

# Laith: Added tests for BannedWord API endpoints
class BannedWordAPITestCase(APITestCase):
    def setUp(self):
        # Create admin user
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='user@example.com',
            password='userpassword'
        )
        
        # Create some banned words
        self.banned_word1 = BannedWord.objects.create(word='inappropriate', severity=1)
        self.banned_word2 = BannedWord.objects.create(word='offensive', severity=2)
        self.banned_word3 = BannedWord.objects.create(word='vulgar', severity=3)
        
        # Create API client and authenticate admin
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
    
    def test_list_banned_words(self):
        """Test that admins can list banned words"""
        response = self.client.get('/api/admin/banned-words/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        words = [item['word'] for item in response.data]
        self.assertIn('inappropriate', words)
        self.assertIn('offensive', words)
        self.assertIn('vulgar', words)
    
    def test_create_banned_word(self):
        """Test that admins can create new banned words"""
        data = {
            'word': 'unacceptable',
            'severity': 2
        }
        response = self.client.post('/api/admin/banned-words/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BannedWord.objects.count(), 4)
        self.assertTrue(BannedWord.objects.filter(word='unacceptable').exists())
    
    def test_update_banned_word(self):
        """Test that admins can update banned words"""
        data = {
            'word': 'inappropriate',
            'severity': 3  # Change severity from 1 to 3
        }
        response = self.client.put(f'/api/admin/banned-words/{self.banned_word1.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.banned_word1.refresh_from_db()
        self.assertEqual(self.banned_word1.severity, 3)
    
    def test_delete_banned_word(self):
        """Test that admins can delete banned words"""
        response = self.client.delete(f'/api/admin/banned-words/{self.banned_word1.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(BannedWord.objects.count(), 2)
        self.assertFalse(BannedWord.objects.filter(word='inappropriate').exists())
    
    def test_non_admin_cannot_access(self):
        """Test that non-admin users cannot access banned words API"""
        self.client.force_authenticate(user=self.user)  # Switch to regular user
        
        # Test list
        response = self.client.get('/api/admin/banned-words/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test create
        data = {'word': 'test', 'severity': 1}
        response = self.client.post('/api/admin/banned-words/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test update
        response = self.client.put(f'/api/admin/banned-words/{self.banned_word2.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test delete
        response = self.client.delete(f'/api/admin/banned-words/{self.banned_word2.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)



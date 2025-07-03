from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from .models import Product, Review, ReviewInteraction

#task9 sabah
class ReviewDisplayTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)

        self.product = Product.objects.create(name='Test Product', description='Description', price=9.99)

        self.review = Review.objects.create(
            product=self.product,
            user=self.user,
            rating=4,
            review_text='Nice product',
            visible=True,
            views=5
        )

        # ✅ Add interaction (vote)
        ReviewInteraction.objects.create(
            review=self.review,
            user=self.user,
            helpful=True
        )

    def test_review_display_with_extras(self):
        response = self.client.get(f'/api/reviews/{self.review.id}/')  # تأكدي إن المسار صح
        self.assertEqual(response.status_code, 200)
        self.assertIn('views', response.data)
        self.assertEqual(response.data['views'], 6)
        self.assertIn('user_interacted', response.data)
        self.assertTrue(response.data['user_interacted'])

    def test_review_display_anonymous(self):
      client = APIClient()
      response = client.get(f'/api/reviews/{self.review.id}/')
      self.assertEqual(response.status_code, 200)
      self.assertFalse(response.data['user_interacted'])
      self.assertFalse(response.data['has_report'])


#task9 mjd

from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth.models import User
from reviews.models import Product, Review, ReviewReport
from rest_framework_simplejwt.tokens import RefreshToken

def setUp(self):
    self.user = User.objects.create_user(username='testuser', password='testpass')
    self.product = Product.objects.create(name='Test Product', price=9.99)
    self.review = Review.objects.create(product=self.product, user=self.user, rating=4, review_text='Nice review!')

    # JWT Auth
    refresh = RefreshToken.for_user(self.user)
    self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')


    def test_views_counter_increment(self):
        url = reverse('review-detail', args=[self.review.id])  # تأكد من اسم الراؤتر
        # Call retrieve multiple times
        self.client.get(url)
        self.client.get(url)

        self.review.refresh_from_db()
        self.assertEqual(self.review.views, 2)

    def test_report_review_success(self):
        self.client.login(username='testuser', password='testpass')
        url = reverse('review-report', args=[self.review.id])
        data = {"reason": "Spam content"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ReviewReport.objects.filter(review=self.review, user=self.user).exists())

    def test_report_review_duplicate(self):
        ReviewReport.objects.create(review=self.review, user=self.user, reason="Spam")
        self.client.login(username='testuser', password='testpass')
        url = reverse('review-report', args=[self.review.id])
        data = {"reason": "Spam again"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

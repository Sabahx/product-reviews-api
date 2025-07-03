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



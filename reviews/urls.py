
from rest_framework.routers import DefaultRouter
<<<<<<< HEAD
from .views import ReviewCommentViewSet, ReviewViewSet,RegisterView, ProductViewSet, ReviewVoteViewSet ,NotificationViewSet
=======
from .views import ReviewCommentViewSet, ReviewViewSet,RegisterView, ProductViewSet, ReviewVoteViewSet
>>>>>>> 0d4e224f4b88d804c64f252921113f09f81b3a50
from django.urls import path, include

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'review-comments', ReviewCommentViewSet, basename='review-comment')
router.register(r'review-votes', ReviewVoteViewSet, basename='review-vote') 
<<<<<<< HEAD
router.register(r'notifications', NotificationViewSet, basename='notification')
=======
>>>>>>> 0d4e224f4b88d804c64f252921113f09f81b3a50

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]


<<<<<<< HEAD

=======
>>>>>>> 0d4e224f4b88d804c64f252921113f09f81b3a50

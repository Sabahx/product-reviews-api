
from rest_framework.routers import DefaultRouter
from .views import ReviewCommentViewSet, ReviewViewSet,RegisterView, ProductViewSet, ReviewVoteViewSet ,NotificationViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'review-comments', ReviewCommentViewSet, basename='review-comment')
router.register(r'review-votes', ReviewVoteViewSet, basename='review-vote') 
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]




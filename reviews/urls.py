from rest_framework.routers import DefaultRouter
from .views import KeywordSearchReviewsView, ReviewCommentViewSet, ReviewViewSet,RegisterView, ProductViewSet, ReviewVoteViewSet ,ProductAnalyticsView, TopRatedProductsView, TopReviewersView , NotificationViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'review-comments', ReviewCommentViewSet, basename='review-comment')
router.register(r'review-votes', ReviewVoteViewSet, basename='review-vote')
router.register(r'notifications', NotificationViewSet, basename='notification')
urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('products/<int:pk>/analytics/', ProductAnalyticsView.as_view(), name='product-analytics'),
    path('analytics/top-reviewers/', TopReviewersView.as_view(), name='top-reviewers'),
    path('analytics/top-products/', TopRatedProductsView.as_view(), name='top-rated-products'),
    path('analytics/search-reviews/', KeywordSearchReviewsView.as_view(), name='search-reviews'),
]


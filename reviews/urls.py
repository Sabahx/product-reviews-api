
from rest_framework.routers import DefaultRouter
from .views import ReviewViewSet,RegisterView, ProductViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'products', ProductViewSet, basename='product') 

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]




from rest_framework.routers import DefaultRouter
from .views import ReviewViewSet,RegisterView
from django.urls import path, include

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]



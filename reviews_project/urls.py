from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',           include('accounts.urls')),
    path('api/',       include('reviews.urls')),
    path('reviews/', include('reviews.urls')),         # مسارات الـ API لديك
    path('accounts/', include('accounts.urls')),       # تسجيل / دخول / خروج
    path('admin-dashboard/', include('admin_dashboard.urls', namespace='admin_dashboard')),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('shop/', include(('user_dashboard.urls', 'user_dashboard'),namespace='user_dashboard')),
 ]

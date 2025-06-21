from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # تسجيل الدخول
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # تحديث التوكن
    path('api/', include('reviews.urls')),  # باقي الواجهات    
    path('admin/', admin.site.urls),
    path('dashboard/', include('admin_dashboard.urls', namespace='admin_dashboard')),
    path('accounts/', include('accounts.urls', namespace='accounts')),

]

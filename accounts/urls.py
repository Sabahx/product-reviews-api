from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import signup , custom_login,admin_login

app_name = 'accounts'

urlpatterns = [
    path('signup/', signup, name='signup'),
    # path('login/', custom_login, name='login'),
    path('login/admin',  admin_login, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

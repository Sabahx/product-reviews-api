from django.urls import path
from . import views

app_name = 'user_dashboard'

urlpatterns = [
path('', views.home, name='home'),
# path('products/', views.product_list, name='product_list'),
path('products/<int:pk>/', views.product_detail, name='product_detail'),
path('products/<int:pk>/review/', views.add_review, name='add_review'),
path('login/', views.login_user, name='login'),
]
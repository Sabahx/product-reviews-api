from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
path('', views.dashboard, name='dashboard'),
path('reviews/', views.review_list, name='review_list'),
path('reviews/int:pk/approve/', views.review_approve, name='review_approve'),
path('reviews/int:pk/reject/', views.review_reject, name='review_reject'),
]
# from django.urls import path
# from .views import home
# from . import views

# app_name = 'admin_dashboard'

# urlpatterns = [
#     path('', views.home, name='home'),
#     path('pending/', views.pending_reviews, name='pending_reviews'),
#     path('approve/<int:review_id>/', views.approve_review, name='approve_review'),
#     path('delete/<int:review_id>/', views.delete_review, name='delete_review'),
#     path('stats/', views.product_stats, name='product_stats'),
#     path('notifications/', views.notifications, name='notifications'),
#     path('notifications/read/<int:notif_id>/', views.mark_notification_read, name='mark_notification_read'),
#     path('all-reviews/', views.all_reviews, name='all_reviews'),

#     # CRUD للمنتجات
#     # path('products/', views.product_list,   name='product_list'),
#     path('products/add/', views.product_create, name='product_create'),
#     path('products/<int:pk>/edit/',   views.product_update, name='product_update'),
#     path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
#     path('products/', views.product_list_ajax, name='product_list'),

# ]
from django.urls import path
from . import views
from .views import home

app_name = 'admin_dashboard'

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('pending/', views.pending_reviews, name='pending_reviews'),
    path('approve/<int:review_id>/', views.approve_review, name='approve_review'),
    path('delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('stats/', views.product_stats, name='product_stats'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/<int:notif_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('all-reviews/', views.all_reviews, name='all_reviews'),

    # CRUD للمنتجات
    path('products/',             views.product_list,         name='product_list'),
    path('products/add/',         views.product_form,         name='product_create'),
    path('products/<int:pk>/edit/',   views.product_form,     name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete_confirm, name='product_delete'),
]


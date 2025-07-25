from rest_framework.routers import DefaultRouter
from .views import  add_comment, delete_review, edit_review_view ,login_view ,logout_view, KeywordSearchReviewsView,notifications_page,register_view, ReviewCommentViewSet, ReviewViewSet,RegisterView, ProductViewSet, ReviewVoteViewSet ,ProductAnalyticsView, TopRatedProductsView, TopReviewersView ,ReviewApproveView, BannedWordsReviewsView, BannedWordViewSet, NotificationViewSet, add_review, product_detail_view, product_list_view, report_review
from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'review-comments', ReviewCommentViewSet, basename='review-comment')
router.register(r'review-votes', ReviewVoteViewSet, basename='review-vote') 
router.register(r'admin/banned-words', BannedWordViewSet, basename='banned-word')
router.register(r'notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Authentication
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    
    # Main Pages
    path('', views.home, name='home'),
    path('profile/', views.user_profile, name='user_profile'),
    # Product Pages
    path('product/<int:pk>/', product_detail_view, name='product-detail'),
    path('product/<int:product_id>/', product_detail_view, name='product_detail'),  # Alternative name
    
    # Review Actions
    path('product/<int:product_id>/favorite/', views.toggle_favorite, name='toggle-favorite'),
    path('product/<int:pk>/review/', add_review, name='add-review'),
    path('reviews/<int:review_id>/comment/', add_comment, name='add-comment'),
    path('reviews/<int:review_id>/edit/', edit_review_view, name='edit_review'),
    path('reviews/<int:review_id>/delete/', delete_review, name='delete_review'),
    path('reviews/<int:pk>/report/', report_review, name='report-review'),
    
    # Missing URLs that the template needs
    path('reviews/<int:review_id>/helpful/', views.review_helpful, name='review-helpful'),
    
    # Optional: Favorites feature (commented out until implemented)
    # path('product/<int:product_id>/favorite/', views.toggle_favorite, name='toggle-favorite'),
    
    # Analytics
    path('products/<int:pk>/analytics/', ProductAnalyticsView.as_view(), name='product-analytics'),
    path('analytics/top-reviewers/', TopReviewersView.as_view(), name='top-reviewers'),
    path('analytics/top-products/', TopRatedProductsView.as_view(), name='top-rated-products'),
    path('analytics/search-reviews/', KeywordSearchReviewsView.as_view(), name='search-reviews'),
    
    # Admin Tools
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('reviews/<int:pk>/approve_review/', ReviewApproveView.as_view(), name='approve-review'),
    path('admin/banned-word-reviews/', BannedWordsReviewsView.as_view(), name='banned-word-reviews'),

    #notifications
    path('notifications/', views.notifications_page, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('notifications/clear-old/', views.clear_old_notifications, name='clear_old_notifications'),
    path('notifications/clear-all/', views.clear_all_notifications, name='clear_all_notifications'),
    path('api/notifications/unread-count/', views.get_unread_count, name='unread_count'),
   
]


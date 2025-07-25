from rest_framework.routers import DefaultRouter
from .views import  AddCommentAPIView, UserProfileAPIView, delete_review, edit_review_view ,login_view ,logout_view, KeywordSearchReviewsView,notifications_page,register_view, ReviewCommentViewSet, ReviewViewSet,RegisterView, ProductViewSet, ReviewVoteViewSet ,ProductAnalyticsView, TopRatedProductsView, TopReviewersView ,ReviewApproveView, BannedWordsReviewsView, BannedWordViewSet, NotificationViewSet, add_review, product_detail_view, product_list_view, report_review, user_me_view
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
    path('api/', include(router.urls)),  # ← API URLs فقط
    
    # Auth/Register
    # path('api/register/', RegisterView.as_view(), name='register'),

    # Frontend views
    path('',views.home ,name="home"),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('product/<int:pk>/', product_detail_view, name='product-detail'),
    path('product/<int:pk>/review/', add_review, name='add-review'),
    path('report/<int:pk>/', report_review, name='report-review'),

    # Analytics
    path('products/<int:pk>/analytics/', ProductAnalyticsView.as_view(), name='product-analytics'),
    path('analytics/top-reviewers/', TopReviewersView.as_view(), name='top-reviewers'),
    path('analytics/top-products/', TopRatedProductsView.as_view(), name='top-rated-products'),
    path('analytics/search-reviews/', KeywordSearchReviewsView.as_view(), name='search-reviews'),

    # Admin tools
    path('reviews/<int:pk>/approve_review/', ReviewApproveView.as_view(), name='approve-review'),
    path('admin/banned-word-reviews/', BannedWordsReviewsView.as_view(), name='banned-word-reviews'),
    #####
    path('register/', register_view, name='register'),
    path('api/register/',  RegisterView.as_view(), name='api-register'),
    
    path('profile/', views.user_profile_page, name='user_profile'),
    path('api/user/profile/', UserProfileAPIView.as_view(), name='user-profile-api'),
    path('api/me/', user_me_view, name='user-me'),
    
    #path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('login/', login_view, name='login'),
    #path('login/', auth_views.LoginView.as_view(template_name='login.html',next_page='home'), name='login'),
    path('notifications/', views.notifications_page, name='notifications'),
    path('logout/', logout_view, name='logout'),
    path('notifications/mark_all_read/', views.mark_all_read, name='mark_all_read'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    path('', views.home, name='home'),  # الصفحة الرئيسية تعرض index.html
    path('reviews/<int:review_id>/comment/', AddCommentAPIView.as_view(), name='add-comment'),
    path('product/<int:product_id>/', product_detail_view, name='product_detail'),
    path('reviews/<int:review_id>/edit/', edit_review_view, name='edit_review'),
    path('reviews/<int:review_id>/delete/', delete_review, name='delete_review'),
]


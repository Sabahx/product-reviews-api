from datetime import timedelta
import csv
import json
import openpyxl
from io import BytesIO
from django.shortcuts import redirect, render , get_object_or_404
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count, Avg, Subquery, OuterRef
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser
)
from django.contrib import messages
from django.contrib.auth import login
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Product,
    Review,
    ReviewComment,
    ReviewView,
    ReviewVote,
    ReviewInteraction,
    BannedWord,
    Notification,
    ReviewReport,
    
)
from .serializers import (
    RegisterSerializer,
    ReviewSerializer,
    ProductSerializer,
    ReviewCommentSerializer,
    ReviewVoteSerializer,
    BannedWordSerializer,
    NotificationSerializer,
    User
)
from .permissions import IsOwnerOrReadOnly

from rest_framework_simplejwt.authentication import JWTAuthentication

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = 'pk'
    
    # ✅ Explicitly override create method to ensure authentication
    def create(self, request, *args, **kwargs):
        """Override create to ensure authentication is properly applied"""
        print(f"🔍 CREATE method called")
        print(f"🔍 User: {request.user}")
        print(f"🔍 Is authenticated: {request.user.is_authenticated}")
        print(f"🔍 Auth header: {request.META.get('HTTP_AUTHORIZATION', 'No auth header')}")
        
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, 
                          status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        
        if self.action in ['update', 'partial_update', 'destroy', 'retrieve']:
           return Review.objects.all()  # ← هذا السطر هو المحتوى المتوقع داخل if
    
        queryset = Review.objects.filter(visible=True)
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product__id=product_id)
        
        # Laith: Added support for filtering by rating (e.g. ?rating=5)
        rating = self.request.query_params.get('rating')
        if rating:
            try:
                rating = int(rating)
                if 1 <= rating <= 5:  # Validate rating is between 1-5
                    queryset = queryset.filter(rating=rating)
            except ValueError:
                # If rating is not a valid integer, ignore the filter
                pass
                
        # Laith: Added support for sorting reviews
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        
        if sort_by == 'newest':
            # Sort by creation date (newest first)
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'highest_rating':
            # Sort by rating (highest first)
            queryset = queryset.order_by('-rating')
        elif sort_by == 'most_interactive':
            # Sort by number of interactions (most interactions first)
            queryset = queryset.annotate(
                interaction_count=Count('interactions')
            ).order_by('-interaction_count')
        else:
            # Default sorting by created_at (newest first)
            queryset = queryset.order_by('-created_at')
            
        return queryset
    #task9 section 5 (sabah)
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views = models.F('views') + 1
        instance.save(update_fields=["views"])
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'],permission_classes=[IsAuthenticated],authentication_classes = [JWTAuthentication])
    def interact(self, request, pk=None):
        """المستخدم يقيّم المراجعة بأنها مفيدة أو غير مفيدة"""
        review = self.get_object()
        helpful = request.data.get('helpful')

        if helpful is None:
            return Response({"error": "يجب إرسال قيمة الحقل 'helpful'"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            interaction = ReviewInteraction.objects.get(review=review, user=request.user)
            if interaction.helpful == helpful:
                # Same vote - remove it
                interaction.delete()
                user_vote = None
            else:
                # Different vote - update it
                interaction.helpful = helpful
                interaction.save()
                user_vote = helpful
        except ReviewInteraction.DoesNotExist:
            # No previous vote - create new one
            ReviewInteraction.objects.create(review=review, user=request.user, helpful=helpful)
            user_vote = helpful
        
        return Response({
            "message": "تم حفظ التفاعل",
            "likes": review.likes,  # Make sure you have this method
            "dislikes": review.dislikes,
            "user_vote": user_vote
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='top-review')
    def top_review(self, request):
        """عرض المراجعة التي حصلت على أكبر عدد من الإعجابات"""
        
        top = Review.objects.annotate(
            likes=Count('interactions', filter=models.Q(interactions__helpful=True))
        ).order_by('-likes').first()

        if top:
            return Response(self.get_serializer(top).data)
        return Response({"message": "لا توجد مراجعات بعد"}, status=status.HTTP_404_NOT_FOUND)
    
    #لارسال ابلاغ
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def report(self, request, pk=None):
        review = self.get_object()
        reason = request.data.get('reason')
        if not reason:
            return Response({"error": "يجب تحديد سبب البلاغ"}, status=400)

        report, created = ReviewReport.objects.get_or_create(review=review, user=request.user, defaults={'reason': reason})
        if not created:
            return Response({"error": "تم الإبلاغ مسبقًا"}, status=400)
    
        return Response({"message": "تم الإبلاغ عن المراجعة بنجاح"})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        review = self.get_object()
        review.visible = True
        review.save()
        return Response({'status': 'Review Approved'})
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        review = self.get_object()
        if request.method == 'GET':
            comments = review.comments.all()
            serializer = ReviewCommentSerializer(comments, many=True)
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = ReviewCommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(review=review, user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Laith: Added action to filter reviews with banned words (admin only)
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def with_banned_words(self, request):
        """
        Returns reviews containing banned words.
        Can filter by severity level using the 'severity' query parameter.
        """
        severity = request.query_params.get('severity')
        
        reviews = self.get_queryset().filter(contains_banned_words=True)
        
        if severity:
            try:
                severity = int(severity)
                # Get banned words with the specified severity
                banned_words = BannedWord.objects.filter(severity=severity).values_list('word', flat=True)
                
                # Filter reviews containing these words
                filtered_reviews = []
                for review in reviews:
                    if review.banned_words_found:
                        found_words = review.banned_words_found.split(', ')
                        for word in banned_words:
                            if word in found_words:
                                filtered_reviews.append(review)
                                break
                
                reviews = Review.objects.filter(id__in=[r.id for r in filtered_reviews])
            except ValueError:
                return Response({"detail": "Invalid severity parameter"}, status=400)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # queryset ليحسب average_rating و reviews_count باستخدام annotate.

    def get_queryset(self):
        return Product.objects.annotate(
            average_rating=Avg('reviews__rating'),
            reviews_count=Count('reviews')
        )

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['get'])
    def export_reviews(self, request, pk=None):
        product = self.get_object()
        reviews = product.reviews.filter(approved=True)
        
        format = request.query_params.get('format', 'csv')
        
        if format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{product.name}_reviews.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['User', 'Rating', 'Title', 'Content', 'Date', 'Helpful', 'Not Helpful'])
            
            for review in reviews:
                writer.writerow([
                    review.user.username,
                    review.rating,
                    review.title,
                    review.content,
                    review.created_at.strftime('%Y-%m-%d'),
                    review.helpful_count,
                    review.not_helpful_count
                ])
            
            return response
        
        elif format == 'excel':
            output = BytesIO()
            workbook = openpyxl.Workbook()
            worksheet = workbook.active
            worksheet.title = "Reviews"
            
            # كتابة العناوين
            worksheet.append(['User', 'Rating', 'Title', 'Content', 'Date', 'Helpful', 'Not Helpful'])
            
            # كتابة البيانات
            for review in reviews:
                worksheet.append([
                    review.user.username,
                    review.rating,
                    review.title,
                    review.content,
                    review.created_at.strftime('%Y-%m-%d'),
                    review.helpful_count,
                    review.not_helpful_count
                ])
            
            workbook.save(output)
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{product.name}_reviews.xlsx"'
            return response
        
        return Response({'error': 'Invalid format'}, status=400)

    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        product = self.get_object()
        reviews = product.reviews.filter(visible=True)
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)

class ReviewCommentViewSet(viewsets.ModelViewSet):
    queryset = ReviewComment.objects.all()
    serializer_class = ReviewCommentSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ReviewVoteViewSet(viewsets.ModelViewSet):
    queryset = ReviewVote.objects.all()
    serializer_class = ReviewVoteSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

#task8 analytics section (sabah aljajeh)
#معدل التقييم خلال فترة	
class ProductAnalyticsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found'}, status=404)

        days = int(request.query_params.get('days', 30))
        since_date = timezone.now() - timedelta(days=days)

        reviews = Review.objects.filter(product=product, created_at__gte=since_date, visible=True)
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        total_reviews = reviews.count()

        return Response({
            'product': product.name,
            'average_rating_last_days': round(avg_rating, 2),
            'review_count_last_days': total_reviews,
            'period_days': days
        })
    
#عرض قائمة بأكثر المستخدمين نشاطًا (مرتّبين حسب عدد المراجعات المكتوبة).

class TopReviewersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        top_users = User.objects.annotate(review_count=Count('review')) \
                                .filter(review__visible=True) \
                                .order_by('-review_count')[:10]

        result = [
            {"username": user.username, "review_count": user.review_count}
            for user in top_users
        ]
        return Response(result)

#عرض قائمة المنتجات اللي حصلت على أعلى معدل تقييم خلال فترة زمنية (مثلاً آخر 30 يوم).

class TopRatedProductsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=int(days))

        top_products = Product.objects.annotate(
         avg_rating=Avg('reviews__rating', filter=Q(reviews__created_at__gte=since, reviews__visible=True)),
         review_count=Count('reviews', filter=Q(reviews__created_at__gte=since, reviews__visible=True))
         ).filter(review_count__gte=1).order_by('-avg_rating')[:10]


        result = [
            {
                "product_id": product.id,
                "product_name": product.name,
                "average_rating": round(product.avg_rating, 2),
                "review_count": product.review_count
            }
            for product in top_products
        ]
        return Response(result)

#يرجع مراجعات تحتوي كلمات أو جمل معيّنة (مثل "سيء", "ممتاز", "سعر").
#mjd⬇
"""# عرض أعلى مراجعة تفاعلاً (Top Review)
class TopReviewView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        top_review = (
            Review.objects.filter(product_id=product_id, visible=True)
            .annotate(likes=Count('interactions', filter=Q(interactions__helpful=True)))
            .order_by('-likes', '-created_at')  # الأفضلية للأكثر إعجابًا ثم الأحدث
            .first()
        )
        if top_review:
            return Response(ReviewSerializer(top_review, context={'request': request}).data)
        else:
            return Response({'detail': 'لا توجد مراجعات متاحة'}, status=404)
"""
class KeywordSearchReviewsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        keyword = request.query_params.get('q', '')
        if not keyword:
            return Response({"detail": "Keyword is required (use ?q=...)"}, status=400)

        matching_reviews = Review.objects.filter(
            review_text__icontains=keyword,
            visible=True
        ).select_related('product', 'user')

        result = [
            {
                "review_id": r.id,
                "product": r.product.name,
                "user": r.user.username,
                "rating": r.rating,
                "text": r.review_text,
                "created_at": r.created_at
            }
            for r in matching_reviews
        ]
        return Response(result)

class ReviewApproveView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return Response(status=404)
        
        review.visible = request.data.get("visible", True)
        review.save()
        return Response({"detail": "Review approved"}, status=200)

# Laith: Added view for filtering reviews with banned words for admin use
class BannedWordsReviewsView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """
        Returns reviews that contain banned words.
        Optional query parameters:
        - severity: Filter by banned word severity (1, 2, or 3)
        - days: Filter reviews from the last X days
        """
        days = request.query_params.get('days')
        severity = request.query_params.get('severity')
        
        reviews = Review.objects.filter(contains_banned_words=True)
        
        if days:
            try:
                days = int(days)
                start_date = timezone.now() - timedelta(days=days)
                reviews = reviews.filter(created_at__gte=start_date)
            except ValueError:
                return Response({"detail": "Invalid days parameter"}, status=400)
        
        if severity:
            try:
                severity = int(severity)
                # Get all banned words with the specified severity
                banned_words = BannedWord.objects.filter(severity=severity).values_list('word', flat=True)
                
                # Filter reviews that contain any of these words
                # This is a more complex query that checks each banned word
                q_objects = Q()
                for word in banned_words:
                    q_objects |= Q(review_text__icontains=word)
                
                reviews = reviews.filter(q_objects)
            except ValueError:
                return Response({"detail": "Invalid severity parameter"}, status=400)
        
        result = []
        for review in reviews:
            result.append({
                "id": review.id,
                "product": review.product.name,
                "user": review.user.username,
                "rating": review.rating,
                "review_text": review.review_text,
                "banned_words_found": review.banned_words_found,
                "created_at": review.created_at,
                "visible": review.visible
            })
        
        return Response(result)

# Laith: Added viewset for managing banned words
class BannedWordViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing banned words.
    Only accessible by admin users.
    """
    queryset = BannedWord.objects.all().order_by('-created_at')
    serializer_class = BannedWordSerializer
    permission_classes = [IsAdminUser]  # Only admin users can access this endpoint

    def get_queryset(self):
        queryset = BannedWord.objects.all().order_by('-created_at')
        # Support filtering by severity
        severity = self.request.query_params.get('severity', None)
        if severity is not None:
            try:
                severity = int(severity)
                queryset = queryset.filter(severity=severity)
            except ValueError:
                pass
        return queryset

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def notifications_page(request):
    # استدعاء الإشعارات الخاصة بالمستخدم لتمريرها للقالب
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'notifications': notifications
    }
    return render(request, 'notifications.html', context)



class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({'status': 'marked as read'})

def home(request):
    
    return render(request, 'home.html')
   
# task 10 sabah ( index,html)
def product_list_view(request):
    products = Product.objects.annotate(
        average_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    )

    # 🔍 فلترة حسب الاسم
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(name__icontains=search_query)

    # ⬇️ الترتيب حسب طلب المستخدم
    sort_by = request.GET.get('sort')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        products = products.order_by('-average_rating')
    elif sort_by == 'reviews':
        products = products.order_by('-reviews_count')

    return render(request, 'index.html', {'products': products})


def product_detail_view(request, pk):
    product = get_object_or_404(Product.objects.annotate(
        average_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    ), pk=pk)

    # تحميل المراجعات مع تعليقاتها المرتبطة
    reviews = Review.objects.filter(product=product, visible=True)\
        .select_related('user')\
        .prefetch_related('comments')
        
    # Log a view for each review when accessed
    for review in reviews:
        ReviewView.objects.get_or_create(
            review=review,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR', '') if not request.user.is_authenticated else ''
        )

    return render(request, 'product_detail.html', {
        'product': product,
        'reviews': reviews,
    })



@login_required
def add_review(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        text = request.POST.get('review_text', '')

        Review.objects.create(
            product=product,
            user=request.user,
            rating=rating,
            review_text=text,
            visible=True  # تحتاج موافقة
        )

    return redirect('product-detail', pk=product.id)

class AddCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, review_id):
        text = request.data.get('text')
        if not text:
            return Response({'error': 'Text is required'}, status=status.HTTP_400_BAD_REQUEST)
        review = get_object_or_404(Review, id=review_id)
        comment = ReviewComment.objects.create(
            review=review,
            user=request.user,
            text=text
        )
        return Response({
            'id': comment.id,
            'text': comment.text,
            'user': {'username': request.user.username}
        }, status=status.HTTP_201_CREATED)

@login_required
def report_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    reason = request.POST.get('reason', 'غير محدد')

    report, created = ReviewReport.objects.get_or_create(
        review=review,
        user=request.user,
        defaults={'reason': reason}
    )
    if not created:
        # تم الإبلاغ سابقًا
        pass

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def register_view(request):
    return render(request, 'register.html')

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens for the new user
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "user": serializer.data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

def login_view(request):
    return render(request, 'login.html')

def user_profile_page(request):
    return render(request, 'user_profile.html')

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # User's reviews
        user_reviews = Review.objects.filter(user=user)
        user_reviews_count = user_reviews.count()

        # Likes received on user's reviews
        user_likes_received = ReviewInteraction.objects.filter(
            review__user=user, helpful=True
        ).count()

        # Comments written by user
        user_comments_count = ReviewComment.objects.filter(user=user).count()

        # Reviews liked by user
        liked_reviews = ReviewInteraction.objects.filter(
            user=user, helpful=True
        ).select_related('review', 'review__product', 'review__user')

        # Prepare reviews data
        reviews_data = [
            {
                "id": review.id,
                "product_id": review.product.id,
                "product_name": review.product.name,
                "rating": review.rating,
                "created_at": review.created_at.strftime("%Y-%m-%d"),
                "visible": review.visible,
                "review_text": review.review_text,
                "likes_count": review.likes,
                "comments_count": review.comments.count(),
            }
            for review in user_reviews
        ]

        # Prepare liked reviews data
        liked_reviews_data = [
            {
                "id": interaction.review.id,
                "product_id": interaction.review.product.id,
                "product_name": interaction.review.product.name,
                "user": interaction.review.user.username,
                "rating": interaction.review.rating,
                "created_at": interaction.review.created_at.strftime("%Y-%m-%d"),
                "review_text": interaction.review.review_text,
                "likes_count": interaction.review.likes,
                "comments_count": interaction.review.comments.count(),
            }
            for interaction in liked_reviews
        ]

        data = {
            "username": user.username,
            "email": user.email,
            "date_joined": user.date_joined.strftime("%Y-%m-%d"),
            "reviews_count": user_reviews_count,
            "likes_received": user_likes_received,
            "comments_count": user_comments_count,
            "reviews": reviews_data,
            "liked_reviews": liked_reviews_data,
        }
        return Response(data)

    def put(self, request):
        user = request.user
        email = request.data.get("email")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")
        current_password = request.data.get("current_password")

        # Validate current password
        if not user.check_password(current_password):
            return Response({"error": "كلمة المرور الحالية غير صحيحة"}, status=status.HTTP_400_BAD_REQUEST)

        # Update email
        if email:
            user.email = email

        # Update password
        if new_password:
            if new_password != confirm_password:
                return Response({"error": "كلمتا المرور غير متطابقتين"}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)

        user.save()
        return Response({"success": "تم تحديث البيانات بنجاح"})


from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def mark_all_read(request):
    notifications = Notification.objects.filter(user=request.user, read=False)
    notifications.update(read=True)
    return redirect('notifications')  # أو إلى أي صفحة تريد


@login_required
def clear_notifications(request):
    Notification.objects.filter(user=request.user).delete()
    return redirect('notifications')  # توجه إلى صفحة الإشعارات بعد الحذف

from django.db.models import Avg, Count

def home(request):
    # Get all products with annotations (average_rating and reviews_count)
    products = Product.objects.annotate(
        average_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    )

    # Search filtering
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(name__icontains=search_query)
        
    # Star rating filter (e.g., ?rating=4)
    rating_filter = request.GET.get('rating')
    if rating_filter and rating_filter.isdigit():
        rating_filter = int(rating_filter)
        products = products.filter(average_rating__gte=rating_filter,average_rating__lt=rating_filter+1)

    # Sorting
    sort_option = request.GET.get('sort', '')
    if sort_option == 'price_asc':
        products = products.order_by('price')
    elif sort_option == 'price_desc':
        products = products.order_by('-price')
    elif sort_option == 'rating':
        products = products.order_by('-average_rating')  # Now works because of annotation
    elif sort_option == 'reviews':
        products = products.order_by('-reviews_count')  # Fixed typo (was 'review_count')

    context = {
        'products': products,
        'unread_notifications_count': 0,  # Or fetch real unread notifications
    }
    return render(request, 'index.html', context)

@login_required
def edit_review_view(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')

        review.rating = rating
        review.review_text = review_text
        review.save()

        messages.success(request, 'تم تحديث المراجعة بنجاح.')
        return redirect('user_profile')

    return render(request, 'edit_review.html', {'review': review})




@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'تم حذف المراجعة بنجاح.')
        return redirect('user_profile')
    return redirect('user_profile')

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_me_view(request):
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        'is_staff': user.is_staff,  # Make sure this is included
        'is_superuser': user.is_superuser
    })

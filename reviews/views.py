from datetime import timedelta
import csv
import openpyxl
from io import BytesIO
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count, Avg, Subquery, OuterRef
from django.http import HttpResponse, HttpResponseRedirect ,JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib import messages
from django.core.paginator import Paginator
from rest_framework import viewsets, permissions, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser
)

from .models import (
    Product,
    Review,
    ReviewComment,
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
)
from .permissions import IsOwnerOrReadOnly

User = get_user_model()



# =============================================================================
# DRF API VIEWSETS
# =============================================================================

class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product reviews with full CRUD operations.
    Includes features like voting, commenting, reporting, and analytics.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = 'pk'

    def get_queryset(self):
        """
        Optimize queryset with proper joins and filtering based on action.
        """
        if self.action in ['update', 'partial_update', 'destroy', 'retrieve']:
            # For modification actions, return all reviews with optimized queries
            return Review.objects.select_related('user', 'product')\
                .prefetch_related('interactions', 'votes', 'reports', 'comments')
    
        # For list actions, only show visible reviews with filters
        queryset = Review.objects.filter(visible=True)\
            .select_related('user', 'product')\
            .prefetch_related('interactions', 'votes', 'reports', 'comments')
        
        # Filter by product if specified
        product_id = self.request.query_params.get('product')
        if product_id:
            try:
                product_id = int(product_id)
                queryset = queryset.filter(product__id=product_id)
            except ValueError:
                pass  # Invalid product_id, ignore filter
        
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

    def perform_create(self, serializer):
        """Set the user when creating a review."""
        serializer.save(user=self.request.user)

    # task9 section 5 (sabah)
    def get_serializer_context(self):
        """Add request context for serializer computed fields."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single review and increment view count.
        Fixed: Removed duplicate method and optimized view counting.
        """
        instance = self.get_object()
        # Increment views atomically to avoid race conditions
        instance.views = models.F('views') + 1
        instance.save(update_fields=["views"])
        instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
        
    # mjd⬇
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def interact(self, request, pk=None):
        """المستخدم يقيّم المراجعة بأنها مفيدة أو غير مفيدة"""
        review = self.get_object()
        helpful = request.data.get('helpful')

        # Validate input
        if helpful is None:
            return Response(
                {"error": "يجب إرسال قيمة الحقل 'helpful'"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure helpful is boolean
        if not isinstance(helpful, bool):
            return Response(
                {"error": "helpful must be a boolean value"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # تقييد كل مستخدم بتفاعل واحد لكل مراجعة
        interaction, created = ReviewInteraction.objects.update_or_create(
            review=review,
            user=request.user,
            defaults={'helpful': helpful}
        )
        
        action_text = "تم إنشاء" if created else "تم تحديث"
        return Response(
            {"message": f"{action_text} التفاعل بنجاح"}, 
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='top-review')
    def top_review(self, request):
        """عرض المراجعة التي حصلت على أكبر عدد من الإعجابات"""
        
        top = Review.objects.filter(visible=True).annotate(
            likes=Count('interactions', filter=models.Q(interactions__helpful=True))
        ).order_by('-likes', '-created_at').first()  # الأفضلية للأكثر إعجابًا ثم الأحدث

        if top:
            serializer = self.get_serializer(top)
            return Response(serializer.data)
        return Response(
            {"message": "لا توجد مراجعات بعد"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    # ⬆

    # mjd task9⬇
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def report(self, request, pk=None):
        """لارسال ابلاغ عن المراجعة"""
        review = self.get_object()
        reason = request.data.get('reason', '').strip()
        
        if not reason:
            return Response(
                {"error": "يجب تحديد سبب البلاغ"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        report, created = ReviewReport.objects.get_or_create(
            review=review, 
            user=request.user, 
            defaults={'reason': reason}
        )
        
        if not created:
            return Response(
                {"error": "تم الإبلاغ مسبقًا عن هذه المراجعة"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
        return Response({"message": "تم الإبلاغ عن المراجعة بنجاح"})
    # ⬆

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """Approve a review (admin only)."""
        review = self.get_object()
        review.visible = True
        review.save()
        return Response({'status': 'Review Approved'})
    
    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def comments(self, request, pk=None):
        """Get or create comments for a review."""
        review = self.get_object()
        
        if request.method == 'GET':
            comments = review.comments.select_related('user').order_by('created_at')
            serializer = ReviewCommentSerializer(comments, many=True)
            return Response(serializer.data)
            
        elif request.method == 'POST':
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Authentication required"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
            serializer = ReviewCommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(review=review, user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def vote(self, request, pk=None):
        """Vote on a review (helpful/not helpful)."""
        review = self.get_object()
        user = request.user
        helpful = request.data.get('helpful', None)
        
        if helpful is None:
            return Response(
                {'error': 'Helpful field is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure helpful is boolean
        if not isinstance(helpful, bool):
            return Response(
                {'error': 'Helpful must be a boolean value'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vote, created = ReviewVote.objects.get_or_create(
            review=review,
            user=user,
            defaults={'helpful': helpful}
        )
        
        if not created:
            vote.helpful = helpful
            vote.save()
        
        serializer = ReviewVoteSerializer(vote)
        return Response(serializer.data)

    # Laith: Added action to filter reviews with banned words (admin only)
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def with_banned_words(self, request):
        """
        Returns reviews containing banned words.
        Can filter by severity level using the 'severity' query parameter.
        """
        severity = request.query_params.get('severity')
        
        queryset = Review.objects.filter(contains_banned_words=True)\
            .select_related('user', 'product')
        
        if severity:
            try:
                severity = int(severity)
                if severity in [1, 2, 3]:  # Validate severity
                    banned_words = BannedWord.objects.filter(severity=severity)\
                        .values_list('word', flat=True)
                    
                    # Use database filtering instead of Python loops for better performance
                    q_objects = Q()
                    for word in banned_words:
                        q_objects |= Q(banned_words_found__icontains=word)
                    
                    queryset = queryset.filter(q_objects)
                else:
                    return Response(
                        {"detail": "Severity must be 1, 2, or 3"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {"detail": "Invalid severity parameter"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products with computed fields for ratings and review counts.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        """Add computed fields for average rating and review count."""
        return Product.objects.annotate(
            average_rating=Avg('reviews__rating', filter=Q(reviews__visible=True)),
            reviews_count=Count('reviews', filter=Q(reviews__visible=True))
        ).select_related().prefetch_related('reviews')

    def get_permissions(self):
        """Admin only for CUD operations, read for everyone else."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]

    @action(detail=True, methods=['get'])
    def export_reviews(self, request, pk=None):
        """
        Export product reviews to CSV or Excel format.
        Fixed: Corrected field names and added proper error handling.
        """
        product = self.get_object()
        reviews = product.reviews.filter(visible=True)\
            .select_related('user')\
            .prefetch_related('interactions')
        
        format_type = request.query_params.get('format', 'csv').lower()
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{product.name}_reviews.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'User', 'Rating', 'Review Text', 'Date', 
                'Helpful', 'Not Helpful', 'Views', 'Sentiment'
            ])
            
            for review in reviews:
                helpful_count = review.interactions.filter(helpful=True).count()
                not_helpful_count = review.interactions.filter(helpful=False).count()
                
                writer.writerow([
                    review.user.username,
                    review.rating,
                    review.review_text,
                    review.created_at.strftime('%Y-%m-%d'),
                    helpful_count,
                    not_helpful_count,
                    review.views,
                    review.sentiment
                ])
            
            return response
        
        elif format_type == 'excel':
            output = BytesIO()
            workbook = openpyxl.Workbook()
            worksheet = workbook.active
            worksheet.title = "Reviews"
            
            # كتابة العناوين
            headers = [
                'User', 'Rating', 'Review Text', 'Date', 
                'Helpful', 'Not Helpful', 'Views', 'Sentiment'
            ]
            worksheet.append(headers)
            
            # كتابة البيانات
            for review in reviews:
                helpful_count = review.interactions.filter(helpful=True).count()
                not_helpful_count = review.interactions.filter(helpful=False).count()
                
                worksheet.append([
                    review.user.username,
                    review.rating,
                    review.review_text,
                    review.created_at.strftime('%Y-%m-%d'),
                    helpful_count,
                    not_helpful_count,
                    review.views,
                    review.sentiment
                ])
            
            workbook.save(output)
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{product.name}_reviews.xlsx"'
            return response
        
        return Response(
            {'error': 'Invalid format. Use "csv" or "excel"'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get all visible reviews for a product."""
        product = self.get_object()
        reviews = product.reviews.filter(visible=True)\
            .select_related('user')\
            .prefetch_related('interactions', 'votes', 'comments')\
            .order_by('-created_at')
        
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)


class ReviewCommentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing review comments."""
    queryset = ReviewComment.objects.select_related('user', 'review').order_by('-created_at')
    serializer_class = ReviewCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        """Set the user when creating a comment."""
        serializer.save(user=self.request.user)


class ReviewVoteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing review votes."""
    queryset = ReviewVote.objects.select_related('user', 'review').order_by('-created_at')
    serializer_class = ReviewVoteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        """Set the user when creating a vote."""
        serializer.save(user=self.request.user)


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
        """Support filtering by severity."""
        queryset = BannedWord.objects.all().order_by('-created_at')
        severity = self.request.query_params.get('severity', None)
        
        if severity is not None:
            try:
                severity = int(severity)
                if severity in [1, 2, 3]:
                    queryset = queryset.filter(severity=severity)
            except ValueError:
                pass  # Invalid severity, ignore filter
                
        return queryset


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user notifications (read-only)."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only show notifications for the current user."""
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all user notifications as read."""
        count = self.get_queryset().filter(read=False).update(read=True)
        return Response({'status': f'{count} notifications marked as read'})


# =============================================================================
# ANALYTICS API VIEWS
# =============================================================================

# task8 analytics section (sabah aljajeh)
class ProductAnalyticsView(APIView):
    """معدل التقييم خلال فترة"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found'}, status=404)

        days = int(request.query_params.get('days', 30))
        since_date = timezone.now() - timedelta(days=days)

        reviews = Review.objects.filter(
            product=product, 
            created_at__gte=since_date, 
            visible=True
        )
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        total_reviews = reviews.count()

        return Response({
            'product': product.name,
            'average_rating_last_days': round(avg_rating, 2),
            'review_count_last_days': total_reviews,
            'period_days': days
        })


class TopReviewersView(APIView):
    """عرض قائمة بأكثر المستخدمين نشاطًا (مرتّبين حسب عدد المراجعات المكتوبة)."""
    permission_classes = [AllowAny]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        
        top_users = User.objects.annotate(
            review_count=Count('review', filter=Q(review__visible=True))
        ).filter(review_count__gt=0).order_by('-review_count')[:limit]

        result = [
            {"username": user.username, "review_count": user.review_count}
            for user in top_users
        ]
        return Response(result)


class TopRatedProductsView(APIView):
    """عرض قائمة المنتجات اللي حصلت على أعلى معدل تقييم خلال فترة زمنية (مثلاً آخر 30 يوم)."""
    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        since = timezone.now() - timedelta(days=days)

        top_products = Product.objects.annotate(
            avg_rating=Avg(
                'reviews__rating', 
                filter=Q(reviews__created_at__gte=since, reviews__visible=True)
            ),
            review_count=Count(
                'reviews', 
                filter=Q(reviews__created_at__gte=since, reviews__visible=True)
            )
        ).filter(review_count__gte=1).order_by('-avg_rating')[:limit]

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


class KeywordSearchReviewsView(APIView):
    """يرجع مراجعات تحتوي كلمات أو جمل معيّنة (مثل "سيء", "ممتاز", "سعر")."""
    permission_classes = [AllowAny]

    def get(self, request):
        keyword = request.query_params.get('q', '').strip()
        if not keyword:
            return Response(
                {"detail": "Keyword is required (use ?q=...)"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        matching_reviews = Review.objects.filter(
            review_text__icontains=keyword,
            visible=True
        ).select_related('product', 'user').order_by('-created_at')

        # Add pagination support
        limit = int(request.query_params.get('limit', 50))
        matching_reviews = matching_reviews[:limit]

        result = [
            {
                "review_id": r.id,
                "product": r.product.name,
                "user": r.user.username,
                "rating": r.rating,
                "text": r.review_text,
                "created_at": r.created_at,
                "sentiment": r.sentiment
            }
            for r in matching_reviews
        ]
        return Response(result)


# Laith: Added view for filtering reviews with banned words for admin use
class BannedWordsReviewsView(APIView):
    """Admin view for reviews containing banned words."""
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
        
        reviews = Review.objects.filter(contains_banned_words=True)\
            .select_related('user', 'product')
        
        if days:
            try:
                days = int(days)
                start_date = timezone.now() - timedelta(days=days)
                reviews = reviews.filter(created_at__gte=start_date)
            except ValueError:
                return Response(
                    {"detail": "Invalid days parameter"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if severity:
            try:
                severity = int(severity)
                if severity in [1, 2, 3]:
                    # Get all banned words with the specified severity
                    banned_words = BannedWord.objects.filter(severity=severity)\
                        .values_list('word', flat=True)
                    
                    # Filter reviews that contain any of these words
                    q_objects = Q()
                    for word in banned_words:
                        q_objects |= Q(review_text__icontains=word)
                    
                    reviews = reviews.filter(q_objects)
                else:
                    return Response(
                        {"detail": "Severity must be 1, 2, or 3"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {"detail": "Invalid severity parameter"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
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


class ReviewApproveView(APIView):
    """Admin view to approve/disapprove reviews."""
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return Response(
                {"detail": "Review not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        visible = request.data.get("visible")
        if visible is None:
            return Response(
                {"detail": "visible field is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        review.visible = bool(visible)
        review.save()
        
        action = "approved" if review.visible else "disapproved"
        return Response({"detail": f"Review {action}"}, status=200)


class RegisterView(generics.CreateAPIView):
    """API endpoint for user registration."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


# =============================================================================
# TRADITIONAL DJANGO VIEWS (For Web Interface)
# =============================================================================

def home(request):
    """
    Home page with product listing, search, and sorting functionality.
    task 10 sabah ( index,html)
    """
    # استعلام جلب المنتجات مع البحث والترتيب
    products = Product.objects.annotate(
        average_rating=Avg('reviews__rating', filter=Q(reviews__visible=True)),
        reviews_count=Count('reviews', filter=Q(reviews__visible=True))
    )

    # 🔍 فلترة حسب الاسم
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(name__icontains=search_query)

    # ⬇️ الترتيب حسب طلب المستخدم
    sort_by = request.GET.get('sort', '')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        products = products.order_by('-average_rating')
    elif sort_by == 'reviews':
        products = products.order_by('-reviews_count')
    else:
        products = products.order_by('-id')  # Default to newest products

    # Get unread notifications count for authenticated users
    unread_notifications_count = 0
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(
            user=request.user, read=False
        ).count()

    context = {
        'products': products,
        'search_query': search_query,
        'sort_by': sort_by,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'index.html', context)


def product_list_view(request):
    """Alternative product listing view."""
    return home(request)  # Redirect to home for consistency


# task 10 product_details.html
def product_detail_view(request, pk=None, product_id=None):
    """Product detail view with reviews and all necessary context"""
    # Handle both pk and product_id parameter names
    product_id = pk or product_id
    product = get_object_or_404(Product, id=product_id)
    
    # Get reviews with filtering and sorting
    reviews = Review.objects.filter(product=product).select_related('user')
    
    # Apply filters
    rating_filter = request.GET.get('rating_filter')
    if rating_filter:
        reviews = reviews.filter(rating=rating_filter)
    
    # Apply sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'newest':
        reviews = reviews.order_by('-created_at')
    elif sort_by == 'oldest':
        reviews = reviews.order_by('created_at')
    elif sort_by == 'highest':
        reviews = reviews.order_by('-rating')
    elif sort_by == 'lowest':
        reviews = reviews.order_by('rating')
    elif sort_by == 'helpful':
        # This requires the helpful_users field
        reviews = reviews.annotate(
            helpful_count=models.Count('helpful_users')
        ).order_by('-helpful_count')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(reviews, 10)  # 10 reviews per page
    page_number = request.GET.get('page')
    reviews = paginator.get_page(page_number)
    
    # Check if user has already reviewed this product
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = Review.objects.filter(
            product=product, 
            user=request.user
        ).exists()
    
    # Check if product is in session favorites (session-based implementation)
    is_favorite = False
    if request.user.is_authenticated:
        favorites = request.session.get('favorites', [])
        is_favorite = product_id in favorites
    
    context = {
        'product': product,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
        'is_favorite': is_favorite,
    }
    
    return render(request, 'product_detail.html', context)

@login_required
def add_review(request, pk):
    """Add a new review for a product."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 0))
            text = request.POST.get('review_text', '').strip()

            # Validate rating
            if not (1 <= rating <= 5):
                messages.error(request, 'التقييم يجب أن يكون بين 1 و 5')
                return redirect('product-detail', pk=product.id)
            
            # Validate review text
            if not text:
                messages.error(request, 'نص المراجعة مطلوب')
                return redirect('product-detail', pk=product.id)
            
            # Check if user already reviewed this product
            if Review.objects.filter(product=product, user=request.user).exists():
                messages.error(request, 'لقد قمت بمراجعة هذا المنتج من قبل')
                return redirect('product-detail', pk=product.id)

            Review.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                review_text=text,
                visible=True  # Could be set to False for moderation
            )
            
            messages.success(request, 'تم إضافة المراجعة بنجاح')
            
        except ValueError:
            messages.error(request, 'قيمة التقييم غير صحيحة')
        except Exception as e:
            messages.error(request, 'حدث خطأ أثناء إضافة المراجعة')

    return redirect('product-detail', pk=product.id)


@login_required
def add_comment(request, review_id):
    """Add a comment to a review."""
    review = get_object_or_404(Review, id=review_id)
    
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            ReviewComment.objects.create(
                review=review,
                user=request.user,
                text=text
            )
            messages.success(request, 'تم إضافة التعليق بنجاح')
        else:
            messages.error(request, 'نص التعليق مطلوب')
    
    return redirect('product-detail', pk=review.product.id)


@login_required
def report_review(request, pk):
    """Report a review as inappropriate."""
    review = get_object_or_404(Review, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'غير محدد').strip()
        
        if not reason:
            messages.error(request, 'يجب تحديد سبب البلاغ')
        else:
            report, created = ReviewReport.objects.get_or_create(
                review=review,
                user=request.user,
                defaults={'reason': reason}
            )
            
            if created:
                messages.success(request, 'تم الإبلاغ عن المراجعة بنجاح')
            else:
                messages.info(request, 'تم الإبلاغ عن هذه المراجعة من قبل')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def edit_review_view(request, review_id):
    """Edit user's own review."""
    review = get_object_or_404(Review, id=review_id, user=request.user)

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', review.rating))
            review_text = request.POST.get('review_text', '').strip()

            # Validate rating
            if not (1 <= rating <= 5):
                messages.error(request, 'التقييم يجب أن يكون بين 1 و 5')
                return render(request, 'edit_review.html', {'review': review})
            
            # Validate review text
            if not review_text:
                messages.error(request, 'نص المراجعة مطلوب')
                return render(request, 'edit_review.html', {'review': review})

            review.rating = rating
            review.review_text = review_text
            review.save()

            messages.success(request, 'تم تحديث المراجعة بنجاح.')
            return redirect('user_profile')
            
        except ValueError:
            messages.error(request, 'قيمة التقييم غير صحيحة')
        except Exception as e:
            messages.error(request, 'حدث خطأ أثناء تحديث المراجعة')

    return render(request, 'edit_review.html', {'review': review})


@login_required
def delete_review(request, review_id):
    """Delete user's own review."""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    
    if request.method == 'POST':
        try:
            review.delete()
            messages.success(request, 'تم حذف المراجعة بنجاح.')
        except Exception as e:
            messages.error(request, 'حدث خطأ أثناء حذف المراجعة')
    
    return redirect('user_profile')


@login_required
def user_profile(request):
    """User profile page with their reviews and statistics."""
    user = request.user

    # مراجعات المستخدم
    user_reviews = Review.objects.filter(user=user)\
        .select_related('product')\
        .prefetch_related('interactions', 'comments')\
        .order_by('-created_at')
    user_reviews_count = user_reviews.count()

    # عدد الإعجابات التي استلمها المستخدم في مراجعاته
    user_likes_received = ReviewInteraction.objects.filter(
        review__user=user, helpful=True
    ).count()

    # عدد التعليقات التي كتبها المستخدم
    user_comments_count = ReviewComment.objects.filter(user=user).count()

    # المراجعات التي أعجبت المستخدم
    liked_reviews = ReviewInteraction.objects.filter(
        user=user, helpful=True
    ).select_related('review', 'review__product', 'review__user')\
     .order_by('-created_at')[:10]  # Show last 10

    context = {
        'user_reviews': user_reviews,
        'user_reviews_count': user_reviews_count,
        'user_likes_received': user_likes_received,
        'user_comments_count': user_comments_count,
        'liked_reviews': liked_reviews,
    }

    return render(request, 'user_profile.html', context)

@login_required
def review_helpful(request, review_id):
    """Handle helpful/unhelpful votes for reviews"""
    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id)
        action = request.POST.get('action')
        
        # Prevent users from voting on their own reviews
        if review.user == request.user:
            messages.error(request, 'لا يمكنك التصويت على مراجعتك الخاصة')
            return redirect('product-detail', pk=review.product.id)
        
        # You'll need to add these fields to your Review model:
        # helpful_users = models.ManyToManyField(User, related_name='helpful_reviews', blank=True)
        # unhelpful_users = models.ManyToManyField(User, related_name='unhelpful_reviews', blank=True)
        
        if action == 'helpful':
            # Remove from unhelpful if exists
            if hasattr(review, 'unhelpful_users') and request.user in review.unhelpful_users.all():
                review.unhelpful_users.remove(request.user)
            
            # Toggle helpful vote
            if hasattr(review, 'helpful_users'):
                if request.user in review.helpful_users.all():
                    review.helpful_users.remove(request.user)
                    messages.info(request, 'تم إلغاء تصويتك')
                else:
                    review.helpful_users.add(request.user)
                    messages.success(request, 'شكراً لك على التصويت!')
        
        elif action == 'unhelpful':
            # Remove from helpful if exists
            if hasattr(review, 'helpful_users') and request.user in review.helpful_users.all():
                review.helpful_users.remove(request.user)
            
            # Toggle unhelpful vote
            if hasattr(review, 'unhelpful_users'):
                if request.user in review.unhelpful_users.all():
                    review.unhelpful_users.remove(request.user)
                    messages.info(request, 'تم إلغاء تصويتك')
                else:
                    review.unhelpful_users.add(request.user)
                    messages.info(request, 'تم تسجيل رأيك')
        
        # If this is an AJAX request, return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            helpful_count = review.helpful_users.count() if hasattr(review, 'helpful_users') else 0
            unhelpful_count = review.unhelpful_users.count() if hasattr(review, 'unhelpful_users') else 0
            
            return JsonResponse({
                'success': True,
                'helpful_count': helpful_count,
                'unhelpful_count': unhelpful_count,
                'user_voted_helpful': request.user in review.helpful_users.all() if hasattr(review, 'helpful_users') else False,
                'user_voted_unhelpful': request.user in review.unhelpful_users.all() if hasattr(review, 'unhelpful_users') else False,
            })
        
        return redirect('product-detail', pk=review.product.id)
    
    return redirect('home')

@login_required
def toggle_favorite(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        # Simple session-based favorites (no database)
        favorites = request.session.get('favorites', [])
        
        if product_id in favorites:
            favorites.remove(product_id)
            messages.success(request, 'تم إزالة المنتج من المفضلة')
        else:
            favorites.append(product_id)
            messages.success(request, 'تم إضافة المنتج للمفضلة')
        
        request.session['favorites'] = favorites
        return redirect('product-detail', pk=product_id)
    
    return redirect('home')

# =============================================================================
# AUTHENTICATION VIEWS
# =============================================================================

def register_view(request):
    """User registration view."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        # Basic validation
        if not username:
            messages.error(request, "اسم المستخدم مطلوب")
            return render(request, 'register.html')
        
        if not email:
            messages.error(request, "البريد الإلكتروني مطلوب")
            return render(request, 'register.html')
        
        if not password:
            messages.error(request, "كلمة المرور مطلوبة")
            return render(request, 'register.html')
        
        if len(password) < 6:
            messages.error(request, "كلمة المرور يجب أن تكون 6 أحرف على الأقل")
            return render(request, 'register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "اسم المستخدم موجود بالفعل")
            return render(request, 'register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "البريد الإلكتروني مستخدم بالفعل")
            return render(request, 'register.html')

        try:
            user = User.objects.create_user(
                username=username, 
                password=password, 
                email=email
            )
            login(request, user)
            messages.success(request, "تم إنشاء الحساب بنجاح")
            return redirect('home')
        except Exception as e:
            messages.error(request, "حدث خطأ أثناء إنشاء الحساب")

    return render(request, 'register.html')


def login_view(request):
    """User login view."""
    form = AuthenticationForm(data=request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        messages.success(request, f"مرحباً {form.get_user().username}")
        
        # التقاط قيمة next إذا كانت موجودة في POST أو GET
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('home')  # توجيه للصفحة الرئيسية في حال عدم وجود next
    
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """User logout view."""
    username = request.user.username if request.user.is_authenticated else None
    logout(request)
    
    if username:
        messages.success(request, f"تم تسجيل الخروج بنجاح. وداعاً {username}")
    
    return redirect('home')


# =============================================================================
# NOTIFICATION VIEWS
# =============================================================================

@login_required
def notifications_page(request):
    """Enhanced notifications page with filtering and pagination."""
    notifications_query = Notification.objects.filter(user=request.user)\
        .select_related('related_review', 'related_review__product', 'related_user')\
        .order_by('-created_at')
    
    # Filter by type if specified
    filter_type = request.GET.get('type')
    if filter_type and filter_type != 'all':
        notifications_query = notifications_query.filter(notification_type=filter_type)
    
    # Filter by read status
    filter_read = request.GET.get('read')
    if filter_read == 'unread':
        notifications_query = notifications_query.filter(read=False)
    elif filter_read == 'read':
        notifications_query = notifications_query.filter(read=True)
    
    # Pagination
    paginator = Paginator(notifications_query, 20)
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)
    
    # Get counts for badges
    unread_count = Notification.objects.filter(user=request.user, read=False).count()
    total_count = Notification.objects.filter(user=request.user).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'total_count': total_count,
        'filter_type': filter_type or 'all',
        'filter_read': filter_read or 'all',
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    return render(request, 'notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'تم وضع علامة مقروء على الإشعار'
        })
    
    # Redirect to action URL if available
    if notification.action_url:
        return redirect(notification.action_url)
    
    return redirect('notifications')


@login_required
def mark_all_read(request):
    """Mark all notifications as read with better feedback."""
    if request.method == 'POST':
        unread_notifications = Notification.objects.filter(user=request.user, read=False)
        count = unread_notifications.count()
        
        if count > 0:
            # Update read status and timestamp
            now = timezone.now()
            unread_notifications.update(read=True, read_at=now)
            messages.success(request, f'تم وضع علامة "مقروء" على {count} إشعار')
        else:
            messages.info(request, 'لا توجد إشعارات غير مقروءة')
    
    return redirect('notifications')


@login_required
def clear_old_notifications(request):
    """Clear notifications older than 30 days."""
    if request.method == 'POST':
        thirty_days_ago = timezone.now() - timedelta(days=30)
        old_notifications = Notification.objects.filter(
            user=request.user,
            created_at__lt=thirty_days_ago
        )
        count = old_notifications.count()
        old_notifications.delete()
        
        if count > 0:
            messages.success(request, f'تم حذف {count} إشعار قديم')
        else:
            messages.info(request, 'لا توجد إشعارات قديمة للحذف')
    
    return redirect('notifications')


@login_required
def clear_all_notifications(request):
    """Clear all user notifications with confirmation."""
    if request.method == 'POST':
        count = Notification.objects.filter(user=request.user).count()
        Notification.objects.filter(user=request.user).delete()
        messages.success(request, f'تم حذف جميع الإشعارات ({count} إشعار)')
    
    return redirect('notifications')


@login_required
def get_unread_count(request):
    """API endpoint to get unread notifications count."""
    count = Notification.objects.filter(user=request.user, read=False).count()
    return JsonResponse({'unread_count': count})


# =============================================================================
# NOTIFICATION UTILITIES
# =============================================================================

def create_notification(user, message, notification_type='system', related_review=None, 
                       related_user=None, action_url=None):
    """
    Utility function to create notifications consistently.
    
    Args:
        user: Target user for the notification
        message: Notification message
        notification_type: Type of notification
        related_review: Related review object (optional)
        related_user: User who triggered the notification (optional)
        action_url: URL to redirect when notification is clicked (optional)
    """
    return Notification.objects.create(
        user=user,
        message=message,
        notification_type=notification_type,
        related_review=related_review,
        related_user=related_user,
        action_url=action_url
    )


def notify_review_comment(review, commenter, comment):
    """Create notification when someone comments on a review."""
    if review.user != commenter:  # Don't notify user about their own comment
        message = f"{commenter.username} علّق على مراجعتك للمنتج {review.product.name}"
        action_url = f"/reviews/{review.id}/"
        
        create_notification(
            user=review.user,
            message=message,
            notification_type='comment',
            related_review=review,
            related_user=commenter,
            action_url=action_url
        )


def notify_review_like(review, liker):
    """Create notification when someone likes a review."""
    if review.user != liker:  # Don't notify user about their own like
        message = f"{liker.username} أعجب بمراجعتك للمنتج {review.product.name}"
        action_url = f"/reviews/{review.id}/"
        
        create_notification(
            user=review.user,
            message=message,
            notification_type='like',
            related_review=review,
            related_user=liker,
            action_url=action_url
        )


# =============================================================================
# NOTIFICATION TEMPLATE TAGS (Optional)
# =============================================================================

from django import template

register = template.Library()

@register.inclusion_tag('notifications/notification_badge.html', takes_context=True)
def notification_badge(context):
    """Template tag to show notification badge."""
    user = context['request'].user
    if user.is_authenticated:
        unread_count = Notification.objects.filter(user=user, read=False).count()
        return {'unread_count': unread_count}
    return {'unread_count': 0}


@register.filter
def time_since_arabic(value):
    """Arabic time since filter for notifications."""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    diff = now - value
    
    if diff < timedelta(minutes=1):
        return "الآن"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"منذ {minutes} دقيقة"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"منذ {hours} ساعة"
    elif diff < timedelta(days=7):
        return f"منذ {diff.days} يوم"
    else:
        return value.strftime("%Y/%m/%d")



# =============================================================================
# ADMIN VIEWS
# =============================================================================

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard with statistics."""
    # Get some basic statistics
    stats = {
        'total_products': Product.objects.count(),
        'total_reviews': Review.objects.count(),
        'visible_reviews': Review.objects.filter(visible=True).count(),
        'pending_reviews': Review.objects.filter(visible=False).count(),
        'total_users': User.objects.count(),
        'reviews_with_banned_words': Review.objects.filter(contains_banned_words=True).count(),
        'total_reports': ReviewReport.objects.count(),
        'total_banned_words': BannedWord.objects.count(),
    }
    
    # Recent activity
    recent_reviews = Review.objects.select_related('user', 'product')\
        .order_by('-created_at')[:10]
    recent_reports = ReviewReport.objects.select_related('user', 'review', 'review__product')\
        .order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'recent_reviews': recent_reviews,
        'recent_reports': recent_reports,
    }
    
    return render(request, 'admin_dashboard.html', context)


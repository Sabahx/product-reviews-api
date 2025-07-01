from django.shortcuts import render
from .serializers import RegisterSerializer, ReviewCommentSerializer, ReviewVoteSerializer
from rest_framework import viewsets, permissions, status ,generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.views import APIView
from .models import Review, ReviewComment, ReviewVote ,Product,Notification
from .serializers import ReviewSerializer , NotificationSerializer
from .permissions import IsOwnerOrReadOnly
from datetime import timedelta
from django.utils import timezone
from django.db.models import Subquery, OuterRef ,Avg ,Count , Q
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from .models import Product ,ReviewInteraction
from .serializers import ProductSerializer
from django.db import models
from django.http import HttpResponse
import csv
import openpyxl
from io import BytesIO


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'pk'

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        
        if self.action in ['update', 'partial_update', 'destroy', 'retrieve']:
           return Review.objects.all()  # ← هذا السطر هو المحتوى المتوقع داخل if
    
        queryset = Review.objects.filter(visible=True)
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product__id=product_id)
        rating = self.request.query_params.get('rating')
        if rating:
            queryset = queryset.filter(rating=rating)
        return queryset
        
    ##mjd⬇
    @action(detail=True, methods=['post'],permission_classes=[IsAuthenticated])
    def interact(self, request, pk=None):
        """المستخدم يقيّم المراجعة بأنها مفيدة أو غير مفيدة"""
        review = self.get_object()
        helpful = request.data.get('helpful')

        if helpful is None:
            return Response({"error": "يجب إرسال قيمة الحقل 'helpful'"}, status=status.HTTP_400_BAD_REQUEST)

        # تقييد كل مستخدم بتفاعل واحد لكل مراجعة
        interaction, created = ReviewInteraction.objects.update_or_create(
            review=review,
            user=request.user,
            defaults={'helpful': helpful}
        )
        return Response({"message": "تم حفظ التفاعل"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='top-review')
    def top_review(self, request):
        """عرض المراجعة التي حصلت على أكبر عدد من الإعجابات"""
        
        top = Review.objects.annotate(
            likes=Count('interactions', filter=models.Q(interactions__helpful=True))
        ).order_by('-likes').first()

        if top:
            return Response(self.get_serializer(top).data)
        return Response({"message": "لا توجد مراجعات بعد"}, status=status.HTTP_404_NOT_FOUND)
##⬆
    #mjd task9⬇
    #عداد
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views = models.F('views') + 1  # زيادة بدون تعارض مع السباق (race condition)
        instance.save(update_fields=["views"])
        instance.refresh_from_db()
        return super().retrieve(request, *args, **kwargs)
    
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

    # Review approval by admin
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return Response(status=404)
        
        # Check if review is already approved
        if review.visible:
            return Response({
                'status': 'already_approved',
                'message': 'المراجعة موافق عليها مسبقاً',
                'review_id': review.id,
                'warning': 'لا يوجد إجراء مطلوب، المراجعة ظاهرة بالفعل'
            }, status=200)
        
        try:    
            review.visible = request.data.get("visible", True)
            review.save()
            
            # Create notification for the reviewer
            Notification.objects.create(
                user=review.user,
                message=f"تمت الموافقة على مراجعتك للمنتج {review.product.name}",
                read = False,
                created_at = timezone.now(),
                related_review=f"/products/{review.product.id}/reviews/{review.id}",
            )
            
            # Prepare detailed response
            serializer = ReviewSerializer(review)
            response_data = {
                'status': 'success',
                'message': 'تمت الموافقة على المراجعة بنجاح',
                'data': serializer.data,
                'details': {
                    'review_id': review.id,
                    'product': ProductSerializer(review.product),
                    'approval_time': timezone.now(),
                }
            }
            
            return Response(response_data, status=200)
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'فشل في الموافقة على المراجعة',
                'error': str(e),
                'error_code': 'REVIEW_APPROVAL_FAILED',
                'suggested_action': 'التحقق من سجلات الخادم وإعادة المحاولة'
            }, status=500)
    
    # Commenting on reviews
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

    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        review = self.get_object()
        user = request.user
        helpful = request.data.get('helpful', None)
        
        if helpful is None:
            return Response({'error': 'Helpful field is required'}, status=status.HTTP_400_BAD_REQUEST)
        
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


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]



class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # queryset ليحسب average_rating و reviews_count باستخدام annotate.

    def get_queryset(self):
        return Product.objects.annotate(
            average_rating=Avg('reviews__rating'),
            reviews_count=Count('reviews')
        )


    # السماح فقط للمشرفين بالإضافة أو التعديل، وباقي المستخدمين للقراءة فقط
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]
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


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({'status': 'marked as read'})


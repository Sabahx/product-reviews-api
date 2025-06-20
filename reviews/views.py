from django.shortcuts import render

# Create your views here.

from .serializers import RegisterSerializer
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Review
from .serializers import ReviewSerializer
from .permissions import IsOwnerOrReadOnly
from rest_framework import generics
from rest_framework.permissions import AllowAny

from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from .models import Product
from .serializers import ProductSerializer




class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        review = self.get_object()
        review.visible = True
        review.save()
        return Response({'status': 'تمت الموافقة على المراجعة'})


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]



class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # السماح فقط للمشرفين بالإضافة أو التعديل، وباقي المستخدمين للقراءة فقط
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        product = self.get_object()
        reviews = product.reviews.filter(visible=True)
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)
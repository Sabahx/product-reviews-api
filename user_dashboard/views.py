from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from reviews.models import Product, Review
# from reviews.forms import ReviewForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from .forms import ReviewForm
from django.db.models import Prefetch          # ← أضفّي هذا السطر

def login_user(request):
    """
    تسجيل دخول المستخدم العادي.
    بعد النجاح يُعاد توجيهه إلى قائمة المنتجات.
    """
    next_url = request.GET.get('next', None)
    error = None

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(next_url or 'user_dashboard:product_list')
        else:
            error = 'بيانات الدخول غير صحيحة'
    else:
        form = AuthenticationForm(request)

    return render(request, 'login.html', {
        'form': form,
        'next': next_url or '',
        'error': error,
    })  

@login_required
def add_review(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            rev = form.save(commit=False)
            rev.product = product
            rev.user    = request.user
            rev.visible = False
            rev.save()
    return redirect('user_dashboard:home')

@login_required
def home(request):
    # نجلب المراجعات المعتمدة مسبقًا
    approved_qs = Review.objects.filter(visible=True)
    products = Product.objects.order_by('-created_at').prefetch_related(
        Prefetch('reviews', queryset=approved_qs, to_attr='approved_reviews')
    )
    return render(request, 'user_dashboard/home.html', {
        'products': products
    })
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    # مراجعات المنتج المعتمدة
    approved_reviews = product.reviews.filter(visible=True).select_related('user')
    # نموذج لإضافة مراجعة جديدة
    form = ReviewForm()
    return render(request, 'user_dashboard/product_detail.html', {
        'product': product,
        'approved_reviews': approved_reviews,
        'form': form,
    })
    
@login_required
def add_review(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            rev = form.save(commit=False)
            rev.product = product
            rev.user    = request.user
            rev.visible = False
            rev.save()
    return redirect('user_dashboard:home')
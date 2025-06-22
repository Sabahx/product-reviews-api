from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, Q
from reviews.models import Product, Review, Notification

def is_staff_user(user):
    return user.is_staff

# =====================================
# صفحة اللوحة الرئيسية
# =====================================
@login_required
@user_passes_test(is_staff_user)
def home(request):
    # إحصائيات المنتجات
    products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__visible=True)),
        approved_count=Count('reviews', filter=Q(reviews__visible=True)),
        pending_count=Count('reviews', filter=Q(reviews__visible=False))
    )
    # أحدث 5 مراجعات معتمدة
    recent_reviews = Review.objects.filter(visible=True).order_by('-created_at')[:5]
    # عدد التنبيهات غير المقروءة
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'home.html', {
        'products': products,
        'recent_reviews': recent_reviews,
        'unread_notifs': unread_notifs,
    })

# =====================================
# مراجعات بانتظار الموافقة
# =====================================
@login_required
@user_passes_test(is_staff_user)
def pending_reviews(request):
    reviews = Review.objects.filter(visible=False).order_by('-created_at')
    return render(request, 'pending_reviews.html', {
        'reviews': reviews,
    })

@login_required
@user_passes_test(is_staff_user)
def approve_review(request, review_id):
    rev = get_object_or_404(Review, pk=review_id, visible=False)
    rev.visible = True
    rev.save()
    return redirect('admin_dashboard:pending_reviews')

@login_required
@user_passes_test(is_staff_user)
def delete_review(request, review_id):
    rev = get_object_or_404(Review, pk=review_id)
    rev.delete()
    return redirect('admin_dashboard:pending_reviews')

# =====================================
# إحصائيات المنتجات
# =====================================
@login_required
@user_passes_test(is_staff_user)
def product_stats(request):
    products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__visible=True)),
        approved_count=Count('reviews', filter=Q(reviews__visible=True)),
        pending_count=Count('reviews', filter=Q(reviews__visible=False))
    )
    # حساب المجاميع
    total_products = products.count()
    total_approved = sum(p.approved_count for p in products)
    total_pending  = sum(p.pending_count  for p in products)

    return render(request, 'product_stats.html', {
        'products': products,
        'total_products': total_products,
        'total_approved': total_approved,
        'total_pending': total_pending,
    })

# =====================================
# التنبيهات
# =====================================
@login_required
@user_passes_test(is_staff_user)
def notifications(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications.html', {
        'notifications': notifs,
    })

@login_required
@user_passes_test(is_staff_user)
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, pk=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return redirect('admin_dashboard:notifications')

# =====================================
# جميع المراجعات (للإشراف)
# =====================================
@login_required
@user_passes_test(is_staff_user)
def all_reviews(request):
    reviews = Review.objects.select_related('product', 'user').order_by('-created_at')
    return render(request, 'all_reviews.html', {
        'reviews': reviews,
    })

# =====================================
# CRUD المنتجات (واجهات HTML تستدعي API)
# =====================================
@login_required
@user_passes_test(is_staff_user)
def product_list(request):
    # جلب كل المنتجات من الــ ORM
    products = Product.objects.order_by('-created_at')
    return render(request, 'product_list.html', {
        'products': products
    })
@login_required
@user_passes_test(is_staff_user)
def product_form(request, pk=None):
    return render(request, 'product_form.html', {
        'pk': pk
    })

@login_required
@user_passes_test(is_staff_user)
def product_delete_confirm(request, pk):

    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product.delete()
        return redirect('admin_dashboard:product_list')

    return render(request, 'product_confirm_delete.html', {
        'product': product
    })

@login_required
@user_passes_test(is_staff_user)
def product_stats(request):
    # Annotate each product
    products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__visible=True)),
        approved_count=Count('reviews', filter=Q(reviews__visible=True)),
        pending_count=Count('reviews', filter=Q(reviews__visible=False))
    )

    # احسب المجاميع هنا
    total_products = products.count()
    total_approved = sum(p.approved_count for p in products)
    total_pending  = sum(p.pending_count  for p in products)

    return render(request, 'product_stats.html', {
        'products': products,
        'total_products': total_products,
        'total_approved': total_approved,
        'total_pending': total_pending,
    })
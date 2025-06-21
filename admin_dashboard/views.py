from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from reviews.models import Review

# @staff_member_required
# def dashboard(request):
#    return render(request, 'admin_dashboard/dashboard.html')

@staff_member_required
def review_list(request):
    qs = Review.objects.all().order_by('-created_at')
    rating = request.GET.get('rating')
    search = request.GET.get('search')
    if rating:
        qs = qs.filter(rating=rating)
    if search:
        qs = qs.filter(text__icontains=search)
    return render(request, 'admin_dashboard/review_list.html', {'reviews': qs})

@staff_member_required
def review_approve(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.visible = True
    review.save()
    return redirect('admin_dashboard:review_list')

@staff_member_required
def review_reject(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.visible = False
    review.save()
    return redirect('admin_dashboard:review_list')

@staff_member_required
def dashboard(request):
    total = Review.objects.count()
    pending = Review.objects.filter(visible=False).count()
    return render(request, 'admin_dashboard/dashboard.html', {
        'reviews_count_all': total,
        'reviews_count_pending': pending,
    })

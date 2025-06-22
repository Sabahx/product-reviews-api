from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import SignUpForm
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from django.urls import reverse

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('user_dashboard:home')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})

def admin_login(request):
    next_url = request.GET.get('next', reverse('admin_dashboard:home'))
    error = None

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                return redirect(request.POST.get('next') or next_url)
            else:
                error = 'عذراً ليس لديك صلاحية المشرف'
        else:
            error = 'بيانات الدخول غير صحيحة'
    else:
        form = AuthenticationForm(request)

    return render(request, 'accounts/login.html', {
        'form': form,
        'next': next_url,
        'error': error,
    })

def custom_login(request):
    # المسار الافتراضي لو ما في next
    default_redirect = reverse('admin_dashboard:home')
    # جيب قيمة next من GET أو استخدم الافتراضي
    next_url = request.GET.get('next', default_redirect)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        # جيب قيمة next من الـ POST (في حال فرّمتها hidden input)
        next_url = request.POST.get('next') or default_redirect

        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {
        'form': form,
        'next': next_url,
    })
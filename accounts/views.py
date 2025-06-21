from django.views.generic import FormView
from django.contrib.auth import login
from django.shortcuts import redirect
from .forms import SignUpForm
from django.contrib.auth.views import LoginView
from django.contrib import messages

class SignUpView(FormView):
    template_name = 'accounts/signup.html'
    form_class    = SignUpForm
    success_url   = '/dashboard/'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "تم إنشاء الحساب وتسجيل الدخول بنجاح.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "هناك أخطاء في البيانات المدخلة، يرجى التحقق.")
        return self.render_to_response(self.get_context_data(form=form))
    
class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"أهلاً {form.get_user().username}، تم تسجيل الدخول بنجاح.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
        return self.render_to_response(self.get_context_data(form=form))

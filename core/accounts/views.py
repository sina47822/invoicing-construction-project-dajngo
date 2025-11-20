from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Create your views here.
class RegisterView(View):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'accounts/registration/register.html', {'form': form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ثبت‌نام موفق! حالا وارد شوید.')
            return redirect('accounts:login')
        return render(request, 'accounts/registration/register.html', {'form': form})

def dashboard(request):
    # این می‌تونه صفحه اصلی بعد از ورود باشه. فعلاً ساده نگه می‌داریم، بعداً می‌تونی محتوا اضافه کنی
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return render(request, 'accounts/dashboard.html', {})  # template dashboard.html

@login_required
def profile_view(request):
    return render(request, 'accounts/profile/profile.html')

@login_required
def settings_view(request):
    user = request.user

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")

        # تغییر مشخصات پایه کاربر
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        messages.success(request, "تنظیمات حساب با موفقیت ذخیره شد.")
        return redirect("settings")

    return render(request, "accounts/profile/settings.html", {"user": user})
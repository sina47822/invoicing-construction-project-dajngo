from django.shortcuts import render

# Create your views here.
class RegisterView(View):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'registration/register.html', {'form': form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ثبت‌نام موفق! حالا وارد شوید.')
            return redirect('login')
        return render(request, 'registration/register.html', {'form': form})

def dashboard(request):
    # این می‌تونه صفحه اصلی بعد از ورود باشه. فعلاً ساده نگه می‌داریم، بعداً می‌تونی محتوا اضافه کنی
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'dashboard.html', {})  # template dashboard.html
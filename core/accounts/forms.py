
class UserInvitationForm(forms.ModelForm):
    class Meta:
        model = UserInvitation
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'email': 'آدرس ایمیل',
            'role': 'نقش در پروژه'
        }

class ProjectAccessForm(forms.Form):
    """
    فرم برای مدیریت دسترسی‌های پروژه
    """
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project')
        self.current_user = kwargs.pop('current_user')
        super().__init__(*args, **kwargs)
        
        # فیلدهای داینامیک برای کاربران موجود
        project_users = ProjectUser.objects.filter(project=self.project)
        for pu in project_users:
            self.fields[f'user_{pu.id}_role'] = forms.ChoiceField(
                choices=ProjectUser.PROJECT_ROLE_CHOICES,
                initial=pu.role,
                label=f"نقش {pu.user.get_full_name() or pu.user.username}",
                widget=forms.Select(attrs={'class': 'form-select'})
            )
            self.fields[f'user_{pu.id}_remove'] = forms.BooleanField(
                required=False,
                label='حذف کاربر',
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )
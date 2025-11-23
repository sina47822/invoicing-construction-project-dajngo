# project/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Max
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from django.core.paginator import Paginator
import logging

# Models
from .models import Project
from accounts.models import ProjectUser, ProjectRole, UserProfile
from sooratvaziat.models import ProjectFinancialSummary, MeasurementSession, MeasurementSessionItem

# Forms and decorators
#forms 
from django.forms import inlineformset_factory, modelform_factory, HiddenInput, TextInput, Select
from .forms import ProjectCreateForm, ProjectEditForm, UserCreateForm, ProjectUserAssignmentForm
from .decorators import project_access_required, role_required

# Utils
from sooratvaziat.utils import (
    gregorian_to_jalali,
    jalali_to_gregorian,
    format_number_int,
    _to_decimal,
    _get_progress_class,
    format_number_decimal,
    get_status_badge,
    format_currency
)

logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)

@login_required
def user_create(request):
    """
    ایجاد کاربر جدید توسط پیمانکار
    """
    if not request.user.profile.is_verified:  # فرض کنید پیمانکاران تأیید شده‌اند
        messages.error(request, 'شما مجوز ایجاد کاربر جدید را ندارید.')
        return redirect('project:project_list')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    
                    messages.success(request, f'کاربر {user.username} با موفقیت ایجاد شد.')
                    return redirect('project:user_list')
                    
            except Exception as e:
                messages.error(request, f'خطا در ایجاد کاربر: {str(e)}')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید')
    else:
        form = UserCreateForm()
    
    context = {
        'title': 'ایجاد کاربر جدید',
        'form': form,
    }
    return render(request, 'project/user_form.html', context)

@login_required
@project_access_required(['admin' , 'contractor'])
def project_users_manage(request, pk):
    """
    مدیریت کاربران پروژه - فقط پیمانکار
    """
    project = get_object_or_404(Project, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = ProjectUserAssignmentForm(request.POST, project=project, current_user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'کاربر با موفقیت به پروژه اضافه شد.')
                return redirect('project:project_users_manage', pk=project.pk)
            except Exception as e:
                messages.error(request, f'خطا در اضافه کردن کاربر: {str(e)}')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید')
    else:
        form = ProjectUserAssignmentForm(project=project, current_user=request.user)
    
    # کاربران پروژه
    project_users = project.project_users.filter(is_active=True).select_related('user', 'role', 'assigned_by')
    
    # نقش‌های موجود
    available_roles = ProjectRole.objects.filter(is_active=True)
    
    context = {
        'title': f'مدیریت کاربران - {project.project_name}',
        'project': project,
        'form': form,
        'project_users': project_users,
        'available_roles': available_roles,
    }
    return render(request, 'project/project_users_manage.html', context)

@login_required
@project_access_required(['admin' , 'contractor'])
def project_user_remove(request, project_pk, user_pk):
    """
    حذف کاربر از پروژه - فقط پیمانکار
    """
    project = get_object_or_404(Project, pk=project_pk, is_active=True)
    project_user = get_object_or_404(ProjectUser, pk=user_pk, project=project, is_active=True)
    
    if request.method == 'POST':
        try:
            project_user.is_active = False
            project_user.save()
            messages.success(request, 'کاربر از پروژه حذف شد.')
        except Exception as e:
            messages.error(request, f'خطا در حذف کاربر: {str(e)}')
    
    return redirect('project:project_users_manage', pk=project.pk)

# ویوهای AJAX برای دریافت داده‌ها
@login_required
def get_users_by_role(request):
    """
    دریافت کاربران بر اساس نقش (AJAX)
    """
    role_name = request.GET.get('role')
    
    if role_name:
        users = User.objects.filter(
            roles__name=role_name,
            roles__is_active=True,
            is_active=True
        ).values('id', 'username', 'first_name', 'last_name')
        
        users_list = list(users)
        return JsonResponse(users_list, safe=False)
    
    return JsonResponse([], safe=False)

@login_required
def get_project_users(request, pk):
    """
    دریافت کاربران یک پروژه (AJAX)
    """
    project = get_object_or_404(Project, pk=pk, is_active=True)
    
    if not project.has_access(request.user):
        return JsonResponse([], safe=False)
    
    users = project.project_users.filter(is_active=True).values(
        'user__id', 
        'user__username', 
        'user__first_name', 
        'user__last_name',
        'role__name'
    )
    
    users_list = list(users)
    return JsonResponse(users_list, safe=False)

@login_required
@role_required(['contractor', 'admin'])
def project_delete(request, pk):
    """
    View برای حذف پروژه
    """
    # اگر کاربر ادمین است، همه پروژه‌های فعال را نشان بده
    if request.user.is_superuser:
        project = get_object_or_404(Project, pk=pk, is_active=True)
    else:
        # در غیر این صورت، پروژه‌هایی که کاربر ایجاد کرده یا در آنها نقش دارد
        project = get_object_or_404(
            Project,
            Q(created_by=request.user) | Q(project_users__user=request.user),
            pk=pk,
            is_active=True
        )

    if not project.can_edit(request.user):
        messages.error(request, 'شما دسترسی حذف این پروژه را ندارید')
        return redirect('project:project_detail', pk=project.pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # نرم حذف (set is_active = False)
                project.is_active = False
                project.deleted_at = timezone.now()
                project.save()
                
                messages.success(
                    request, 
                    f'پروژه "{project.project_name}" با موفقیت غیرفعال شد.'
                )
                
                return redirect('projects:project_list')
                
        except Exception as e:
            logger.error(f"Project delete error: {str(e)}", exc_info=True)
            messages.error(
                request, 
                f'خطا در حذف پروژه: {str(e)}'
            )
            return redirect('projects:project_edit', pk=pk)
    
    # GET request - نمایش صفحه تأیید حذف
    context = {
        'project': project,
        'title': f'حذف پروژه: {project.project_name}',
        'page_title': 'تأیید حذف',
        'active_menu': 'projects',
    }
    return render(request, 'project/project_delete.html', context)

@login_required
@role_required(['contractor', 'admin'])
def project_create(request):
    """
    View برای ایجاد پروژه جدید
    """
    if request.method == 'POST':
        print("📨 دریافت POST request")
        print("📋 داده‌های فرم:", dict(request.POST))
        
        form = ProjectCreateForm(request.POST, request.FILES, current_user=request.user)
        
        if form.is_valid():
            print("✅ فرم معتبر است")
            try:
                with transaction.atomic():
                    # ذخیره پروژه با user جاری
                    project = form.save(commit=False)
                    project.user = request.user
                    
                    # **تنظیم modified_by در اینجا**
                    project.modified_by = request.user
                    
                    # دیباگ: چاپ مقادیر قبل از ذخیره
                    print(f"💾 ذخیره پروژه:")
                    print(f"   نام: {project.project_name}")
                    print(f"   کد: {project.project_code}")
                    print(f"   کشور: {project.country}")
                    print(f"   استان: {project.province}") 
                    print(f"   شهر: {project.city}")
                    print(f"   تاریخ: {project.contract_date}")
                    print(f"   سال اجرا: {project.execution_year}")
                    
                    # **ذخیره ساده بدون پارامتر user**
                    project.save()
                    
                    # ایجاد پیام موفقیت
                    messages.success(
                        request, 
                        f'پروژه "{project.project_name}" با موفقیت ایجاد شد (کد: {project.project_code})'
                    )
                    # به طور پیش‌فرض، کاربر فعلی را به عنوان پیمانکار اصلی اضافه می‌کنیم
                    ProjectUser.objects.create(
                        project=project,
                        user=request.user,
                        role='contractor',
                        is_primary=True
                    )
                    # ریدایرکت به لیست پروژه‌ها
                    return redirect('projects:project_list')
                    
            except Exception as e:
                # لاگ خطا
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating project: {str(e)}", exc_info=True)
                
                messages.error(
                    request, 
                    f'خطا در ایجاد پروژه: {str(e)}'
                )
        else:
            print("❌ فرم نامعتبر است")
            print("🔍 خطاهای فرم:", form.errors)
            
            # نمایش خطاهای فرم
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    messages.error(
                        request, 
                        f'خطا در {field_label}: {error}'
                    )
    else:
        print("📝 درخواست GET - نمایش فرم خالی")
        form = ProjectCreateForm(
            current_user=request.user,
            initial={
                'execution_year': 1404,
                'status': 'active',
                'country': 'ایران',
            }
        )
    
    context = {
        'form': form,
        'title': 'ایجاد پروژه جدید',
        'page_title': 'ایجاد پروژه جدید',
        'active_menu': 'projects',
        'province_cities_json': form.get_province_cities_json(),
        'current_user': request.user,
    }
    return render(request, 'project/project_create.html', context)
    
@login_required
def project_list(request):
    """
    View برای لیست پروژه‌های کاربر (با قابلیت ایجاد پروژه جدید)
    - بهینه‌سازی شده با استفاده از ProjectFinancialSummary
    """
    # ========== فیلتر پروژه‌های کاربر جاری (فعال فقط) ==========
    
    # اگر کاربر ادمین است، همه پروژه‌های فعال را نشان بده
    if request.user.is_superuser:
        projects = Project.objects.filter(is_active=True)
    else:
        # در غیر این صورت، پروژه‌هایی که کاربر ایجاد کرده یا در آنها نقش دارد
        project_ids = ProjectUser.objects.filter(
            user=request.user,
            is_active=True
        ).values_list('project_id', flat=True)
        
        projects = Project.objects.filter(
            Q(created_by=request.user) | Q(id__in=project_ids),
            is_active=True
        ).distinct()
    
    # مرتب‌سازی
    projects = projects.order_by('-execution_year', 'project_code')
    
    # جستجو (اختیاری)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        projects = projects.filter(
            Q(project_name__icontains=search_query) |
            Q(project_code__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(employer__icontains=search_query) |
            Q(contractor__icontains=search_query)
        )
    
    # ========== Pagination ==========
    paginator = Paginator(projects, 10)  # 10 پروژه در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ========== بهینه‌سازی آمار با ProjectFinancialSummary ==========
    pks = [project.id for project in page_obj.object_list]
    
    # دریافت خلاصه‌های مالی برای پروژه‌های این صفحه (سریع!)
    financial_summaries = {}
    if pks:
        try:
            summaries = ProjectFinancialSummary.objects.filter(
                project_id__in=pks  # Fixed: use project_id instead of pk
            ).select_related('project').values(
                'project_id',  # Fixed: use project_id
                'total_amount',
                'total_with_vat',
                'progress_percentage',
                'sessions_count',
                'approved_sessions_count',
                'total_items_count',
                'last_updated'
            )
            
            for summary in summaries:
                financial_summaries[summary['project_id']] = {
                    'total_amount': summary['total_amount'] or Decimal('0.00'),
                    'total_with_vat': summary['total_with_vat'] or Decimal('0.00'),
                    'progress_percentage': summary['progress_percentage'] or Decimal('0.00'),
                    'sessions_count': summary['sessions_count'] or 0,
                    'approved_sessions_count': summary['approved_sessions_count'] or 0,
                    'total_items_count': summary['total_items_count'] or 0,
                    'last_updated': summary['last_updated'],
                    'formatted_total_amount': format_number_int(summary['total_amount'] or 0),
                    'formatted_total_vat': format_number_int(summary['total_with_vat'] or 0),
                    'progress_percentage_display': f"{summary['progress_percentage'] or 0:.1f}%",
                }
        except Exception as e:
            # در صورت خطا، fallback به محاسبه دستی
            print(f"Error loading financial summaries: {e}")
            financial_summaries = {}
    
    # ========== آمار کلی پروژه‌ها ==========
    total_projects = page_obj.paginator.count
    
    try:
        total_contract_amount = projects.aggregate(
            total=models.Sum('contract_amount')  # Fixed: use contract_amount, not total_contract_amount
        )['total'] or Decimal('0.00')
    except Exception as e:
        print(f"Error calculating total contract amount: {e}")
        total_contract_amount = Decimal('0.00')
    
    # مجموع مبالغ متره از خلاصه‌های مالی (بهینه!)
    total_measured_amount = sum(
        summary['total_amount'] for summary in financial_summaries.values()
    ) if financial_summaries else Decimal('0.00')
    
    # مجموع مبالغ با مالیات
    total_measured_with_vat = sum(
        summary['total_with_vat'] for summary in financial_summaries.values()
    ) if financial_summaries else Decimal('0.00')
    
    # آمار کلی صورت‌جلسات
    total_sessions = sum(
        summary['sessions_count'] for summary in financial_summaries.values()
    ) if financial_summaries else 0
    
    total_approved_sessions = sum(
        summary['approved_sessions_count'] for summary in financial_summaries.values()
    ) if financial_summaries else 0
    
    total_items = sum(
        summary['total_items_count'] for summary in financial_summaries.values()
    ) if financial_summaries else 0
    
    # محاسبه درصد پیشرفت کلی
    overall_progress_percentage = Decimal('0.00')
    if total_contract_amount > 0:
        overall_progress_percentage = (total_measured_amount / total_contract_amount) * 100
    
    # ========== آمادگی داده‌ها برای Template ==========
    # اضافه کردن اطلاعات مالی به هر پروژه
    for project in page_obj.object_list:
        financial_info = financial_summaries.get(project.id, {})
        
        # اطلاعات پیش‌فرض
        project.financial_info = {
            'total_amount': financial_info.get('total_amount', Decimal('0.00')),
            'total_with_vat': financial_info.get('total_with_vat', Decimal('0.00')),
            'progress_percentage': financial_info.get('progress_percentage', Decimal('0.00')),
            'sessions_count': financial_info.get('sessions_count', 0),
            'approved_sessions_count': financial_info.get('approved_sessions_count', 0),
            'total_items_count': financial_info.get('total_items_count', 0),
            'last_updated': financial_info.get('last_updated', None),
            'formatted_total_amount': financial_info.get('formatted_total_amount', '۰'),
            'formatted_total_vat': financial_info.get('formatted_total_vat', '۰'),
            'progress_percentage_display': financial_info.get('progress_percentage_display', '۰%'),
            'has_financial_data': bool(financial_info.get('total_amount', 0) > 0),
            'progress_class': _get_progress_class(financial_info.get('progress_percentage', 0)),
        }
        
        # اطلاعات کارفرما
        project.employer_display = project.employer or 'نامشخص'
        
    context = {
        # Pagination
        'projects': page_obj,
        'search_query': search_query,
        
        # آمار کلی
        'total_projects': total_projects,
        'total_contract_amount': total_contract_amount,
        'formatted_total_contract': format_number_int(total_contract_amount),
        
        # آمار متره (از خلاصه‌های مالی)
        'total_measured_amount': total_measured_amount,
        'total_measured_with_vat': total_measured_with_vat,
        'formatted_total_measured': format_number_int(total_measured_amount),
        'formatted_total_measured_vat': format_number_int(total_measured_with_vat),
        
        # آمار صورت‌جلسات
        'total_sessions': total_sessions,
        'total_approved_sessions': total_approved_sessions,
        'total_items': total_items,
        
        # پیشرفت کلی
        'overall_progress_percentage': overall_progress_percentage,
        'formatted_overall_progress': f"{overall_progress_percentage:.1f}%",
        
        # Pagination info
        'page_obj': page_obj,
        'title': 'لیست پروژه‌ها',
        'page_title': 'مدیریت پروژه‌ها',
        'active_menu': 'projects',
        
        # آمار اضافی برای داشبورد
        'stats_summary': {
            'total_projects': total_projects,
            'total_contract': format_number_int(total_contract_amount),
            'total_measured': format_number_int(total_measured_amount),
            'total_sessions': total_sessions,
            'total_items': total_items,
            'overall_progress': f"{overall_progress_percentage:.1f}%",
        },
    }
    
    return render(request, 'project/project_list.html', context)

@login_required
def project_detail(request, pk):
    """
    View برای نمایش جزئیات کامل پروژه
    """
    try:
        # اگر کاربر ادمین است، همه پروژه‌های فعال را نشان بده
        if request.user.is_superuser:
            project = get_object_or_404(Project, pk=pk, is_active=True)
        else:
            # در غیر این صورت، پروژه‌هایی که کاربر ایجاد کرده یا در آنها نقش دارد
            project = get_object_or_404(
                Project,
                Q(created_by=request.user) | Q(project_users__user=request.user),
                pk=pk,
                is_active=True
            )
        
        if not project.has_access(request.user):
            messages.error(request, 'شما دسترسی مشاهده این پروژه را ندارید')
            return redirect('projects:project_list')
        
        # کاربران پروژه
        project_users = project.project_users.filter(is_active=True).select_related('user', 'role', 'assigned_by')
        
    except Project.DoesNotExist:
        logger.error(f"Error getting project {pk}: Project not found")
        messages.error(request, 'پروژه مورد نظر یافت نشد.')
        return redirect('projects:project_list')
    except Exception as e:
        logger.error(f"Error getting project {pk}: {e}")
        messages.error(request, 'خطا در بارگذاری پروژه.')
        return redirect('projects:project_list')
    
    # محاسبه آمار
    statistics = get_project_statistics(project)
    
    # محاسبه معیارهای مالی
    financial_metrics = calculate_financial_metrics(project)
    
    # خلاصه مالی
    financial_summary = get_financial_summary(project)
    
    # رویدادهای اخیر
    recent_events = get_recent_events(project)
    
    # هشدارها
    warnings = get_project_warnings(project, financial_metrics)
    
    # داده‌های نمودار
    chart_data = get_chart_data(project)
    
    # اطلاعات اضافی
    project_duration = calculate_project_duration(project)
    last_activity = get_last_activity(project)
    
    context = {
        # اطلاعات اصلی
        'project': project,
        'financial_metrics': financial_metrics,
        'financial_summary': financial_summary,
        'statistics': statistics,
        
        # آمار - استفاده از کلیدهای صحیح از تابع get_project_statistics
        'total_sessions': statistics.get('sessions_count', 0),
        'approved_sessions': statistics.get('approved_sessions_count', 0),
        'pending_sessions': statistics.get('pending_sessions_count', 0),
        'total_items': statistics.get('total_items_count', 0),
        'total_measured_amount': statistics.get('total_measured_amount', Decimal('0.00')),
        'formatted_total_measured': format_number_int(statistics.get('total_measured_amount', Decimal('0.00'))),
        
        'total_payments': statistics.get('payments_count', 0),
        'approved_payments': statistics.get('approved_payments_count', 0),
        'total_paid_amount': statistics.get('total_paid_amount', Decimal('0.00')),
        'formatted_total_paid': format_number_int(statistics.get('total_paid_amount', Decimal('0.00'))),
        
        'total_documents': statistics.get('total_documents', 0),
        
        # پیشرفت کلی
        'overall_progress': financial_metrics.get('progress', Decimal('0.00')),
        'formatted_progress': financial_metrics.get('progress_display', '۰%'),
        'progress_class': _get_progress_class(financial_metrics.get('progress', 0)),
        
        # نمودارها
        'chart_data': chart_data,
        
        # لیست‌های اخیر
        'recent_sessions': recent_events.get('sessions', []),
        'recent_payments': recent_events.get('payments', []),
        
        # Timeline و هشدارها
        'recent_events': recent_events,
        'warnings': warnings,
        
        # اطلاعات اضافی
        'project_duration': project_duration,
        'last_activity': last_activity,
        
        # Template variables
        'title': f'جزئیات پروژه: {project.project_name}',
        'page_title': f'پروژه {project.project_name} (کد: {project.project_code})',
        'active_menu': 'projects',
        'current_user': request.user,
        'show_sidebar': True,
    }
    
    return render(request, 'project/project_detail.html', context)

@login_required
@role_required(['contractor', 'admin'])
def project_edit(request, pk):
    """
    View برای ویرایش پروژه
    """
    # دریافت پروژه با بررسی مالکیت
    if request.user.is_superuser:
        project = get_object_or_404(Project, pk=pk, is_active=True)
    else:
        project = get_object_or_404(
            Project,
            Q(created_by=request.user) | Q(project_users__user=request.user),
            pk=pk,
            is_active=True
        )
    
    if not project.can_edit(request.user):
        messages.error(request, 'شما دسترسی ویرایش این پروژه را ندارید')
        return redirect('project:project_detail', pk=project.pk)    
    
    if request.method == 'POST':
        form = ProjectEditForm(
            request.POST, 
            request.FILES, 
            instance=project, 
            current_user=request.user,
            original_project=project
        )
        
        if form.is_valid():
            print("✅ فرم ویرایش معتبر است")
            try:
                with transaction.atomic():
                    # ذخیره تغییرات
                    updated_project = form.save(commit=False)
                    
                    # بررسی تغییرات مهم
                    changes_made = form.detect_changes(project, updated_project, form)
                    
                    # ذخیره نهایی
                    updated_project.save()
                    
                    # ایجاد پیام موفقیت
                    if changes_made:
                        messages.success(
                            request, 
                            f'پروژه "{updated_project.project_name}" با موفقیت به‌روزرسانی شد. '
                            f'{", ".join(changes_made)} تغییر یافت.'
                        )
                    else:
                        messages.info(
                            request, 
                            f'پروژه "{updated_project.project_name}" بدون تغییر ذخیره شد.'
                        )
                    
                    return redirect('projects:project_detail', pk=pk)
                        
            except Exception as e:
                messages.error(
                    request, 
                    f'خطا در به‌روزرسانی پروژه: {str(e)}'
                )
                logger.error(f"Project edit error: {str(e)}", exc_info=True)
        else:
            print("❌ فرم ویرایش نامعتبر است:", form.errors)
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else 'عمومی'
                for error in errors:
                    messages.error(request, f'خطا در {field_label}: {error}')
    else:
        print(f"📝 نمایش فرم ویرایش برای پروژه {project.pk}")
        # فرم اولیه با داده‌های پروژه
        form = ProjectEditForm(
            instance=project,
            current_user=request.user,
            original_project=project
        )
    
    context = {
        'form': form,
        'title': f'ویرایش پروژه {project.project_name}',
        'page_title': 'ویرایش پروژه',
        'active_menu': 'projects',
        'province_cities_json': form.get_province_cities_json(),
        'current_user': request.user,
        'project': project,
    }
    return render(request, 'project/project_edit.html', context)

def calculate_financial_metrics(project):
    """
    محاسبه معیارهای مالی بر اساس مدل‌های موجود
    """
    try:
        # مقداردهی اولیه
        total_paid = Decimal('0.00')
        total_billed = Decimal('0.00')
        contract_amount = getattr(project, 'total_contract_amount', Decimal('0.00'))
        remaining = contract_amount
        progress = Decimal('0.00')
        
        # محاسبه مجموع متره از صورت‌جلسات
        try:
            session_items = MeasurementSessionItem.objects.filter(
                measurement_session_number__project=project,
                measurement_session_number__is_active=True,
                is_active=True
            )
            total_billed = sum(
                item.item_total for item in session_items
            ) or Decimal('0.00')
        except Exception as e:
            logger.warning(f"Error calculating from session items: {e}")
            total_billed = Decimal('0.00')
        
        # محاسبه درصد پیشرفت
        if contract_amount and contract_amount > 0:
            progress = (total_billed / contract_amount) * 100
            progress = min(max(progress, 0), 100)
            remaining = contract_amount - total_billed
        else:
            progress = Decimal('0.00')
            remaining = contract_amount
        
        return {
            'total_paid': total_paid,
            'total_billed': total_billed,
            'remaining': remaining,
            'progress': progress,
            'contract_amount': contract_amount,
            'formatted_paid': format_number_int(total_paid),
            'formatted_billed': format_number_int(total_billed),
            'formatted_remaining': format_number_int(remaining),
            'formatted_contract_amount': format_number_int(contract_amount),
            'progress_display': f"{progress:.1f}%",
            'progress_class': get_progress_class(progress),
            'has_financial_data': total_paid > 0 or total_billed > 0,
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_financial_metrics: {e}")
        return {
            'total_paid': Decimal('0.00'),
            'total_billed': Decimal('0.00'),
            'remaining': getattr(project, 'total_contract_amount', Decimal('0.00')),
            'progress': Decimal('0.00'),
            'contract_amount': getattr(project, 'total_contract_amount', Decimal('0.00')),
            'formatted_paid': '۰',
            'formatted_billed': '۰',
            'formatted_remaining': format_number_int(getattr(project, 'total_contract_amount', Decimal('0.00'))),
            'formatted_contract_amount': format_number_int(getattr(project, 'total_contract_amount', Decimal('0.00'))),
            'progress_display': '۰%',
            'progress_class': 'bg-danger',
            'has_financial_data': False,
        }

def get_project_statistics(project):
    """
    دریافت آمار کلی پروژه بر اساس مدل‌های موجود
    """
    stats = {
        'sessions_count': 0,
        'approved_sessions_count': 0,
        'pending_sessions_count': 0,
        'total_items_count': 0,
        'unique_pricelist_items_count': 0,
        'total_measured_amount': Decimal('0.00'),
        'payments_count': 0,
        'approved_payments_count': 0,
        'total_paid_amount': Decimal('0.00'),
        'total_documents': 0,
    }
    
    try:
        # آمار صورت‌جلسات (MeasurementSession)
        sessions = MeasurementSession.objects.filter(
            project=project,
            is_active=True
        )
        
        stats['sessions_count'] = sessions.count()
        stats['approved_sessions_count'] = sessions.filter(is_approved=True).count()
        stats['pending_sessions_count'] = sessions.filter(is_approved=False).count()
        
        # آمار آیتم‌ها
        session_items = MeasurementSessionItem.objects.filter(
            measurement_session_number__project=project,
            measurement_session_number__is_active=True,
            is_active=True
        )
        
        stats['total_items_count'] = session_items.count()
        stats['unique_pricelist_items_count'] = session_items.values(
            'pricelist_item'
        ).distinct().count()
        
        # مبلغ کل متره شده
        total_amount = session_items.aggregate(
            total=models.Sum('item_total')
        )['total'] or Decimal('0.00')
        stats['total_measured_amount'] = total_amount
        
        # آمار پرداخت‌ها (اگر مدل Payment موجود)
        try:
            from .models import Payment
            payments = Payment.objects.filter(
                project=project,
                is_active=True
            )
            
            stats['payments_count'] = payments.count()
            stats['approved_payments_count'] = payments.filter(is_approved=True).count()
            
            # مبلغ کل پرداخت شده
            total_paid = payments.filter(is_approved=True).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
            stats['total_paid_amount'] = total_paid
            
        except ImportError:
            logger.info("Payment model not available")
            
    except Exception as e:
        logger.error(f"Error getting project statistics: {e}")
    
    # ایجاد کلیدهای سازگار با template (اگر نیاز باشد)
    stats['total_sessions'] = stats['sessions_count']
    stats['approved_sessions'] = stats['approved_sessions_count']
    stats['pending_sessions'] = stats['pending_sessions_count']
    stats['total_items'] = stats['total_items_count']
    
    return stats
    
def get_financial_summary(project):
    """
    دریافت خلاصه مالی از ProjectFinancialSummary
    """
    try:
        summary = ProjectFinancialSummary.objects.filter(project=project).first()
        if summary:
            return {
                'total_amount': summary.total_amount,
                'total_quantity': summary.total_quantity,
                'total_with_vat': summary.total_with_vat,
                'progress_percentage': getattr(summary, 'progress_percentage', 0),
                'sessions_count': getattr(summary, 'sessions_count', 0),
                'approved_sessions_count': getattr(summary, 'approved_sessions_count', 0),
                'last_updated': summary.last_updated,
                'formatted_amount': format_number_int(summary.total_amount),
                'formatted_quantity': format_number_int(summary.total_quantity),
                'progress_display': f"{getattr(summary, 'progress_percentage', 0):.1f}%",
            }
        return None
    except Exception as e:
        logger.warning(f"Error getting financial summary: {e}")
        return None

def get_recent_sessions(project, limit=5):
    """
    دریافت صورت‌جلسات اخیر
    """
    try:
        sessions = MeasurementSession.objects.filter(
            project=project,
            is_active=True
        ).select_related(
            'created_by',
            'discipline_choice'
        ).order_by('-session_date', '-created_at')[:limit]
        
        return [
            {
                'id': session.id,
                'session_number': session.session_number,
                'session_date': session.session_date,
                'session_date_jalali': getattr(session, 'session_date_jalali', str(session.session_date)),
                'discipline': session.get_discipline_choice_display(),
                'total_amount': sum(item.item_total for item in session.items.filter(is_active=True)) or Decimal('0.00'),
                'items_count': session.items.filter(is_active=True).count(),
                'is_approved': getattr(session, 'is_approved', False),
                'created_by': getattr(session.created_by, 'username', 'نامشخص'),
                'formatted_amount': format_number_int(
                    sum(item.item_total for item in session.items.filter(is_active=True))
                ),
            }
            for session in sessions
        ]
    except Exception as e:
        logger.error(f"Error getting recent sessions: {e}")
        return []

def get_recent_payments(project, limit=5):
    """
    دریافت پرداخت‌های اخیر (اگر مدل موجود)
    """
    payments = []
    try:
        from .models import Payment
        db_payments = Payment.objects.filter(
            project=project,
            is_active=True,
            is_approved=True
        ).select_related('created_by').order_by('-payment_date', '-created_at')[:limit]
        
        payments = [
            {
                'id': payment.id,
                'payment_number': getattr(payment, 'payment_number', f'P{payment.id}'),
                'payment_date': payment.payment_date,
                'amount': payment.amount,
                'description': getattr(payment, 'description', ''),
                'created_by': getattr(payment.created_by, 'username', 'نامشخص'),
                'formatted_amount': format_number_int(payment.amount),
            }
            for payment in db_payments
        ]
    except ImportError:
        logger.info("Payment model not available")
    except Exception as e:
        logger.warning(f"Error getting recent payments: {e}")
    
    return payments

def get_sessions_pagination(request, project):
    """
    Pagination برای صورت‌جلسات
    """
    try:
        all_sessions = MeasurementSession.objects.filter(
            project=project,
            is_active=True
        ).select_related('created_by').order_by('-session_date')
        
        paginator = Paginator(all_sessions, 10)
        page_number = request.GET.get('sessions_page', 1)
        page_obj = paginator.get_page(page_number)
        
        # اضافه کردن اطلاعات اضافی به هر session
        for session in page_obj:
            session.total_amount = sum(
                item.item_total for item in session.items.filter(is_active=True)
            ) or Decimal('0.00')
            session.formatted_amount = format_number_int(session.total_amount)
            session.items_count = session.items.filter(is_active=True).count()
        
        return page_obj
    except Exception as e:
        logger.error(f"Error in sessions pagination: {e}")
        return None

def get_payments_pagination(request, project):
    """
    Pagination برای پرداخت‌ها
    """
    try:
        from .models import Payment
        all_payments = Payment.objects.filter(
            project=project,
            is_active=True
        ).order_by('-payment_date')
        
        paginator = Paginator(all_payments, 10)
        page_number = request.GET.get('payments_page', 1)
        page_obj = paginator.get_page(page_number)
        
        # فرمت کردن مبالغ
        for payment in page_obj:
            payment.formatted_amount = format_number_int(payment.amount)
        
        return page_obj
    except ImportError:
        return None
    except Exception as e:
        logger.error(f"Error in payments pagination: {e}")
        return None

def get_chart_data(project):
    """
    داده‌های نمودار بر اساس MeasurementSession
    """
    try:
        from datetime import date
        import calendar
        
        months_data = []
        end_date = timezone.now().date()
        
        # 12 ماه گذشته
        for i in range(12, 0, -1):
            # محاسبه ماه
            year_month = end_date.replace(day=1) - timedelta(days=30*i)
            month_start = year_month.replace(day=1)
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)
            
            # صورت‌جلسات ماهانه
            monthly_sessions = MeasurementSession.objects.filter(
                project=project,
                session_date__range=[month_start, month_end],
                is_active=True
            )
            
            month_amount = Decimal('0.00')
            for session in monthly_sessions:
                # محاسبه مبلغ از آیتم‌ها
                session_amount = sum(
                    item.item_total for item in session.items.filter(is_active=True)
                )
                month_amount += session_amount
            
            # نام ماه به فارسی (ساده)
            month_names = ['ژانویه', 'فوریه', 'مارس', 'آوریل', 'مه', 'ژوئن',
                          'ژوئیه', 'اوت', 'سپتامبر', 'اکتبر', 'نوامبر', 'دسامبر']
            month_name = f"{month_names[month_start.month-1]} {month_start.year}"
            
            months_data.append({
                'month': month_name,
                'sessions_amount': float(month_amount),
                'payments_amount': 0.0,  # فعلاً صفر - نیاز به مدل Payment
                'formatted_sessions': format_number_int(month_amount),
                'formatted_payments': '۰',
                'session_count': monthly_sessions.count(),
            })
        
        return months_data[::-1]  # معکوس کردن
        
    except Exception as e:
        logger.error(f"Error generating chart data: {e}")
        return []

def get_recent_events(project, limit=10):
    """
    دریافت رویدادهای اخیر برای نمایش در sidebar
    """
    events = {
        'sessions': [],
        'payments': [],
        'activities': []
    }
    
    try:
        # صورت‌جلسات اخیر
        recent_sessions = MeasurementSession.objects.filter(
            project=project,
            is_active=True
        ).select_related('created_by').order_by('-session_date')[:5]
        
        for session in recent_sessions:
            session_info = {
                'id': session.id,
                'session_number': session.session_number,
                'session_date': session.session_date,
                'discipline': session.get_discipline_choice_display(),
                'total_amount': sum(item.item_total for item in session.items.filter(is_active=True)) or Decimal('0.00'),
                'items_count': session.items.filter(is_active=True).count(),
                'is_approved': getattr(session, 'is_approved', False),
                'created_by': getattr(session.created_by, 'username', 'نامشخص'),
            }
            events['sessions'].append(session_info)
        
        # پرداخت‌های اخیر
        try:
            from .models import Payment
            recent_payments = Payment.objects.filter(
                project=project,
                is_active=True
            ).order_by('-payment_date')[:5]
            
            for payment in recent_payments:
                payment_info = {
                    'id': payment.id,
                    'payment_date': payment.payment_date,
                    'amount': payment.amount,
                    'description': getattr(payment, 'description', ''),
                    'is_approved': getattr(payment, 'is_approved', False),
                }
                events['payments'].append(payment_info)
                
        except ImportError:
            pass
            
        # فعالیت‌های ترکیبی برای timeline
        activities = []
        
        # اضافه کردن صورت‌جلسات به فعالیت‌ها
        for session in recent_sessions:
            activities.append({
                'type': 'session',
                'date': session.session_date,
                'description': f'صورت‌جلسه #{session.session_number} ثبت شد',
                'icon': 'fas fa-file-contract',
                'color': 'success' if session.is_approved else 'warning'
            })
        
        # اضافه کردن پرداخت‌ها به فعالیت‌ها
        try:
            from .models import Payment
            for payment in recent_payments:
                activities.append({
                    'type': 'payment',
                    'date': payment.payment_date,
                    'description': f'پرداخت {format_number_int(payment.amount)} ریال ثبت شد',
                    'icon': 'fas fa-money-bill-wave',
                    'color': 'info'
                })
        except:
            pass
            
        # مرتب‌سازی بر اساس تاریخ
        activities.sort(key=lambda x: x['date'], reverse=True)
        events['activities'] = activities[:limit]
        
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
    
    return events
    
def get_project_warnings(project, financial_metrics):
    """
    دریافت هشدارهای پروژه
    """
    warnings = []
    
    try:
        progress = financial_metrics['progress']
        contract_amount = project.contract_amount or Decimal('0.00')
        total_billed = financial_metrics['total_billed']
        
        # 1. پیشرفت بیش از 100%
        if progress > 100:
            warnings.append({
                'type': 'danger',
                'title': '⚠️ پیشرفت بیش از حد',
                'message': f'درصد پیشرفت ({progress:.1f}%) از مبلغ قرارداد فراتر رفته است',
                'icon': 'fas fa-exclamation-triangle',
                'priority': 'high'
            })
        
        # 2. عدم تطابق متره و پرداخت
        elif abs(total_billed - financial_metrics['total_paid']) > contract_amount * 0.1:
            discrepancy = abs(total_billed - financial_metrics['total_paid'])
            warnings.append({
                'type': 'warning',
                'title': '⚠️ عدم تطابق مالی',
                'message': f'تفاوت {format_number_int(discrepancy)} ریال بین متره و پرداخت وجود دارد',
                'icon': 'fas fa-balance-scale',
                'priority': 'medium'
            })
        
        # 3. صورت‌جلسات تأیید نشده
        pending_sessions = MeasurementSession.objects.filter(
            project=project,
            is_active=True,
            is_approved=False
        ).count()
        
        if pending_sessions > 0:
            warnings.append({
                'type': 'info',
                'title': 'ℹ️ صورت‌جلسات در انتظار',
                'message': f'{pending_sessions} صورت‌جلسه منتظر تأیید است',
                'icon': 'fas fa-hourglass-half',
                'priority': 'low'
            })
        
        # 4. پیشرفت پایین با وجود صورت‌جلسات
        total_sessions = MeasurementSession.objects.filter(
            project=project, is_active=True
        ).count()
        
        if progress < 20 and total_sessions > 2:
            warnings.append({
                'type': 'warning',
                'title': '⚠️ پیشرفت کند',
                'message': f'با وجود {total_sessions} صورت‌جلسه، پیشرفت تنها {progress:.1f}% است',
                'icon': 'fas fa-turtle',
                'priority': 'medium'
            })
        
        # 5. عدم به‌روزرسانی خلاصه مالی
        try:
            summary = ProjectFinancialSummary.objects.filter(project=project).first()
            if summary and summary.last_updated:
                days_since_update = (timezone.now().date() - summary.last_updated.date()).days
                if days_since_update > 30:
                    warnings.append({
                        'type': 'info',
                        'title': 'ℹ️ خلاصه مالی قدیمی',
                        'message': f'آخرین به‌روزرسانی خلاصه مالی {days_since_update} روز پیش بوده است',
                        'icon': 'fas fa-calendar-times',
                        'priority': 'low'
                    })
        except:
            pass
        
        return warnings
        
    except Exception as e:
        logger.error(f"Error getting project warnings: {e}")
        return []

def calculate_project_duration(project):
    """
    محاسبه مدت زمان پروژه
    """
    try:
        # بررسی فیلدهای تاریخ در مدل Project
        start_date = getattr(project, 'start_date', None)
        end_date = getattr(project, 'end_date', None)
        execution_year = getattr(project, 'execution_year', None)
        
        if start_date and end_date:
            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                except:
                    start_date = None
            
            if isinstance(end_date, str):
                try:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except:
                    end_date = None
            
            if start_date and end_date:
                duration = end_date - start_date
                total_days = duration.days
                
                years = total_days // 365
                months = (total_days % 365) // 30
                days = total_days % 30
                
                if years > 0:
                    duration_text = f"{years} سال و {months} ماه"
                elif months > 0:
                    duration_text = f"{months} ماه و {days} روز"
                else:
                    duration_text = f"{days} روز"
                
                return {
                    'total_days': total_days,
                    'years': years,
                    'months': months,
                    'days': days,
                    'text': duration_text,
                    'is_completed': end_date <= timezone.now().date(),
                    'start_date': start_date,
                    'end_date': end_date,
                }
        
        # Fallback: بر اساس execution_year
        elif execution_year:
            current_year = timezone.now().year
            duration_years = current_year - execution_year + 1
            return {
                'total_days': 0,
                'years': duration_years,
                'months': 0,
                'days': 0,
                'text': f"{duration_years} سال",
                'is_completed': False,
                'start_date': None,
                'end_date': None,
            }
        
        return {
            'total_days': 0,
            'years': 0,
            'months': 0,
            'days': 0,
            'text': 'مدت زمان مشخص نشده',
            'is_completed': False,
            'start_date': None,
            'end_date': None,
        }
        
    except Exception as e:
        logger.error(f"Error calculating project duration: {e}")
        return {
            'total_days': 0,
            'text': 'خطا در محاسبه',
            'is_completed': False,
        }

def get_last_activity(project):
    """
    دریافت آخرین فعالیت پروژه
    """
    try:
        last_activity = None
        activity_type = None
        
        # آخرین صورت‌جلسه
        try:
            last_session = MeasurementSession.objects.filter(
                project=project,
                is_active=True
            ).aggregate(last=Max('updated_at'))['last']
            
            if last_session:
                last_activity = last_session
                activity_type = 'session'
        except Exception as e:
            logger.warning(f"Error getting last session: {e}")
        
        # آخرین به‌روزرسانی خلاصه مالی
        try:
            last_summary = ProjectFinancialSummary.objects.filter(
                project=project
            ).aggregate(last=Max('last_updated'))['last']
            
            if last_summary and (not last_activity or last_summary > last_activity):
                last_activity = last_summary
                activity_type = 'financial'
        except Exception as e:
            logger.warning(f"Error getting last financial update: {e}")
        
        # فرمت نمایش
        if last_activity:
            # تبدیل به جلالی (اگر jdatetime موجود)
            try:
                from jdatetime import datetime as jdatetime
                if isinstance(last_activity, datetime):
                    jalali_date = jdatetime.fromgregorian(datetime=last_activity)
                    return jalali_date.strftime('%Y/%m/%d %H:%M')
                else:
                    return last_activity.strftime('%Y/%m/%d %H:%M')
            except ImportError:
                return last_activity.strftime('%Y/%m/%d %H:%M')
        else:
            return 'فعالیتی ثبت نشده'
            
    except Exception as e:
        logger.error(f"Error getting last activity: {e}")
        return 'نامشخص'

@login_required
@project_access_required(['contractor', 'admin'])
def project_users_manage(request, pk):
    """
    مدیریت کاربران پروژه - فقط پیمانکار و ادمین
    """
    project = get_object_or_404(Project, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = ProjectUserAssignmentForm(request.POST, project=project, current_user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'کاربر با موفقیت به پروژه اضافه شد.')
                return redirect('project:project_users_manage', pk=project.pk)
            except Exception as e:
                messages.error(request, f'خطا در اضافه کردن کاربر: {str(e)}')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید')
    else:
        form = ProjectUserAssignmentForm(project=project, current_user=request.user)
    
    # کاربران پروژه
    project_users = project.project_users.filter(is_active=True).select_related('user', 'role', 'assigned_by')
    
    context = {
        'title': f'مدیریت کاربران - {project.project_name}',
        'project': project,
        'form': form,
        'project_users': project_users,
    }
    return render(request, 'project/project_users_manage.html', context)

@login_required
@project_access_required(['contractor', 'admin'])
def project_user_remove(request, project_pk, user_pk):
    """
    حذف کاربر از پروژه - فقط پیمانکار و ادمین
    """
    project = get_object_or_404(Project, pk=project_pk, is_active=True)
    project_user = get_object_or_404(ProjectUser, pk=user_pk, project=project, is_active=True)
    
    if request.method == 'POST':
        try:
            project_user.is_active = False
            project_user.save()
            messages.success(request, 'کاربر از پروژه حذف شد.')
        except Exception as e:
            messages.error(request, f'خطا در حذف کاربر: {str(e)}')
    
    return redirect('project:project_users_manage', pk=project.pk)

@login_required
@role_required(['contractor', 'admin'])
def user_create(request):
    """
    ایجاد کاربر جدید توسط پیمانکار یا ادمین
    """
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    
                    messages.success(request, f'کاربر {user.username} با موفقیت ایجاد شد.')
                    return redirect('project:user_list')
                    
            except Exception as e:
                messages.error(request, f'خطا در ایجاد کاربر: {str(e)}')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید')
    else:
        form = UserCreateForm()
    
    context = {
        'title': 'ایجاد کاربر جدید',
        'form': form,
    }
    return render(request, 'project/user_form.html', context)

@login_required
@role_required(['contractor', 'admin'])
def user_list(request):
    """
    لیست کاربران ایجاد شده توسط کاربر جاری
    """
    # کاربرانی که توسط کاربر جاری ایجاد شده‌اند
    users = User.objects.filter(
        profile__is_verified=True
    ).select_related('profile').order_by('-date_joined')
    
    context = {
        'title': 'لیست کاربران',
        'users': users,
    }
    return render(request, 'project/user_list.html', context)

@login_required
def detect_changes(original_project, updated_project, form):
    """
    تشخیص تغییرات انجام شده در پروژه
    """
    changes = []
    original_data = {
        'project_name': original_project.project_name,
        'project_code': original_project.project_code,
        'execution_year': str(original_project.execution_year),
        'contract_date': original_project.contract_date,
        'total_contract_amount': original_project.total_contract_amount,
        'status': original_project.status,
        'is_active': original_project.is_active,
    }
    
    updated_data = {
        'project_name': updated_project.project_name,
        'project_code': updated_project.project_code,
        'execution_year': str(updated_project.execution_year),
        'contract_date': updated_project.contract_date,
        'total_contract_amount': updated_project.total_contract_amount,
        'status': updated_project.status,
        'is_active': updated_project.is_active,
    }
    
    change_labels = {
        'project_name': 'نام پروژه',
        'project_code': 'کد پروژه',
        'execution_year': 'سال اجرا',
        'contract_date': 'تاریخ قرارداد',
        'total_contract_amount': 'مبلغ قرارداد',
        'status': 'وضعیت',
        'is_active': 'وضعیت فعال',
    }
    
    for field, label in change_labels.items():
        if original_data.get(field) != updated_data.get(field):
            changes.append(f'"{label}"')
    
    # بررسی user
    if form.cleaned_data.get('user') and form.cleaned_data['user'] != original_project.user:
        changes.append('"کارفرما"')
    
    # بررسی description
    if original_project.description != updated_project.description:
        changes.append('"توضیحات"')
    
    return changes if changes else []

@login_required
def project_toggle_status(request, pk):
    """
    تغییر وضعیت فعال/غیرفعال پروژه (AJAX)
    """
    if request.method == 'POST':
        project = get_object_or_404(
            Project, 
            pk=pk, 
            user=request.user
        )
        
        try:
            # تغییر وضعیت
            project.is_active = not project.is_active
            project.save()
            
            status_text = "فعال" if project.is_active else "غیرفعال"
            messages.success(
                request, 
                f'پروژه "{project.project_name}" با موفقیت {status_text} شد.'
            )
            
            return JsonResponse({
                'success': True,
                'status': project.is_active,
                'message': f'پروژه {status_text} شد',
                'status_text': status_text,
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'message': 'خطا در تغییر وضعیت پروژه',
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def project_duplicate(request, pk):
    """
    کپی کردن پروژه (Duplicate)
    """
    project = get_object_or_404(
        Project, 
        pk=pk, 
        user=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # کپی کردن پروژه
                new_project = project
                new_project.pk = None  # ایجاد رکورد جدید
                new_project.id = None
                new_project.project_code = f"{project.project_code}-COPY"
                new_project.project_name = f"کپی از {project.project_name}"
                new_project.user = request.user
                new_project.created_at = timezone.now()
                new_project.updated_at = timezone.now()
                new_project.is_active = True
                new_project.save()
                
                # کپی کردن صورت‌جلسات مرتبط (اختیاری)
                # sessions = MeasurementSession.objects.filter(project=project)
                # for session in sessions:
                #     new_session = session
                #     new_session.pk = None
                #     new_session.project = new_project
                #     new_session.save()
                
                messages.success(
                    request, 
                    f'پروژه "{new_project.project_name}" با موفقیت کپی شد (کد: {new_project.project_code})'
                )
                
                return redirect('projects:project_edit', pk=new_project.id)
                
        except Exception as e:
            messages.error(
                request, 
                f'خطا در کپی پروژه: {str(e)}'
            )
    
    context = {
        'project': project,
        'title': f'کپی پروژه: {project.project_name}',
        'page_title': f'کپی {project.project_name}',
        'active_menu': 'projects',
    }
    return render(request, 'projects/project_duplicate.html', context)

@login_required
@role_required(['contractor', 'admin'])
def project_access_management(request, pk):
    """
    مدیریت دسترسی‌های پروژه
    """
    project = get_object_or_404(Project, pk=pk, is_active=True)
    
    if not project.can_edit(request.user):
        messages.error(request, 'شما دسترسی مدیریت این پروژه را ندارید')
        return redirect('project:project_detail', pk=pk)
    
    invitation_form = UserInvitationForm()
    access_form = ProjectAccessForm(project=project, current_user=request.user)
    
    if request.method == 'POST':
        if 'invite_user' in request.POST:
            invitation_form = UserInvitationForm(request.POST)
            if invitation_form.is_valid():
                try:
                    # ایجاد توکن و ارسال ایمیل
                    token = secrets.token_urlsafe(32)
                    expiration = timezone.now() + timedelta(days=7)
                    
                    invitation = invitation_form.save(commit=False)
                    invitation.project = project
                    invitation.invited_by = request.user
                    invitation.token = token
                    invitation.expires_at = expiration
                    invitation.save()
                    
                    # ارسال ایمیل دعوت (اینجا می‌توانید سرویس ایمیل خود را اضافه کنید)
                    send_invitation_email(invitation)
                    
                    messages.success(request, f'دعوت‌نامه برای {invitation.email} ارسال شد')
                    return redirect('project:project_access_management', pk=pk)
                    
                except Exception as e:
                    messages.error(request, f'خطا در ارسال دعوت‌نامه: {str(e)}')
        
        elif 'manage_access' in request.POST:
            access_form = ProjectAccessForm(request.POST, project=project, current_user=request.user)
            if access_form.is_valid():
                try:
                    with transaction.atomic():
                        # به‌روزرسانی نقش‌ها
                        project_users = ProjectUser.objects.filter(project=project)
                        for pu in project_users:
                            new_role = access_form.cleaned_data.get(f'user_{pu.id}_role')
                            remove_user = access_form.cleaned_data.get(f'user_{pu.id}_remove', False)
                            
                            if remove_user:
                                pu.delete()
                                messages.info(request, f'کاربر {pu.user.get_full_name()} حذف شد')
                            elif new_role and new_role != pu.role:
                                pu.role = new_role
                                pu.save()
                                messages.info(request, f'نقش {pu.user.get_full_name()} به‌روزرسانی شد')
                    
                    messages.success(request, 'تغییرات با موفقیت ذخیره شد')
                    return redirect('project:project_access_management', pk=pk)
                    
                except Exception as e:
                    messages.error(request, f'خطا در ذخیره تغییرات: {str(e)}')
    
    # دریافت کاربران پروژه و دعوت‌نامه‌ها
    project_users = ProjectUser.objects.filter(project=project).select_related('user')
    invitations = UserInvitation.objects.filter(project=project)
    
    context = {
        'project': project,
        'invitation_form': invitation_form,
        'access_form': access_form,
        'project_users': project_users,
        'invitations': invitations,
        'title': f'مدیریت دسترسی‌های {project.project_name}',
        'page_title': 'مدیریت دسترسی‌ها',
    }
    
    return render(request, 'project/project_access_management.html', context)

def send_invitation_email(invitation):
    """
    تابع برای ارسال ایمیل دعوت
    (این تابع را با سرویس ایمیل خود پر کنید)
    """
    try:
        subject = f'دعوت به همکاری در پروژه {invitation.project.project_name}'
        message = f"""
        سلام
        
        شما برای همکاری در پروژه "{invitation.project.project_name}" دعوت شده‌اید.
        نقش شما در این پروژه: {invitation.get_role_display()}
        
        برای ثبت‌نام و پذیرش دعوت، روی لینک زیر کلیک کنید:
        http://127.0.0.1:8000/accounts/accept-invitation/{invitation.token}/
        
        این لینک تا {invitation.expires_at.strftime('%Y/%m/%d')} معتبر است.
        """
        
        # در اینجا کد ارسال ایمیل را قرار دهید
        # send_mail(subject, message, 'noreply@testmetre.com', [invitation.email])
        print(f"📧 ایمیل دعوت ارسال شد به: {invitation.email}")
        
    except Exception as e:
        print(f"❌ خطا در ارسال ایمیل: {e}")


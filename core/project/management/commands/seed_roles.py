# project/management/commands/seed_roles.py
from django.core.management.base import BaseCommand
from project.models import ProjectRole

class Command(BaseCommand):
    help = 'ایجاد نقش‌های پیش‌فرض سیستم'

    def handle(self, *args, **options):
        roles_data = [
            {
                'name': 'contractor',
                'description': 'پیمانکار اصلی پروژه',
                'can_edit_measurements': True,
                'can_approve': False,
                'can_view_financial': True,
            },
            {
                'name': 'project_manager',
                'description': 'مدیر طرح پروژه',
                'can_edit_measurements': True,
                'can_approve': True,
                'can_view_financial': True,
            },
            {
                'name': 'employer',
                'description': 'کارفرمای پروژه',
                'can_edit_measurements': True,
                'can_approve': True,
                'can_view_financial': True,
            },
            {
                'name': 'supervisor',
                'description': 'ناظر پروژه',
                'can_edit_measurements': True,
                'can_approve': False,
                'can_view_financial': False,
            },
            {
                'name': 'consultant',
                'description': 'مشاور پروژه',
                'can_edit_measurements': False,
                'can_approve': False,
                'can_view_financial': False,
            },
            {
                'name': 'engineer',
                'description': 'مهندس پروژه',
                'can_edit_measurements': False,
                'can_approve': False,
                'can_view_financial': False,
            },
        ]

        for role_data in roles_data:
            role, created = ProjectRole.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'نقش {role.get_name_display()} ایجاد شد')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'نقش {role.get_name_display()} از قبل وجود دارد')
                )
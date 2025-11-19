# sooratvaziat/mixins.py
from django.core.exceptions import PermissionDenied

class UserProjectMixin:
    def dispatch(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id')
        if project_id:
            project = get_object_or_404(Project, id=project_id)
            if project.user != request.user:
                raise PermissionDenied("شما دسترسی به این پروژه را ندارید.")
        return super().dispatch(request, *args, **kwargs)
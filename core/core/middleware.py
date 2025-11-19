"""
Middleware to track current user for audit logging
"""

from django.utils.deprecation import MiddlewareMixin
from threading import local
from django.contrib.auth.models import AnonymousUser

_thread_locals = local()

def get_current_user():
    """Get current user from thread local"""
    try:
        return getattr(_thread_locals, 'user', AnonymousUser())
    except AttributeError:
        return AnonymousUser()

def get_current_request():
    """Get current request from thread local"""
    try:
        return getattr(_thread_locals, 'request', None)
    except AttributeError:
        return None

class CurrentUserMiddleware(MiddlewareMixin):
    """
    Middleware to store current user and request in thread local storage
    """
    
    def process_request(self, request):
        _thread_locals.user = request.user
        _thread_locals.request = request
        return None
    
    def process_exception(self, request, exception):
        # Clean up on exception
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
        if hasattr(_thread_locals, 'request'):
            delattr(_thread_locals, 'request')
        return None
    
    def process_response(self, request, response):
        # Clean up after response
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
        if hasattr(_thread_locals, 'request'):
            delattr(_thread_locals, 'request')
        return response

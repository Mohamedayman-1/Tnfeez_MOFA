"""
URL configuration for budget_transfer project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView


# Create a view that can serve any template from the templates directory
def serve_template(request, template_name):
    return TemplateView.as_view(template_name=f"{template_name}.html")(request)


urlpatterns = [
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    path("admin/", admin.site.urls),
    # Update to use the new apps' URLs instead of budget_app
    path("api/auth/", include("user_management.urls")),
    path("api/budget/", include("budget_management.urls")),
    path("api/transfers/", include("transaction.urls")),
    path("api/accounts-entities/", include("account_and_entitys.urls")),  # Add the new app's URLs
    path("api/admin_panel/", include("Admin_Panel.urls")),  # Add the new app's URLs
    path("api/approvals/", include("approvals.urls")),  # Add the new app's URLs
    path("api/chat/", include("Chatting.urls")),  # Add the new app's URLs
    path("api/validations/", include("django_dynamic_validation.urls")),
    # path("api/Invoice/", include("Invoice.urls")),  # Add the new app's URLs
    # path("api/Ai/", include("AI.urls")),  # Disabled - AI app not in use


]

# WebSocket routing moved to __NOTIFICATIONS_SETUP__/code/routing.py
# Import from there in asgi.py instead

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

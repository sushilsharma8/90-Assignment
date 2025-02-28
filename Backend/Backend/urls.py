from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI schema view
schema_view = get_schema_view(
    openapi.Info(
        title="My Project API",
        default_version="v1",
        description="API documentation for my Django 90 North Assignment project.",
        # terms_of_service="https://www.yoursite.com/terms/",
        contact=openapi.Contact(email="sushilsharma8oct2001@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),  # Include core app API routes

    # API documentation routes
    re_path(r"^$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),  # Root URL -> Swagger UI
    re_path(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),  # Redoc UI
    re_path(r"^swagger.json$", schema_view.without_ui(cache_timeout=0), name="schema-json"),  # JSON schema
]

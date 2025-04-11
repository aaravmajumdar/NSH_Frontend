"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.urls import include # Import the include function to include other URL configurations
from . import views 
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="index"), 
    path("item-search/", views.search, name="search"), 
    path('api/search/', views.api_search, name='api_search'),
    path('api/placement/', views.api_placement, name='api_placement'),
    path("item-rearrange/", views.rearrange, name="rearrange"), 
    path("login", views.login_form, name="login"), 
    path("logout", views.logout_view, name="logout"), 
    path("simulate-time", views.simulation, name="simulation"), 
    path("waste-management", views.waste_management, name="waste_management"), 
    path("placement", views.placement, name="placement"), 
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

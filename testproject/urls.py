
from django.contrib import admin
from django.urls import path, include
from testApp.views import internal_user_count

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('testApp.urls')),
    path('api/internal/user-count/', internal_user_count),
]

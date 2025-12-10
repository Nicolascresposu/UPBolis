from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),   # Admin nativo de Django
    path('', include('web.urls')),     # Rutas de tu app "web"
]

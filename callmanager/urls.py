"""
Корневой URL-конфиг проекта callmanager.
Подключает админку Django, все маршруты приложения core и аутентификацию.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Админка Django (все URL, начинающиеся с /admin/...)
    path('admin/', admin.site.urls),

    # Все маршруты нашего приложения core (главная страница, API, справочник и т.д.)
    path('', include('core.urls')),

    # Вход и выход из системы
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# Раздача статических и медиа-файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
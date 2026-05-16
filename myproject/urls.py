from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.conf import settings
from django.views.static import serve
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='welcome.html'), name='home'),
    path('admin/', admin.site.urls),
    path('auth/',include('authapp.urls')),
    path('provider/', include('serviceproviderapp.urls')),
    path('receiver/', include('servicereceiverapp.urls')),
    path('offer/', include('quoteapp.urls')),
    path('message/', include('messageapp.urls')),
    path('notification/', include('notificationapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

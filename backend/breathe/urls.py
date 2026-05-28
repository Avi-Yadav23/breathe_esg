from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('ingestion.urls')),
    path('auth/login/', obtain_auth_token),
    path('auth/me/', me),
]
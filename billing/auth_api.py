from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


def _user_payload(user):
    return {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name or '',
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def api_csrf(request):
    return Response({'detail': 'ok'})


@api_view(['POST'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def api_login(request):
    username = str(request.data.get('username') or '').strip()
    password = str(request.data.get('password') or '')
    if not username or not password:
        return Response({'error': 'Enter username and password.'}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'error': 'Invalid username or password.'}, status=400)
    if not user.is_active:
        return Response({'error': 'This account is disabled.'}, status=400)
    login(request, user)
    return Response(_user_payload(user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    logout(request)
    return Response({'detail': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_me(request):
    return Response(_user_payload(request.user))

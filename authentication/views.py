from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from customer.models import Customer, CustomerMobile
import re


@api_view(['POST'])
@permission_classes([AllowAny])
def token_view(request):
    """
    Custom token endpoint that handles both login and registration.
    
    Expected payload:
    {
        "username": "user@example.com",
        "password": "password123",
        "name": "John Doe",  # Required for new users
        "email": "user@example.com"  # Required for new users
    }
    """
    username = request.data.get('username')
    password = request.data.get('password')
    name = request.data.get('name')
    email = request.data.get('email')
    
    # Validate required fields
    if not username or not password:
        return Response({
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user exists
    try:
        user = User.objects.get(username=username)
        # User exists - attempt login
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'message': 'Login successful'
        })
        
    except User.DoesNotExist:
        # User doesn't exist - create new user
        # if not name or not email:
        #     return Response({
        #         'error': 'Name and email are required for new user registration'
        #     }, status=status.HTTP_400_BAD_REQUEST)
        
        # # Validate email format
        # email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        # if not re.match(email_pattern, email):
        #     return Response({
        #         'error': 'Invalid email format'
        #     }, status=status.HTTP_400_BAD_REQUEST)
        
        # # Check if email is already taken
        # if User.objects.filter(email=email).exists():
        #     return Response({
        #         'error': 'Email is already registered'
        #     }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                from customer.models import CustomerMobile
                user = User.objects.create_user(
                    username=username,
                    email=email or '',
                    password=password,
                    first_name=name.split()[0] if name else '',
                    last_name=' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''
                )
                
                customer = Customer.objects.create(
                    user=user,
                    name=name or username,
                    email=email or f'{username}@kushnath.local',
                )
                mobile_digits = re.sub(r'\D', '', username)
                if len(mobile_digits) > 10:
                    mobile_digits = mobile_digits[-10:]
                CustomerMobile.objects.get_or_create(customer=customer, mobile=mobile_digits or username)
                
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    },
                    'message': 'User registered successfully'
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({
                'error': f'Registration failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
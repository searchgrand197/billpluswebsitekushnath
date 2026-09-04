from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Customer
from .serializers import CustomerSerializer, CustomerUpdateSerializer

# Create your views here.

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_customer_data(request):
    """
    Get customer data for the authenticated user
    """
    try:
        customer = get_object_or_404(Customer, user=request.user)
        serializer = CustomerSerializer(customer)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Customer.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Customer profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_customer_data(request):
    """
    Update customer data for the authenticated user
    """
    try:
        customer = get_object_or_404(Customer, user=request.user)
        serializer = CustomerUpdateSerializer(customer, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            # Return updated data
            updated_serializer = CustomerSerializer(customer)
            return Response({
                'success': True,
                'message': 'Customer data updated successfully',
                'data': updated_serializer.data
            })
        else:
            return Response({
                'success': False,
                'message': 'Validation error',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Customer.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Customer profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

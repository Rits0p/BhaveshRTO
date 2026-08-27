from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from common.permissions import IsTheOneAdmin
from common.throttles import LoginRateThrottle

from .models import Admin
from .serializers import AdminSerializer, LoginSerializer, SignupSerializer


class AdminExistsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'exists': Admin.objects.exists_already()})


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if Admin.objects.exists_already():
            return Response(
                {'success': False, 'message': 'An admin account already exists. Signup is permanently disabled.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin = Admin.objects.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            name=serializer.validated_data['name'],
        )
        return Response(
            {'success': True, 'message': 'Admin account created. Please log in.', 'adminId': str(admin.id)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        admin = authenticate(request=request, username=email, password=password)
        if not admin or not getattr(admin, 'is_active', False):
            return Response({'success': False, 'message': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not admin.is_verified:
            admin.is_verified = True
            admin.save(update_fields=['is_verified'])

        refresh = RefreshToken.for_user(admin)
        return Response({
            'success': True,
            'message': 'Login successful.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'token': str(refresh.access_token),
            'user': AdminSerializer(admin).data,
        })


class MeView(APIView):
    permission_classes = [IsTheOneAdmin]

    def get(self, request):
        return Response({'success': True, 'admin': AdminSerializer(request.user).data})

# users/views.py
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .serializers import ChangePasswordSerializer, UserSerializer, CustomTokenObtainPairSerializer
from .models import User
from .permissions import IsAdmin


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    request.user.set_password(serializer.validated_data["new_password"])
    request.user.save()
    return Response({"status": "password updated"}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


def _set_auth_cookies(response, access, refresh):
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS,
        str(access),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        settings.AUTH_COOKIE_REFRESH,
        str(refresh),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",  # Match path="/" with access cookie
    )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data["access"]
        refresh = serializer.validated_data["refresh"]

        response = Response({"detail": "logged in"}, status=status.HTTP_200_OK)
        _set_auth_cookies(response, access, refresh)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if refresh_token is None:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            response = Response({"detail": "Refresh token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
            response.delete_cookie(settings.AUTH_COOKIE_ACCESS, path="/")
            response.delete_cookie(settings.AUTH_COOKIE_REFRESH, path="/")
            return response

        access = serializer.validated_data["access"]
        new_refresh = serializer.validated_data.get("refresh", refresh_token)

        response = Response({"detail": "refreshed"}, status=status.HTTP_200_OK)
        _set_auth_cookies(response, access, new_refresh)
        return response


# users/views.py

@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response({"detail": "logged out"}, status=status.HTTP_200_OK)

        response.delete_cookie(
            settings.AUTH_COOKIE_ACCESS,
            path="/",
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        response.delete_cookie(
            settings.AUTH_COOKIE_REFRESH,
            path="/",
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )

        return response

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
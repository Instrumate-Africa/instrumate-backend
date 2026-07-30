from . import serializers
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from instrumate.settings import DEBUG


class RegistrationView(APIView):
    authentication_classes = []

    def post(self, request):
        serializer = serializers.RegistrationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "successful registration"},
                            status=status.HTTP_201_CREATED)

        return Response({"error": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    authentication_classes = []

    def gen_tokens(self, user):
        jwt_tokens = RefreshToken.for_user(user)

        return {
            'refresh_token': str(jwt_tokens),
            'access_token': str(jwt_tokens.access_token)
        }

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            tokens = self.gen_tokens(user)
            response = Response({"message": "login successful",},
                                status=status.HTTP_200_OK)
# set httponly and secure to not debug
            response.set_cookie(
                key='refresh_token',
                value=str(tokens.get('refresh_token')),
                httponly= not DEBUG,
                secure=not DEBUG,
                samesite='Lax',
                path='/auth/refresh/'
            )

            response.set_cookie(
                key='access_token',
                value=str(tokens.get('access_token')),
                httponly=not DEBUG,
                secure=not DEBUG,
                samesite='Lax',
                path='/'
            )

            return response

        return Response({"error": "invalid login"},
                        status=status.HTTP_400_BAD_REQUEST)


class RefreshTokenView(APIView):
    authentication_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        try:
            refresh_token = RefreshToken(refresh_token)
            response = Response({"message": "successful refresh",
                                 "access_token": str(refresh_token.access_token)},
                                status=status.HTTP_200_OK)

            response.set_cookie(
                key='access_token',
                value=str(refresh_token.access_token),
                httponly=not DEBUG,
                secure=not DEBUG,
                samesite='Lax',
                path='/'
            )

            response.set_cookie(
                key='refresh_token',
                value=str(refresh_token),
                httponly=not DEBUG,
                secure=not DEBUG,
                samesite='Lax',
                path='/auth/refresh/'
            )
            return response

        except TokenError as e:
            return Response({"error": str(e)},
                            status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    authentication_classes = []

    def post(self, request):
        response = Response({"message": "user logged out"},
                            status=status.HTTP_200_OK)

        response.delete_cookie('refresh_token', path='/auth/refresh/')
        response.delete_cookie('access_token', path='/')
        return response



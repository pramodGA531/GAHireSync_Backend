# from django.shortcuts import render
from rest_framework import viewsets
from .serializers import UserSerializer, LoginSerializer, JobPostingSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser,JobPostings
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication

# Create your views here.

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data = request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                role = user.role
                return Response({"token":str(token), 'role':role} , status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)
            

class SignupView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': str(token), 'role': user.role}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class User_view(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self,request , *args, **kwargs):
        user = request.user
        user_data = {
            'id' : user.id ,
            'username': user.username,
            'email' : user.email, 
            'role' : user.role
        }
        return Response(user_data , status= status.HTTP_200_OK)
    
    def patch(self,request):
        pass

            
class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        # Optionally filter or customize the queryset
        return CustomUser.objects.all()

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        # Custom logic before updating instance
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Custom logic before partially updating instance
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Custom logic before deleting instance
        return super().destroy(request, *args, **kwargs)


class JobPostingView(APIView):
    permission_classes =[IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def get(self, request):
        job_postings = JobPostings.objects.all()
        serializer = JobPostingSerializer(job_postings, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = JobPostingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(username=request.user)  # Assign the user to the `username` field
            return Response({"data":serializer.data,"username":str(request.user)}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


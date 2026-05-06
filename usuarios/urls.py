from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, UserProfileViewSet, AuthViewSet,
    CustomTokenObtainPairView, PacienteRegisterView
)

# Configurar el router para los ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='userprofile')
router.register(r'auth', AuthViewSet, basename='auth')

# URLs para autenticación JWT
jwt_urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# URLs principales
urlpatterns = [
    # Incluir las URLs del router
    path('', include(router.urls)),
    
    # Incluir las URLs de JWT
    path('', include(jwt_urlpatterns)),
    
    # Endpoint público de registro de pacientes
    path('register/', PacienteRegisterView.as_view(), name='paciente_register'),
]

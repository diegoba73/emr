from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Autenticación
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    # Perfil de usuario
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Usuario actual
    path('current/', views.current_user, name='current_user'),
    path('test-serializer/', views.test_user_serializer, name='test_user_serializer'),
    
    # Gestión de usuarios (solo administradores)
    path('admin/users/', views.AdminUserListView.as_view(), name='admin_users'),
    path('admin/users/<int:pk>/', views.AdminUserDetailView.as_view(), name='admin_user_detail'),
    
    # Listas por rol
    path('pacientes/', views.list_pacientes, name='list_pacientes'),
    path('medicos/', views.list_medicos, name='list_medicos'),
    path('secretarias/', views.list_secretarias, name='list_secretarias'),
]

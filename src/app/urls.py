from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from . import views  

def root_redirect(request):
    return redirect('login')

urlpatterns = [
    path('', root_redirect, name='root'),
    path('login/', views.login_view, name='login'),
    path('home/', views.home_view, name='home'),
    path('logout/', views.logout_view, name='logout'),
]

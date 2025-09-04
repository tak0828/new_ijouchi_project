from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

def login_view(request):
    message = ""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)  # セッションに保存
            return redirect("home")  # ログイン後に /home/ へ
        else:
            message = "ユーザー名またはパスワードが違います"

    return render(request, "app/login.html", {"message": message})

@login_required
def home_view(request):
    return render(request, "app/home.html")

@login_required
def logout_view(request):
    logout(request)
    return redirect("login")

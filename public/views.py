from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("dashboard:inicio")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("public:login")

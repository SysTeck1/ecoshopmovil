from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("dashboard:inicio")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar logo URL para login
        context["dashboard_logo_url"] = "/static/img/logo/logo.png"
        return context


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("public:login")

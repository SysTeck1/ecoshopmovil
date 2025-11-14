from django.urls import path

from .views import CustomLoginView, CustomLogoutView

app_name = "public"

urlpatterns = [
    path("", CustomLoginView.as_view(), name="login"),
    path("ingresar/", CustomLoginView.as_view(), name="login"),
    path("salir/", CustomLogoutView.as_view(), name="logout"),
]

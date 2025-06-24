from django.urls import path
from .views import SignupView, LoginView, LogoutView, CurrentUserView, CSRFTokenView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("csrf/", CSRFTokenView.as_view(), name="csrf"),
]

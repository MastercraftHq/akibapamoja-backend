from django.urls import path
from . import views

urlpatterns = [ 
    path('register/', views.CreateUserView.as_view(), name="create-user"), 
    path('login/', views.LoginView.as_view(), name="log-in"),
    path('me/', views.UpdateUserView.as_view(), name='update-user'),     
]
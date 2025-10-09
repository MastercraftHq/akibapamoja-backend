from django.urls import path
from . import views

urlpatterns = [
    path('', views.ChamaCreateView.as_view(), name='create-chama'),
    path('<int:chama_id>/', views.ChamaDetailView.as_view(), name='chama-detail'),
    path('<int:chama_id>/members/add/', views.AddMemberView.as_view(), name='add-member'),
    path('<int:chama_id>/members/list/', views.ListMembersView.as_view(), name='list-members'),
    path('join/', views.JoinChamaView.as_view(), name='join-chama'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('chamas/', views.ChamaCreateView.as_view(), name='create-chama'),
    path('chamas/<int:chama_id>/', views.ChamaDetailView.as_view(), name='chama-detail'),
    path('chamas/<int:chama_id>/members/add/', views.AddMemberView.as_view(), name='add-member'),
    path('chamas/<int:chama_id>/members/list/', views.ListMembersView.as_view(), name='list-members'),
    path('chamas/join/', views.JoinChamaView.as_view(), name='join-chama'),
]

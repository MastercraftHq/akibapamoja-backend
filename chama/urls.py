from django.urls import path
from . import views

urlpatterns = [
    path('groups/', views.ChamaCreateView.as_view(), name='create-chama'),
    path('groups/<int:pk>/', views.ChamaDetailView.as_view(), name='chama-detail'),
    path('groups/<int:groupId>/members/add/', views.AddMemberView.as_view(), name='add-member'),
    path('groups/<int:groupId>/members/list/', views.ListMembersView.as_view(), name='list-members'),
    path('groups/join/', views.JoinChamaView.as_view(), name='join-chama'),
]

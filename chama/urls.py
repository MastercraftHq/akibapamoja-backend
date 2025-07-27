
from django.urls import path
from . import views

urlpatterns = [
    path('groups/', views.ChamaCreateView.as_view(), name='create-chama'),

    
    path(
        'groups/<uuid:pk>/',
        views.ChamaDetailView.as_view(),
        name='chama-detail'
    ),

    # add / list members now expects a UUID groupId
    path(
        'groups/<uuid:groupId>/members/add/',
        views.AddMemberView.as_view(),
        name='add-member'
    ),
    path(
        'groups/<uuid:groupId>/members/list/',
        views.ListMembersView.as_view(),
        name='list-members'
    ),

    path('groups/join/', views.JoinChamaView.as_view(), name='join-chama'),
]

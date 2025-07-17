from django_filters import rest_framework as filters
from chama.models import  Chama 
from users.models import CustomUser
from .models import Contribution

class ContributionFilter(filters.FilterSet):
    chama_id = filters.ModelChoiceFilter(
        queryset=Chama.objects.all(),
        field_name='chama',
        label='Chama'
    )
    member_id = filters.ModelChoiceFilter(
        queryset=CustomUser.objects.all(),
        field_name='user',
        label='Member'
    )

    class Meta:
        model = Contribution
        fields = ['chama_id', 'member_id']
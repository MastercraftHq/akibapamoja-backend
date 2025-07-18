from django.contrib import admin
from .models import Contribution

@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'member', 'amount', 'payment_method', 'status', 'date')
    list_filter = ('group', 'payment_method', 'status', 'date')
    search_fields = ('mpesa_transaction_id', 'member__email', 'group__name')
    ordering = ('-date',)

from django.contrib import admin
from .models import ContributionSchedule, Contribution, ActivityLog, ContributionCycle

admin.site.register(ContributionSchedule)
admin.site.register(Contribution)
admin.site.register(ActivityLog)
admin.site.register(ContributionCycle)
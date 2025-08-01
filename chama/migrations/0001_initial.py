
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Chama',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('contribution_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('contribution_frequency', models.CharField(max_length=20)),
                ('contribution_day', models.IntegerField()),
                ('currency', models.CharField(max_length=10)),
                ('late_payment_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('minimum_members', models.IntegerField(default=1)),
                ('maximum_members', models.IntegerField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateField(auto_now_add=True)),
                ('updated_at', models.DateField(auto_now=True)),
                ('join_code', models.CharField(max_length=12, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('member', 'Member'), ('admin', 'Admin'), ('treasurer', 'Treasurer')], default='member', max_length=20)),
                ('status', models.CharField(choices=[('invited', 'Invited'), ('active', 'Active'), ('removed', 'Removed')], default='active', max_length=20)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('payout_order', models.IntegerField(blank=True, null=True)),
                ('chama', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='chama.chama')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'chama')},
            },
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IngestionRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('source_type', models.CharField(choices=[('sap', 'SAP Fuel & Procurement'), ('utility', 'Utility Electricity'), ('travel', 'Corporate Travel')], max_length=20)),
                ('original_filename', models.CharField(max_length=255)),
                ('file_hash', models.CharField(max_length=64)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('processing', 'Processing'), ('complete', 'Complete'), ('failed', 'Failed')], default='processing', max_length=20)),
                ('row_count_total', models.IntegerField(default=0)),
                ('row_count_ok', models.IntegerField(default=0)),
                ('row_count_flagged', models.IntegerField(default=0)),
                ('row_count_error', models.IntegerField(default=0)),
                ('error_message', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='RawRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('row_number', models.IntegerField()),
                ('raw_data', models.JSONField()),
                ('parse_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='raw_records', to='ingestion.ingestionrun')),
            ],
            options={
                'ordering': ['row_number'],
            },
        ),
        migrations.CreateModel(
            name='NormalizedRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('scope', models.IntegerField(blank=True, choices=[(1, 'Scope 1'), (2, 'Scope 2'), (3, 'Scope 3')], null=True)),
                ('source_type', models.CharField(max_length=20)),
                ('category', models.CharField(blank=True, max_length=50)),
                ('travel_subcategory', models.CharField(blank=True, choices=[('flight', 'Flight'), ('hotel', 'Hotel'), ('ground', 'Ground Transport')], max_length=20)),
                ('activity_value', models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ('activity_unit', models.CharField(blank=True, max_length=30)),
                ('activity_unit_normalized', models.CharField(blank=True, max_length=30)),
                ('activity_value_normalized', models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ('period_start', models.DateField(blank=True, null=True)),
                ('period_end', models.DateField(blank=True, null=True)),
                ('facility_name', models.CharField(blank=True, max_length=255)),
                ('plant_code', models.CharField(blank=True, max_length=50)),
                ('location_country', models.CharField(blank=True, max_length=2)),
                ('origin_iata', models.CharField(blank=True, max_length=3)),
                ('destination_iata', models.CharField(blank=True, max_length=3)),
                ('travel_class', models.CharField(blank=True, max_length=20)),
                ('distance_km', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('flagged', 'Flagged — Needs Attention'), ('error', 'Parse/Normalization Error')], default='pending', max_length=20)),
                ('flag_reasons', models.JSONField(default=list)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('analyst_note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_edited', models.BooleanField(default=False)),
                ('locked_at', models.DateTimeField(blank=True, null=True)),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='normalized_records', to='ingestion.ingestionrun')),
                ('raw_record', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='normalized', to='ingestion.rawrecord')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_records', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='normalized_records', to='ingestion.tenant')),
            ],
            options={
                'ordering': ['-ingestion_run__uploaded_at', 'raw_record__row_number'],
            },
        ),
        migrations.AddField(
            model_name='ingestionrun',
            name='tenant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingestion_runs', to='ingestion.tenant'),
        ),
        migrations.AddField(
            model_name='ingestionrun',
            name='uploaded_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(choices=[('created', 'Record Created'), ('status_changed', 'Status Changed'), ('value_edited', 'Value Edited'), ('note_added', 'Note Added'), ('locked', 'Locked for Audit')], max_length=30)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('previous_value', models.JSONField(blank=True, null=True)),
                ('new_value', models.JSONField(blank=True, null=True)),
                ('note', models.TextField(blank=True)),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('normalized_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='ingestion.normalizedrecord')),
            ],
            options={
                'ordering': ['timestamp'],
            },
        ),
        migrations.CreateModel(
            name='TenantMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('admin', 'Admin'), ('analyst', 'Analyst'), ('viewer', 'Viewer')], default='analyst', max_length=20)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='ingestion.tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'tenant')},
            },
        ),
    ]

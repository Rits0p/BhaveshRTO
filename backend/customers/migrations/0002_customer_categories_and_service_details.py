from django.db import migrations, models


def copy_primary_category(apps, schema_editor):
    Customer = apps.get_model('customers', 'Customer')
    for customer in Customer.objects.all().iterator():
        customer.categories = [customer.category]
        customer.save(update_fields=['categories'])


class Migration(migrations.Migration):
    dependencies = [('customers', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='categories',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='customer',
            name='service_details',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(copy_primary_category, migrations.RunPython.noop),
    ]

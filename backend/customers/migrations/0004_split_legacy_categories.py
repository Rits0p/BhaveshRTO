from django.db import migrations


def split_legacy_categories(apps, schema_editor):
    """One-time data migration.

    Before this migration, fitness and PUC shared a single 'fitness_puc'
    category and road tax lived under 'permit'. Records created under the
    old model are re-organized so that each service becomes its own entry:

    - service_details['fitness_puc']  -> service_details['fitness'] and/or ['puc']
    - service_details['permit']       -> service_details['tax']
    - the `categories` list and primary `category` follow the new buckets.
    """
    Customer = apps.get_model('customers', 'Customer')

    for customer in Customer.objects.all().iterator():
        details = dict(customer.service_details or {})
        categories = list(customer.categories or [])
        changed = False

        fp = details.pop('fitness_puc', None)
        if fp is not None:
            changed = True
            categories = [c for c in categories if c != 'fitness_puc']
            has_fitness = fp.get('fitness_start') or fp.get('fitness_end')
            has_puc = fp.get('puc_start') or fp.get('puc_end')
            if has_fitness:
                details['fitness'] = {
                    **fp,
                    'start_date': fp.get('fitness_start') or fp.get('start_date'),
                    'end_date': fp.get('fitness_end') or fp.get('end_date'),
                }
                categories.append('fitness')
            if has_puc:
                details['puc'] = {
                    **fp,
                    'start_date': fp.get('puc_start') or fp.get('start_date'),
                    'end_date': fp.get('puc_end') or fp.get('end_date'),
                }
                categories.append('puc')
            if not has_fitness and not has_puc:
                details['fitness'] = fp
                categories.append('fitness')

        permit = details.pop('permit', None)
        if permit is not None:
            changed = True
            categories = [c for c in categories if c != 'permit']
            details['tax'] = permit
            categories.append('tax')

        if changed:
            categories = list(dict.fromkeys(categories))
            customer.category = categories[0] if categories else customer.category
            customer.categories = categories
            customer.service_details = details
            customer.save(update_fields=['category', 'categories', 'service_details', 'updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0003_alter_customer_category'),
    ]

    operations = [
        migrations.RunPython(split_legacy_categories, migrations.RunPython.noop),
    ]

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_delete_licence'),
    ]

    operations = [
        migrations.AddField(
            model_name='depot',
            name='remise',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Remise'),
        ),
        migrations.AlterField(
            model_name='depot',
            name='prix_unitaire_applique',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]

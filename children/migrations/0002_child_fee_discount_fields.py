from django.db import migrations, models
import decimal


class Migration(migrations.Migration):

    dependencies = [
        ('children', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='child',
            name='fee_discount_amount',
            field=models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=10, verbose_name='Desconto valor'),
        ),
        migrations.AddField(
            model_name='child',
            name='fee_discount_percent',
            field=models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=5, verbose_name='Desconto %'),
        ),
    ]

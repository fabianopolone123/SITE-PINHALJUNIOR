from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='fee',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='Desconto'),
        ),
        migrations.AddField(
            model_name='fee',
            name='final_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='Valor final'),
        ),
        migrations.AlterField(
            model_name='fee',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Valor base'),
        ),
    ]

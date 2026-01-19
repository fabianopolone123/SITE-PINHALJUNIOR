from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('points', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pointsledger',
            name='category',
        ),
    ]

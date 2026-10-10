from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('practice', '0002_learnerpreference')]
    operations = [
        migrations.AddField(model_name='attempt', name='error', field=models.CharField(blank=True, default='', max_length=300), preserve_default=False),
        migrations.AddField(model_name='attempt', name='tests_passed', field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='attempt', name='tests_total', field=models.PositiveSmallIntegerField(default=0)),
    ]

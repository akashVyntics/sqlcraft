from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='Attempt', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('problem_id', models.CharField(max_length=80)), ('sql', models.TextField()),
            ('accepted', models.BooleanField(default=False)), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={'indexes': [models.Index(fields=['user', 'problem_id'], name='practice_at_user_id_d4c82d_idx'), models.Index(fields=['user', 'created_at'], name='practice_at_user_id_9b4b17_idx')]}),
        migrations.CreateModel(name='Draft', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('problem_id', models.CharField(max_length=80)), ('sql', models.TextField()), ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={'constraints': [models.UniqueConstraint(fields=('user', 'problem_id'), name='unique_user_problem_draft')]}),
    ]

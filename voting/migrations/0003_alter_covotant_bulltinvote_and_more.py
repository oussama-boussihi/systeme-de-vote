# Generated by Django 5.1.4 on 2025-02-16 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0002_covotant_date_vote_devotant_date_vote_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='covotant',
            name='bulltinvote',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='devotant',
            name='bulltinvote',
            field=models.TextField(),
        ),
    ]

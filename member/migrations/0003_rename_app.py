# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-14 18:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0002_motd'),
    ]

    operations = [
        migrations.RunSQL("DROP TABLE member_motd"),
        migrations.RunSQL("ALTER TABLE members_motd RENAME TO member_motd"),
        migrations.RunSQL("DROP TABLE member_helptext"),
        migrations.RunSQL("ALTER TABLE members_helptext RENAME TO member_helptext"),
        migrations.RunSQL("DROP TABLE member_usernotification"),
        migrations.RunSQL("ALTER TABLE members_usernotification RENAME TO member_usernotification"),
    ]
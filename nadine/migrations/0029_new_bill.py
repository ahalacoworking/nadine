# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-17 19:59
from __future__ import unicode_literals
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
from django.utils.timezone import localtime, now

import django.db.models.deletion


def forward(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    OldBill = apps.get_model("nadine", "OldBill")
    Transaction = apps.get_model("nadine", "Transaction")
    BillingBatch = apps.get_model("nadine", "BillingBatch")
    UserBill = apps.get_model("nadine", "UserBill")
    BillLineItem = apps.get_model("nadine", "BillLineItem")
    CoworkingDayLineItem = apps.get_model("nadine", "CoworkingDayLineItem")
    Payment = apps.get_model("nadine", "Payment")
    Resource = apps.get_model("nadine", "Resource")
    tz = timezone.get_current_timezone()
    print

    # Pull our Coworking Day Resource
    DAY = Resource.objects.filter(key="day").first()

    # Create a BillingBatch for all these new Bills
    batch = BillingBatch.objects.create()

    print("    Migrating Old Bills...")
    for old_bill in OldBill.objects.all().order_by('bill_date'):
        # OldBill -> UserBill
        if old_bill.paid_by:
            user = old_bill.paid_by
        else:
            user = old_bill.user
        start = old_bill.bill_date
        end = start + relativedelta(months=1) - timedelta(days=1)
        bill = UserBill.objects.create(
            user = user,
            period_start = start,
            period_end = end,
            due_date =  old_bill.bill_date,
            comment = 'Migrated bill',
        )
        # if old_bill.membership:
        #     bill.membership = old_bill.membership.new_membership
        bill_date = datetime.combine(old_bill.bill_date, datetime.min.time())
        bill.created_ts = timezone.make_aware(bill_date, tz)
        bill.save()

        # Add this bill to our BillingBatch
        batch.bills.add(bill)

        # We'll create one line item for the membership
        BillLineItem.objects.create(
            bill = bill,
            description = "Coworking Membership",
            amount = old_bill.amount,
        )

        # Add all the dropins
        for day in old_bill.dropins.all().order_by('visit_date'):
            CoworkingDayLineItem.objects.create(
                bill = bill,
                description = "%s Coworking Day" % day.visit_date,
                day = day,
                amount = 0,
            )
            # Associate this day with this bill
            day.bill = bill
            day.save()

        # Add all our guest dropins
        for day in old_bill.guest_dropins.all().order_by('visit_date'):
            CoworkingDayLineItem.objects.create(
                bill = bill,
                description = "%s Guest Coworking Day (%s)" % (day.visit_date, day.user.username),
                day = day,
                amount = 0,
            )
            # Associate this day with this bill
            day.bill = bill
            day.save()

        # If there are any transactions on this bill
        # we are going to manually mark this as closed and paid
        if old_bill.transactions.count() > 0:
            close_date = datetime.combine(bill.period_end, datetime.max.time())
            bill.closed_ts = timezone.make_aware(close_date, tz)
            bill.mark_paid = True
            bill.save()

        # Transactions -> Payments
        for t in old_bill.transactions.all():
            p = Payment.objects.create(
                bill = bill,
                user = user,
                amount = t.amount,
                note = t.note,
            )
            p.created_ts = t.transaction_date
            p.save()

    # Close up this BillingBatch
    batch.completed_ts = localtime(now())
    batch.successful = True
    batch.save()


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('nadine', '0028_new_membership'),
    ]

    operations = [
        # Create our new models
        migrations.CreateModel(
            name='BillLineItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('custom', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='SubscriptionLineItem',
            fields=[
                ('billlineitem_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='nadine.BillLineItem')),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='nadine.ResourceSubscription')),
            ],
            bases=('nadine.billlineitem',),
        ),
        migrations.CreateModel(
            name='CoworkingDayLineItem',
            fields=[
                ('billlineitem_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='nadine.BillLineItem')),
                ('day', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='nadine.CoworkingDay')),
            ],
            bases=('nadine.billlineitem',),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('note', models.TextField(blank=True, null=True, help_text="Private notes about this payment")),
            ],
        ),
        migrations.CreateModel(
            name='UserBill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True)),
                ('closed_ts', models.DateTimeField(blank=True, null=True)),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('due_date', models.DateField()),
                ('in_progress', models.BooleanField(default=False, help_text="Mark a bill as 'in progress' indicating someone is working on it")),
                ('mark_paid', models.BooleanField(default=False, help_text="Mark a bill as paid even if it is not")),
                ('comment', models.TextField(blank=True, null=True, help_text="Public comments visable by the user")),
                ('note', models.TextField(blank=True, null=True, help_text="Private notes about this bill")),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bills', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='BillingBatch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True)),
                ('completed_ts', models.DateTimeField(blank=True, null=True)),
                ('exception', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('bills', models.ManyToManyField(to='nadine.UserBill')),
            ],
            options={
                'ordering': ['-created_ts'],
                'get_latest_by': 'created_ts',
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='bill',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nadine.UserBill'),
        ),
        migrations.AddField(
            model_name='payment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='billlineitem',
            name='bill',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='nadine.UserBill'),
        ),
        migrations.AddField(
            model_name='coworkingday',
            name='bill',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='nadine.UserBill'),
        ),

        # Convert all the old bills to new ones
        migrations.RunSQL('SET CONSTRAINTS ALL IMMEDIATE', reverse_sql=migrations.RunSQL.noop),
        migrations.RunPython(forward, reverse),
        migrations.RunSQL(migrations.RunSQL.noop, reverse_sql='SET CONSTRAINTS ALL IMMEDIATE'),

    ]

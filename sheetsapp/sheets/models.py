from django.db import models


class Orders(models.Model):
    order_number = models.IntegerField(unique=True)
    price_usd = models.DecimalField(max_digits=15, decimal_places=6)
    delivery_date = models.DateField()
    price_rub = models.DecimalField(max_digits=15, decimal_places=6)

    class Meta:
        managed = False
        db_table = 'orders'
        ordering = ('id',)

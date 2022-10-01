from django.shortcuts import render
from .models import Orders


def stats(request):
    sheets_info = Orders.objects.all()
    return render(request, 
                  'sheets/stats.html', 
                  {'sheets_info': sheets_info})

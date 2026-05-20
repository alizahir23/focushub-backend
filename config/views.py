from django.db import connection
from django.shortcuts import render


def index(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()[0]

    return render(request, "index.html", {"db_version": db_version})

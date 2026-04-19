"""Sample Django views with intentional security and quality issues."""
import subprocess

from django.http import HttpResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt


def get_user(request, user_id):
    """SQL injection via string formatting."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM auth_user WHERE id = %s" % user_id)  # noqa: S608
        row = cursor.fetchone()
    return HttpResponse(str(row))


def search_users(request):
    """SQL injection via f-string."""
    q = request.GET.get("q", "")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM auth_user WHERE username LIKE '%{q}%'")
        rows = cursor.fetchall()
    return HttpResponse(str(rows))


def run_command(request):
    """Command injection via shell=True."""
    name = request.GET.get("name", "")
    result = subprocess.run(f"echo hello {name}", shell=True, capture_output=True)  # noqa: S602
    return HttpResponse(result.stdout)


@csrf_exempt
def api_endpoint(request):
    """CSRF exempt endpoint."""
    return HttpResponse("ok")


def unsafe_eval(request):
    """Dangerous eval."""
    expr = request.GET.get("expr", "1+1")
    result = eval(expr)  # noqa: S307
    return HttpResponse(str(result))

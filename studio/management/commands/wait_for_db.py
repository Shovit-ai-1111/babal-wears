import time
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError, InterfaceError


class Command(BaseCommand):
    help = "Wait for PostgreSQL to accept connections before migrations."

    def handle(self, *args, **options):
        for attempt in range(30):
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT 1")
                self.stdout.write("Database ready.")
                return
            except (OperationalError, InterfaceError):
                connections["default"].close()
                self.stdout.write(f"Waiting for database ({attempt + 1}/30)")
                time.sleep(2)
        raise CommandError("Database unavailable after 30 attempts.")

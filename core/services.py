from django.db import transaction


class BaseService:

    @staticmethod
    @transaction.atomic
    def execute(*args, **kwargs):
        raise NotImplementedError
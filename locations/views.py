from django.http import JsonResponse
from .models import House


def houses_by_farm(request):
    farm_id = request.GET.get("farm")

    if not farm_id:
        return JsonResponse([], safe=False)

    houses = House.objects.filter(
        farm_id=farm_id
    ).order_by("name")

    data = [
        {
            "id": house.id,
            "name": house.name,
        }
        for house in houses
    ]

    return JsonResponse(data, safe=False)
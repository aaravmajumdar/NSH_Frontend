from django.contrib import admin
from .models import Zone
from .models import Container
from .models import Item
from .models import RetrievalLog
from .models import PlacementLog
from .models import UndockingLog



# Register your models here.

admin.site.register(Zone)
admin.site.register(Container)
admin.site.register(Item)
admin.site.register(RetrievalLog)
admin.site.register(PlacementLog)
admin.site.register(UndockingLog)

from django.db import models
from django.utils import timezone

class Zone(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Container(models.Model):
    container_id = models.CharField(max_length=50, unique=True)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='containers')
    width = models.FloatField()
    depth = models.FloatField()
    height = models.FloatField()
    is_undocking = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.container_id} ({self.zone.name})"
    
    @property
    def volume(self):
        return self.width * self.depth * self.height
    
    @property
    def used_volume(self):
        used = 0
        for item in self.items.all():
            used += item.volume
        return used
    
    @property
    def available_volume(self):
        return self.volume - self.used_volume
    
    @property
    def utilization_percentage(self):
        if self.volume == 0:
            return 0
        return (self.used_volume / self.volume) * 100

class Item(models.Model):
    item_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    width = models.FloatField()
    depth = models.FloatField()
    height = models.FloatField()
    mass = models.FloatField()
    priority = models.IntegerField(default=50)  # 1-100 scale
    expiry_date = models.DateTimeField(null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    preferred_zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    container = models.ForeignKey(Container, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    is_waste = models.BooleanField(default=False)
    position_width = models.FloatField(null=True, blank=True)
    position_depth = models.FloatField(null=True, blank=True)
    position_height = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (ID: {self.item_id})"
    
    @property
    def volume(self):
        return self.width * self.depth * self.height
    
    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        return timezone.now() > self.expiry_date
    
    @property
    def is_depleted(self):
        if not self.usage_limit:
            return False
        return self.usage_count >= self.usage_limit
    
    @property
    def should_be_waste(self):
        return self.is_expired or self.is_depleted
    
    def get_position(self):
        if all(x is not None for x in [self.position_width, self.position_depth, self.position_height]):
            return {
                "startCoordinates": {
                    "width": self.position_width,
                    "depth": self.position_depth,
                    "height": self.position_height
                },
                "endCoordinates": {
                    "width": self.position_width + self.width,
                    "depth": self.position_depth + self.depth,
                    "height": self.position_height + self.height
                }
            }
        return None
    


class RetrievalLog(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=50)
    timestamp = models.DateTimeField()
    
    def __str__(self):
        return f"Retrieval of {self.item.name} by {self.user_id} at {self.timestamp}"

class PlacementLog(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=50)
    container = models.ForeignKey(Container, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    
    def __str__(self):
        return f"Placement of {self.item.name} in {self.container.container_id} by {self.user_id} at {self.timestamp}"

class UndockingLog(models.Model):
    container = models.ForeignKey(Container, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    items_removed = models.IntegerField()
    total_volume = models.FloatField()
    total_weight = models.FloatField()
    
    def __str__(self):
        return f"Undocking of {self.container.container_id} at {self.timestamp}"

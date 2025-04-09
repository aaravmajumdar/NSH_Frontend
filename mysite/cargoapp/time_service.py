from .models import Item
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List

class TimeService:
    def __init__(self):
        self.current_date = timezone.now()
    
    def simulate_days(self, num_of_days=None, to_timestamp=None, items_to_be_used=None) -> Dict:
        """Simulate the passage of time"""
        if not num_of_days and not to_timestamp:
            return {
                "success": False,
                "message": "Must provide either numOfDays or toTimestamp"
            }
        
        # Calculate new date
        if num_of_days:
            new_date = self.current_date + timedelta(days=num_of_days)
        else:
            new_date = timezone.datetime.fromisoformat(to_timestamp)
        
        # Initialize tracking lists
        items_used = []
        items_expired = []
        items_depleted = []
        
        # Process items to be used
        if items_to_be_used:
            for item_info in items_to_be_used:
                # Get the item
                try:
                    if 'itemId' in item_info:
                        item = Item.objects.get(item_id=item_info['itemId'])
                    else:
                        item = Item.objects.filter(name=item_info['name']).first()
                    
                    if not item:
                        continue
                    
                    # Update usage count
                    if item.usage_limit:
                        item.usage_count += 1
                        
                        # Check if item is now depleted
                        if item.usage_count >= item.usage_limit:
                            item.is_waste = True
                            items_depleted.append({
                                "itemId": item.item_id,
                                "name": item.name
                            })
                        
                        items_used.append({
                            "itemId": item.item_id,
                            "name": item.name,
                            "remainingUses": item.usage_limit - item.usage_count
                        })
                    
                    item.save()
                    
                except Item.DoesNotExist:
                    continue
        
        # Check for expired items
        if num_of_days or to_timestamp:
            expired_query = Item.objects.filter(
                expiry_date__lt=new_date,
                expiry_date__gte=self.current_date,
                is_waste=False
            )
            
            for item in expired_query:
                item.is_waste = True
                item.save()
                
                items_expired.append({
                    "itemId": item.item_id,
                    "name": item.name
                })
        
        # Update current date
        self.current_date = new_date
        
        return {
            "success": True,
            "newDate": new_date.isoformat(),
            "changes": {
                "itemsUsed": items_used,
                "itemsExpired": items_expired,
                "itemsDepletedToday": items_depleted
            }
        }

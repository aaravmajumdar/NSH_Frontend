from .models import Item, Container, RetrievalLog
from django.utils import timezone
from typing import Dict, List, Optional

class SearchService:
    def search_item(self, item_id=None, item_name=None, user_id=None) -> Dict:
        """
        Search for an item by ID or name and provide retrieval steps
        """
        if not item_id and not item_name:
            return {
                "success": False,
                "found": False,
                "message": "Must provide either item ID or name"
            }
        
        try:
            # Find the item
            if item_id:
                item = Item.objects.get(item_id=item_id)
            else:
                item = Item.objects.filter(name=item_name).first()
            
            if not item:
                return {
                    "success": True,
                    "found": False,
                    "message": "Item not found"
                }
            
            # Get container info
            if not item.container:
                return {
                    "success": True,
                    "found": True,
                    "item": self._serialize_item(item),
                    "message": "Item is not in any container"
                }
            
            # Calculate retrieval steps
            retrieval_steps = self._calculate_retrieval_steps(item)
            
            return {
                "success": True,
                "found": True,
                "item": self._serialize_item(item),
                "retrievalSteps": retrieval_steps
            }
        
        except Exception as e:
            return {
                "success": False,
                "found": False,
                "message": str(e)
            }
    
    def _serialize_item(self, item) -> Dict:
        """Serialize item for API response"""
        return {
            "itemId": item.item_id,
            "name": item.name,
            "containerId": item.container.container_id if item.container else None,
            "zone": item.container.zone.name if item.container else None,
            "position": item.get_position()
        }
    
    def _calculate_retrieval_steps(self, target_item) -> List[Dict]:
        """Calculate steps to retrieve an item"""
        steps = []
        step_counter = 1
        
        # If item not in a container, no steps needed
        if not target_item.container:
            return []
        
        # Get all items in the same container
        items_in_container = Item.objects.filter(container=target_item.container)
        
        # Find items blocking the target item
        blocking_items = self._find_blocking_items(target_item, items_in_container)
        
        # Add steps to remove blocking items
        for item in blocking_items:
            steps.append({
                "step": step_counter,
                "action": "remove",
                "itemId": item.item_id,
                "itemName": item.name
            })
            step_counter += 1
            
            steps.append({
                "step": step_counter,
                "action": "setAside",
                "itemId": item.item_id,
                "itemName": item.name
            })
            step_counter += 1
        
        # Add step to retrieve target item
        steps.append({
            "step": step_counter,
            "action": "retrieve",
            "itemId": target_item.item_id,
            "itemName": target_item.name
        })
        step_counter += 1
        
        # Add steps to place back blocking items
        for item in reversed(blocking_items):
            steps.append({
                "step": step_counter,
                "action": "placeBack",
                "itemId": item.item_id,
                "itemName": item.name
            })
            step_counter += 1
        
        return steps
    
    def _find_blocking_items(self, target_item, items_in_container) -> List[Item]:
        """Find items blocking the target item"""
        # This is a simplified algorithm - in real implementation we need more sophisticated
        # logic based on 3D positioning
        
        blocking_items = []
        
        # Get target item coordinates
        if not all([target_item.position_width, target_item.position_depth, target_item.position_height]):
            return []
            
        target_x = target_item.position_width
        target_y = target_item.position_depth
        target_z = target_item.position_height
        
        # Check for items that are in front of the target item
        for item in items_in_container:
            if item.id == target_item.id:
                continue
                
            if not all([item.position_width, item.position_depth, item.position_height]):
                continue
            
            # If item is at a smaller depth (closer to the open face)
            # and overlaps with the target item in width and height
            if (item.position_depth < target_y and
                self._check_overlap(item.position_width, item.position_width + item.width,
                                  target_x, target_x + target_item.width) and
                self._check_overlap(item.position_height, item.position_height + item.height,
                                  target_z, target_z + target_item.height)):
                blocking_items.append(item)
        
        # Sort blocking items by depth (items closest to the open face first)
        blocking_items.sort(key=lambda x: x.position_depth)
        
        return blocking_items
    
    def _check_overlap(self, min1, max1, min2, max2) -> bool:
        """Check if two ranges overlap"""
        return max(0, min(max1, max2) - max(min1, min2)) > 0
    
    def retrieve_item(self, item_id, user_id, timestamp=None) -> Dict:
        """Mark item as retrieved and log the retrieval"""
        if not timestamp:
            timestamp = timezone.now()
            
        try:
            item = Item.objects.get(item_id=item_id)
            
            # Update usage count
            if item.usage_limit:
                item.usage_count += 1
                
                # Check if item is now depleted
                if item.usage_count >= item.usage_limit:
                    item.is_waste = True
            
            item.save()
            
            # Log the retrieval
            RetrievalLog.objects.create(
                item=item,
                user_id=user_id,
                timestamp=timestamp
            )
            
            return {
                "success": True
            }
        except Item.DoesNotExist:
            return {
                "success": False,
                "message": "Item not found"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

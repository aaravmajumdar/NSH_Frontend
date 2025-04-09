from .models import Item, Container, UndockingLog
from django.utils import timezone
from typing import Dict, List
from django.db.models import F

class WasteService:
    def identify_waste(self) -> Dict:
        """Identify items that are waste (expired or depleted)"""
        now = timezone.now()
        
        # Find expired items
        expired_items = Item.objects.filter(
            expiry_date__lt=now,
            is_waste=False
        )
        
        # Find depleted items
        depleted_items = Item.objects.filter(
            usage_limit__isnull=False,
            usage_count__gte=F('usage_limit'),
            is_waste=False
        )
        
        # Mark items as waste
        for item in list(expired_items) + list(depleted_items):
            item.is_waste = True
            item.save()
        
        # Get all waste items for the response
        waste_items = Item.objects.filter(is_waste=True)
        
        return {
            "success": True,
            "wasteItems": [self._serialize_waste_item(item) for item in waste_items]
        }
    
    def _serialize_waste_item(self, item) -> Dict:
        """Serialize waste item for API response"""
        reason = "Unknown"
        if item.is_expired:
            reason = "Expired"
        elif item.is_depleted:
            reason = "Out of Uses"
            
        return {
            "itemId": item.item_id,
            "name": item.name,
            "reason": reason,
            "containerId": item.container.container_id if item.container else None,
            "position": item.get_position()
        }
    
    def generate_return_plan(self, undocking_container_id, undocking_date, max_weight) -> Dict:
        """Generate a plan for returning waste items"""
        try:
            # Get undocking container
            undocking_container = Container.objects.get(container_id=undocking_container_id)
            
            # Mark container as undocking
            undocking_container.is_undocking = True
            undocking_container.save()
            
            # Get waste items
            waste_items = Item.objects.filter(is_waste=True)
            
            # Create return plan
            return_plan = []
            retrieval_steps = []
            step_counter = 1
            total_weight = 0
            total_volume = 0
            return_items = []
            
            # Sort waste items by weight (heaviest first to optimize packing)
            sorted_waste = sorted(waste_items, key=lambda x: x.mass, reverse=True)
            
            for item in sorted_waste:
                # Check if adding this item would exceed the max weight
                if total_weight + item.mass > max_weight:
                    continue
                    
                # Add item to return plan
                return_plan.append({
                    "step": step_counter,
                    "itemId": item.item_id,
                    "itemName": item.name,
                    "fromContainer": item.container.container_id if item.container else "None",
                    "toContainer": undocking_container_id
                })
                step_counter += 1
                
                # Add retrieval steps if item is in a container
                if item.container:
                    # Calculate retrieval steps
                    from .search_service import SearchService
                    search_service = SearchService()
                    item_retrieval_steps = search_service._calculate_retrieval_steps(item)
                    retrieval_steps.extend(item_retrieval_steps)
                
                # Update totals
                total_weight += item.mass
                total_volume += item.volume
                
                # Add to return items list
                return_items.append({
                    "itemId": item.item_id,
                    "name": item.name,
                    "reason": "Expired" if item.is_expired else "Out of Uses"
                })
            
            return {
                "success": True,
                "returnPlan": return_plan,
                "retrievalSteps": retrieval_steps,
                "returnManifest": {
                    "undockingContainerId": undocking_container_id,
                    "undockingDate": undocking_date,
                    "returnItems": return_items,
                    "totalVolume": total_volume,
                    "totalWeight": total_weight
                }
            }
            
        except Container.DoesNotExist:
            return {
                "success": False,
                "message": "Undocking container not found"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    def complete_undocking(self, undocking_container_id, timestamp=None) -> Dict:
        """Complete the undocking process"""
        if not timestamp:
            timestamp = timezone.now()
            
        try:
            # Get undocking container
            undocking_container = Container.objects.get(
                container_id=undocking_container_id,
                is_undocking=True
            )
            
            # Get all waste items in the container
            waste_items = Item.objects.filter(
                container=undocking_container,
                is_waste=True
            )
            
            # Calculate total volume and weight
            total_volume = sum(item.volume for item in waste_items)
            total_weight = sum(item.mass for item in waste_items)
            items_count = waste_items.count()
            
            # Remove items
            waste_items.delete()
            
            # Reset container state
            undocking_container.is_undocking = False
            undocking_container.save()
            
            # Log the undocking
            UndockingLog.objects.create(
                container=undocking_container,
                timestamp=timestamp,
                items_removed=items_count,
                total_volume=total_volume,
                total_weight=total_weight
            )
            
            return {
                "success": True,
                "itemsRemoved": items_count
            }
            
        except Container.DoesNotExist:
            return {
                "success": False,
                "message": "Undocking container not found or not marked for undocking"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

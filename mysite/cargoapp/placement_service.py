from .models import Item, Container, Zone
from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.utils import timezone
import numpy as np
from typing import List, Dict, Any, Tuple

class PlacementService:
    def __init__(self):
        pass
    
    def find_optimal_placement(self, items: List[Dict], containers: List[Dict]) -> Dict:
        """
        Find optimal placement for items in containers
        """
        placements = []
        rearrangements = []
        
        # Sort items by priority (highest first)
        sorted_items = sorted(items, key=lambda x: x['priority'], reverse=True)
        
        for item in sorted_items:
            # First try preferred zone
            preferred_container = self._find_container_in_preferred_zone(item, containers)
            
            if preferred_container:
                placement = self._place_item_in_container(item, preferred_container)
                placements.append(placement)
            else:
                # If no space in preferred zone, try other zones
                other_container = self._find_container_in_any_zone(item, containers)
                
                if other_container:
                    placement = self._place_item_in_container(item, other_container)
                    placements.append(placement)
                else:
                    # If no space anywhere, recommend rearrangements
                    reorg_result = self._suggest_reorganization(item, containers)
                    if reorg_result:
                        rearrangement, placement = reorg_result
                        rearrangements.extend(rearrangement)
                        placements.append(placement)
        
        return {
            "success": True,
            "placements": placements,
            "rearrangements": rearrangements
        }
    
    def _find_container_in_preferred_zone(self, item: Dict, containers: List[Dict]) -> Dict:
        """Find suitable container in preferred zone"""
        preferred_zone = item.get('preferredZone')
        if not preferred_zone:
            return None
            
        # Filter containers by preferred zone
        zone_containers = [c for c in containers if c['zone'] == preferred_zone]
        
        # Find container with enough space
        item_volume = item['width'] * item['depth'] * item['height']
        
        for container in zone_containers:
            # Check if container has enough space
            if self._can_fit_item(item, container):
                return container
                
        return None
    
    def _find_container_in_any_zone(self, item: Dict, containers: List[Dict]) -> Dict:
        """Find any container with enough space"""
        item_volume = item['width'] * item['depth'] * item['height']
        
        for container in containers:
            if self._can_fit_item(item, container):
                return container
                
        return None
    
    def _can_fit_item(self, item: Dict, container: Dict) -> bool:
        """Check if item can fit in container"""
        # This is a simple check - in reality we need 3D bin packing algorithm
        # Here we just check if dimensions fit
        
        # Try all possible orientations
        orientations = [
            (item['width'], item['depth'], item['height']),
            (item['width'], item['height'], item['depth']),
            (item['depth'], item['width'], item['height']),
            (item['depth'], item['height'], item['width']),
            (item['height'], item['width'], item['depth']),
            (item['height'], item['depth'], item['width'])
        ]
        
        for w, d, h in orientations:
            if (w <= container['width'] and 
                d <= container['depth'] and 
                h <= container['height']):
                return True
                
        return False
    
    def _place_item_in_container(self, item: Dict, container: Dict) -> Dict:
        """Calculate exact position in container and create placement record"""
        # For simplicity, place at origin (0,0,0)
        # In real implementation, need 3D bin packing algorithm to find exact position
        
        position = {
            "startCoordinates": {
                "width": 0,
                "depth": 0,
                "height": 0
            },
            "endCoordinates": {
                "width": item['width'],
                "depth": item['depth'],
                "height": item['height']
            }
        }
        
        return {
            "itemId": item['itemId'],
            "containerId": container['containerId'],
            "position": position
        }
    
    def _suggest_reorganization(self, item: Dict, containers: List[Dict]) -> Tuple[List[Dict], Dict]:
        """Suggest reorganization to make space for item"""
        # Find containers with low priority items that could be moved
        
        # For demo, return a simple rearrangement
        rearrangements = [
            {
                "step": 1,
                "action": "move",
                "itemId": "item_to_move",
                "fromContainer": "contA",
                "fromPosition": {
                    "startCoordinates": {"width": 0, "depth": 0, "height": 0},
                    "endCoordinates": {"width": 10, "depth": 10, "height": 10}
                },
                "toContainer": "contB",
                "toPosition": {
                    "startCoordinates": {"width": 0, "depth": 0, "height": 0},
                    "endCoordinates": {"width": 10, "depth": 10, "height": 10}
                }
            }
        ]
        
        # Assume we've made space in contA
        placement = {
            "itemId": item['itemId'],
            "containerId": "contA",
            "position": {
                "startCoordinates": {"width": 0, "depth": 0, "height": 0},
                "endCoordinates": {
                    "width": item['width'],
                    "depth": item['depth'],
                    "height": item['height']
                }
            }
        }
        
        return rearrangements, placement

    def apply_placements(self, placements: List[Dict], rearrangements: List[Dict]):
        """Apply placements and rearrangements to the database"""
        # Handle rearrangements first
        for reorg in rearrangements:
            item = Item.objects.get(item_id=reorg['itemId'])
            to_container = Container.objects.get(container_id=reorg['toContainer'])
            
            # Update item position
            item.container = to_container
            item.position_width = reorg['toPosition']['startCoordinates']['width']
            item.position_depth = reorg['toPosition']['startCoordinates']['depth']
            item.position_height = reorg['toPosition']['startCoordinates']['height']
            item.save()
        
        # Now handle placements
        for placement in placements:
            item = Item.objects.get(item_id=placement['itemId'])
            container = Container.objects.get(container_id=placement['containerId'])
            
            # Update item position
            item.container = container
            item.position_width = placement['position']['startCoordinates']['width']
            item.position_depth = placement['position']['startCoordinates']['depth']
            item.position_height = placement['position']['startCoordinates']['height']
            item.save()

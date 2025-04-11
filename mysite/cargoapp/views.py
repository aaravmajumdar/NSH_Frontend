from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv
import pandas as pd
from io import StringIO
from datetime import datetime

from .models import Zone, Container, Item, RetrievalLog, PlacementLog
from .placement_service import PlacementService
from .search_service import SearchService
from .waste_service import WasteService
from .time_service import TimeService

from django.shortcuts import render, redirect
from django.template import loader
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Sum
from typing import Dict, List

# Initialize services
placement_service = PlacementService()
search_service = SearchService()
waste_service = WasteService()
time_service = TimeService()

def index(request):
    """Render the main application page"""
    return render(request, 'cargo_app/index.html')

# Placement API
@csrf_exempt
def api_placement(request):
    """API endpoint for placement recommendations"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate request
        if 'items' not in data or 'containers' not in data:
            return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)
        
        # Process placement request
        result = placement_service.find_optimal_placement(data['items'], data['containers'])
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

# Search APIs
@csrf_exempt
def api_search(request):
    if request.method == 'GET':
        item_name = request.GET.get('itemName')
        
        if not item_name:
            return JsonResponse({"success": False, "message": "Must provide itemName"}, status=400)
        
        result = search_service.search_item(item_name=item_name)
        return JsonResponse(result)
    else:
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)

@csrf_exempt
def api_retrieve(request):
    """API endpoint for item retrieval"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate request
        if 'itemId' not in data or 'userId' not in data:
            return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)
        
        # Process retrieval request
        result = search_service.retrieve_item(
            data['itemId'],
            data['userId'], 
            data.get('timestamp')
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

@csrf_exempt
def api_place(request):
    """API endpoint for item placement"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate request
        required_fields = ['itemId', 'userId', 'containerId', 'position']
        if not all(field in data for field in required_fields):
            return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)
        
        # Get item and container
        try:
            item = Item.objects.get(item_id=data['itemId'])
            container = Container.objects.get(container_id=data['containerId'])
        except Item.DoesNotExist:
            return JsonResponse({"success": False, "message": "Item not found"}, status=404)
        except Container.DoesNotExist:
            return JsonResponse({"success": False, "message": "Container not found"}, status=404)
        
        # Update item position
        item.container = container
        item.position_width = data['position']['startCoordinates']['width']
        item.position_depth = data['position']['startCoordinates']['depth']
        item.position_height = data['position']['startCoordinates']['height']
        item.save()
        
        # Log the placement
        timestamp = data.get('timestamp', datetime.now().isoformat())
        PlacementLog.objects.create(
            item=item,
            user_id=data['userId'],
            container=container,
            timestamp=timestamp
        )
        
        return JsonResponse({"success": True})
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

# Waste Management APIs
def api_waste_identify(request):
    """API endpoint to identify waste items"""
    if request.method != 'GET':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    result = waste_service.identify_waste()
    return JsonResponse(result)

@csrf_exempt
def api_waste_return_plan(request):
    """API endpoint for waste return planning"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate request
        required_fields = ['undockingContainerId', 'undockingDate', 'maxWeight']
        if not all(field in data for field in required_fields):
            return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)
        
        # Process return plan request
        result = waste_service.generate_return_plan(
            data['undockingContainerId'],
            data['undockingDate'],
            data['maxWeight']
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

@csrf_exempt
def api_waste_complete_undocking(request):
    """API endpoint to complete undocking"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate request
        if 'undockingContainerId' not in data:
            return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)
        
        # Process undocking completion
        result = waste_service.complete_undocking(
            data['undockingContainerId'],
            data.get('timestamp')
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

# Time Simulation API
@csrf_exempt
def api_simulate_day(request):
    """API endpoint for time simulation"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Process simulation request
        result = time_service.simulate_days(
            data.get('numOfDays'),
            data.get('toTimestamp'),
            data.get('itemsToBeUsedPerDay', [])
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)
    
def get_container_utilization(self):
        """
        Calculates the container's utilization.
        Returns:
            float: Percentage of utilization (0-100).
        """
        total_volume = self.width * self.depth * self.height
        used_volume = 0
        for item in self.items.all():  # Iterate over related items
            used_volume += item.width * item.depth * item.height
        
        if total_volume == 0:
            return 0  # Avoid division by zero
        
        return (used_volume / total_volume) * 100

        
def can_fit_item(self, item_width, item_depth, item_height):
        """
        Checks if an item of given dimensions can fit inside the container.
        Parameters:
            item_width (float): Width of the item.
            item_depth (float): Depth of the item.
            item_height (float): Height of the item.
        Returns:
            bool: True if the item fits, False otherwise.
        """
        available_width = self.width - (self.items.aggregate(Sum('width'))['width__sum'] or 0)
        available_depth = self.depth - (self.items.aggregate(Sum('depth'))['depth__sum'] or 0)
        available_height = self.height - (self.items.aggregate(Sum('height'))['height__sum'] or 0)
        
        return item_width <= available_width and item_depth <= available_depth and item_height <= available_height

def has_capacity_for_item(self, item):
        """
        Verifies if container has enough volume to accept the item.
        Args:
            item (Item): the Item instance for which the space should be checked
        Returns:
            bool: if True, there's enough space for item, otherwise False
        """
        
        available_volume = self.available_volume
        item_volume = item.volume


def home(response):
    return render(response, "index.html", {})

def search(response):
        return render(response, "item_search.html", {})

def rearrange(response):
        return render(response, "rearrangement.html", {})

def simulation(response):
        return render(response, "simulation.html", {})

def waste_management(response):
        return render(response, "waste_management.html", {})

def placement(response):
        return render(response, "placement.html", {})

def login_form(request):
        if request.method == 'POST':
                username = request.POST.get('username')
                password = request.POST.get('password')
                user = authenticate(request, username=username, password=password)
                if user is not None:
                        login(request, user)
                        return redirect('/')
                else:
                        messages.error(request, 'Invalid username or password')
        return render(request, "login.html", {})

def logout_view(request):
        logout(request)
        return redirect('/')
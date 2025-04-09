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
def api_search(request):
    """API endpoint for item search"""
    if request.method != 'GET':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    item_id = request.GET.get('itemId')
    item_name = request.GET.get('itemName')
    user_id = request.GET.get('userId')
    
    if not item_id and not item_name:
        return JsonResponse({"success": False, "message": "Must provide either itemId or itemName"}, status=400)
    
    result = search_service.search_item(item_id, item_name, user_id)
    return JsonResponse(result)

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

# Import/Export APIs
@csrf_exempt
def api_import_items(request):
    """API endpoint to import items from CSV"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        csv_file = request.FILES.get('file')
        if not csv_file:
            return JsonResponse({"success": False, "message": "No file uploaded"}, status=400)
        
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Process import
        items_imported = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Check if item already exists
                if Item.objects.filter(item_id=row['Item ID']).exists():
                    item = Item.objects.get(item_id=row['Item ID'])
                else:
                    item = Item(item_id=row['Item ID'])
                
                # Get preferred zone if specified
                preferred_zone = None
                if 'Preferred Zone' in row and row['Preferred Zone']:
                    zone_name = row['Preferred Zone']
                    preferred_zone, _ = Zone.objects.get_or_create(name=zone_name)
                
                # Update item fields
                item.name = row['Name']
                item.width = row['Width (cm)']
                item.depth = row['Depth (cm)']
                item.height = row['Height (cm)']
                item.mass = row['Mass (kg)']
                item.priority = row['Priority (1-100)']
                
                # Handle expiry date
                if 'Expiry Date' in row and row['Expiry Date'] and row['Expiry Date'].lower() != 'n/a':
                    item.expiry_date = datetime.fromisoformat(row['Expiry Date'])
                
                # Handle usage limit
                if 'Usage Limit' in row and row['Usage Limit'] and row['Usage Limit'].lower() != 'n/a':
                    item.usage_limit = int(row['Usage Limit'])
                
                item.preferred_zone = preferred_zone
                item.save()
                
                items_imported += 1
                
            except Exception as e:
                errors.append({"row": index + 2, "message": str(e)})
        
        return JsonResponse({
            "success": True,
            "itemsImported": items_imported,
            "errors": errors
        })
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

@csrf_exempt
def api_import_containers(request):
    """API endpoint to import containers from CSV"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        csv_file = request.FILES.get('file')
        if not csv_file:
            return JsonResponse({"success": False, "message": "No file uploaded"}, status=400)
        
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Process import
        containers_imported = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Check if container already exists
                if Container.objects.filter(container_id=row['Container ID']).exists():
                    container = Container.objects.get(container_id=row['Container ID'])
                else:
                    container = Container(container_id=row['Container ID'])
                
                # Get or create zone
                zone_name = row['Zone']
                zone, _ = Zone.objects.get_or_create(name=zone_name)
                
                # Update container fields
                container.zone = zone
                container.width = row['Width(cm)']
                container.depth = row['Depth(cm)']
                container.height = row['Height(height)']
                container.save()
                
                containers_imported += 1
                
            except Exception as e:
                errors.append({"row": index + 2, "message": str(e)})
        
        return JsonResponse({
            "success": True,
            "containersImported": containers_imported,
            "errors": errors
        })
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

def api_export_arrangement(request):
    """API endpoint to export current arrangement to CSV"""
    if request.method != 'GET':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
    
    try:
        # Get all placed items
        items = Item.objects.filter(container__isnull=False)
        
        # Create CSV data
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(['Item ID', 'Container ID', 'Coordinates (W1,D1,H1),(W2,D2,H2)'])
        
        for item in items:
            position = item.get_position()
            if position:
                start = position['startCoordinates']
                end = position['endCoordinates']
                coords = f"({start['width']},{start['depth']},{start['height']}),({end['width']},{end['depth']},{end['height']})"
                writer.writerow([item.item_id, item.container.container_id, coords])
        
        # Create response
        response = HttpResponse(csv_data.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="arrangement.csv"'
        
        return response
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

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
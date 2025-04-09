from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout

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
import csv
import json

from django.contrib import auth
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template.context_processors import csrf

from game_collection.models import Tag
from game_database.functions import GameHoarderDB
from game_database.models import Genre, Platform
from .forms import *


@login_required(login_url='login')
def index(request):
    custom = Tag.objects.filter(user=request.user)

    context = {
        "tags": custom
    }
    return render(request, "index.html", context)


@login_required(login_url='login')
def friends(request):
    return render(request, "index.html")


@login_required(login_url='login')
def profileView(request):
    return render(request, "account/profileView.html")


@login_required(login_url='login')
def download_csv(request):
    if request.method == 'POST':
        response = HttpResponse(content_type='text/csv')
        data = request.POST.getlist("data")

        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % request.POST.get("filename")

        writer = csv.writer(response)

        headers = json.loads(data[0].replace("'", '"'))
        writer.writerow(headers.keys())

        for row in data:
            title = json.loads(row.replace("'", '"'))

            if 'original_title' in title:
                title["game"] = title["original_title"]
                title.pop("original_title")

            writer.writerow(list(title.values()))

        return response


def login_register(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('login')
        else:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponseRedirect('/es/')
    else:
        form = UserForm

    token = {}
    token.update(csrf(request))
    token['form'] = form

    return render(request, 'login_register.html')


@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect("login")


@login_required(login_url='login')
def search(request):
    # multiple-choice values
    choices = ['genres', 'platforms']
    # all values except those
    params = {k: v for k, v in request.GET.dict().items() if k[:-2] not in choices}

    # check if external API should be used
    use_api = False
    try:
        use_api = params.pop('use_api')
        use_api = use_api == "true"
    except KeyError:
        pass

    # extract multiple-choice values
    for choice in choices:
        if f'{choice}[]' in request.GET.keys():
            params[choice] = request.GET.getlist(f'{choice}[]')

    # if query is empty, don't search
    if not GameHoarderDB.params_empty(params):
        games = GameHoarderDB.search(params, use_api=use_api)
    else:
        games = None
    platforms = [p.get('name') for p in Platform.objects.order_by().values('name').distinct()]
    genres = [g.get('name') for g in Genre.objects.order_by().values('name').distinct()]
    return render(request, 'search/search_form.html', {
        'first_platform': platforms[0] if len(platforms) > 0 else None,
        'first_genre': genres[0] if len(genres) > 0 else None,
        'platforms': platforms[1:] if len(platforms) > 1 else [],
        'genres': genres[1:] if len(genres) > 1 else [],
        'games': games,
        'user': request.user.interested_set
    })


@login_required(login_url='login')
def change_friends(request, operation, pk):
    pass
    friend = User.objects.get(pk=pk)
    if operation == 'add':
        Profile.make_friend(request.user, friend)
    elif operation == 'remove':
        Profile.lose_friend(request.user, friend)
    return redirect('home:home')

from django.shortcuts import render, redirect, get_object_or_404
from .models import Profile, Task, Status, Team
from .forms import TaskForm
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse



def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('task_list')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(User=user)
            login(request, user)
            return redirect('select_role_and_team')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def select_role_and_team(request):
    profile, created = Profile.objects.get_or_create(User=request.user)
    teams = Team.objects.all()

    if request.method == 'POST':
        selected_role = request.POST.get('role')
        selected_team_id = request.POST.get('team')

        profile.role = selected_role
        if selected_team_id:
            profile.team = Team.objects.get(Id=selected_team_id)
        else:
            profile.team = None

        profile.save()
        messages.success(request, "התפקיד והצוות שלך נשמרו בהצלחה!")
        return redirect('task_list')

    return render(request, 'accounts/chooserole.html', {'profile': profile, 'teams': teams})


# --- ניהול משימות ---

@login_required
def task_list(request):
    if request.method == 'GET':
        # 1. שליפת הפרופיל
        profile, created = Profile.objects.get_or_create(User=request.user)

        if not profile.team:
            tasks = Task.objects.none()
        else:
            tasks = Task.objects.filter(Teams=profile.team)


        status_filter = request.GET.get('status')
        mine_filter = request.GET.get('mine')

        if status_filter:
            tasks = tasks.filter(myStatus=status_filter)

        if mine_filter == 'true':
            tasks = tasks.filter(AssignedUser=request.user)


        context = {
            "tasks": tasks,
            "profile": profile,
            "current_status": status_filter,
            "current_mine": mine_filter
        }
        return render(request, "Task/view.html", context)

    return JsonResponse({'status': 'false', 'message': 'Method not allowed'}, status=405)


@login_required
def task_create(request):
    try:
        profile = Profile.objects.get(User=request.user)
    except Profile.DoesNotExist:
        return redirect('login')

    if profile.role != 'admin':
        return redirect('task_list')

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            # שיוך אוטומטי לצוות של המנהל
            task.Teams = profile.team
            task.save()
            return redirect('task_list')
        else:
            print("Form Errors:", form.errors)
    else:
        form = TaskForm()

    return render(request, "Task/add.html", {"form": form})


@login_required
def task_update(request, id):
    profile = Profile.objects.get(User=request.user)

    # תיקון: בדיקה מול 'admin' באותיות קטנות
    if profile.role != 'admin':
        return redirect('task_list')

    task = get_object_or_404(Task, id=id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('task_list')
    else:
        form = TaskForm(instance=task)
    return render(request, "Task/add.html", {"form": form, "task": task})


@login_required
def task_delete(request, id):
    profile = Profile.objects.get(User=request.user)

    if profile.role != 'admin':
        return redirect('task_list')

    task = get_object_or_404(Task, id=id)
    task.delete()
    return redirect('task_list')



@login_required
def task_claim(request, id):
    task = get_object_or_404(Task, id=id)
    profile = Profile.objects.get(User=request.user)

    if profile.role == 'user' and task.Teams == profile.team and task.myStatus == 'new':
        task.AssignedUser = request.user
        task.myStatus = 'in progress'
        task.save()

    return redirect('task_list')


@login_required
def task_complete(request, id):
    task = get_object_or_404(Task, id=id)

    if task.AssignedUser == request.user and task.myStatus == 'in progress':
        task.myStatus = 'completed'
        task.save()

    return redirect('task_list')
import os
import sys
import subprocess
import psutil
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import Machine, TagLatestSnapshot
from datetime import timedelta

COLLECTOR_SCRIPT_NAME = "main.py"
TAG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'collector', 'Tag')
DEFAULT_CSV_HEADER = "machine_name,tag_name,opc_address,deadband,description\n"

def get_python_executable():
    return sys.executable

def get_collector_process():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and COLLECTOR_SCRIPT_NAME in str(cmdline):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print("Error getting collector process.")
            continue
    return None

def dashboard(request):
    machines = Machine.objects.all()
    snapshots = TagLatestSnapshot.objects.select_related('tag', 'tag__machine').all()
    collector_proc = get_collector_process()
    is_running = collector_proc is not None
    
    opc_connected = False
    now = timezone.now()
    latest_update = snapshots.order_by('-last_update').first()
    if latest_update and latest_update.last_update:
        if now - latest_update.last_update < timedelta(seconds=15):
            opc_connected = True

    dashboard_data = []
    for machine in machines:
        machine_tags = [s for s in snapshots if s.tag.machine_id == machine.id]
        dashboard_data.append({
            'machine': machine,
            'tags': machine_tags,
            'total_tags': len(machine_tags),
            'active_tags': len([t for t in machine_tags if t.last_status == 'Good'])
        })

    context = {
        'dashboard_data': dashboard_data,
        'last_sync': timezone.now(),
        'total_machines': len(machines),
        'total_tags_count': len(snapshots),
        'collector_running': is_running,
        'opc_connected': opc_connected,
        'collector_pid': collector_proc.pid if is_running else None
    }
    return render(request, 'monitoring/dashboard.html', context)

def api_get_snapshots(request):
    snapshots = TagLatestSnapshot.objects.select_related('tag').all()
    data = []
    for s in snapshots:
        data.append({
            'tag_id': s.tag.id,
            'value': s.last_value,
            'status': s.last_status,
            'update_time': s.last_update.strftime("%H:%M:%S") if s.last_update else "---"
        })
    collector_proc = get_collector_process()
    is_running = collector_proc is not None
    opc_connected = TagLatestSnapshot.objects.filter(last_update__gte=timezone.now() - timedelta(seconds=15)).exists()
    return JsonResponse({
        'tags': data,
        'collector_running': is_running,
        'opc_connected': opc_connected,
        'last_sync': timezone.now().strftime("%H:%M:%S")
    })

# --- FILE MANAGEMENT VIEWS ---

def tag_config_list(request):
    if not os.path.exists(TAG_DIR):
        os.makedirs(TAG_DIR)
    files = []
    for filename in os.listdir(TAG_DIR):
        if filename.endswith(('.csv', '.xlsx', '.xls')):
            file_path = os.path.join(TAG_DIR, filename)
            stats = os.stat(file_path)
            files.append({
                'name': filename,
                'size': f"{stats.st_size / 1024:.1f} KB",
                'modified': timezone.datetime.fromtimestamp(stats.st_mtime)
            })
    collector_proc = get_collector_process()
    is_running = collector_proc is not None
    opc_connected = TagLatestSnapshot.objects.filter(last_update__gte=timezone.now() - timedelta(seconds=15)).exists()

    return render(request, 'monitoring/tag_config.html', {
        'files': files,
        'collector_running': is_running,
        'opc_connected': opc_connected
    })

def create_tag_file(request):
    if request.method == 'POST':
        filename = request.POST.get('filename', '').strip()
        if not filename:
            messages.error(request, "Filename is required.")
            return redirect('tag_config_list')
        
        if not filename.endswith('.csv'):
            filename += '.csv'
            
        file_path = os.path.join(TAG_DIR, filename)
        if os.path.exists(file_path):
            messages.error(request, "File already exists.")
            return redirect('tag_config_list')
            
        try:
            with open(file_path, 'w') as f:
                f.write(DEFAULT_CSV_HEADER)
            messages.success(request, f"File '{filename}' created.")
            return redirect('edit_tag_file', filename=filename)
        except Exception as e:
            messages.error(request, f"Failed to create file: {str(e)}")
    return redirect('tag_config_list')

def upload_tag_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        file_path = os.path.join(TAG_DIR, uploaded_file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        messages.success(request, f"File '{uploaded_file.name}' uploaded.")
    return redirect('tag_config_list')

def edit_tag_file(request, filename):
    file_path = os.path.join(TAG_DIR, filename)
    if request.method == 'POST':
        content = request.POST.get('content')
        with open(file_path, 'w') as f:
            f.write(content)
        messages.success(request, f"File '{filename}' saved.")
        return redirect('tag_config_list')
    with open(file_path, 'r') as f:
        content = f.read()
    return render(request, 'monitoring/edit_file.html', {'filename': filename, 'content': content})

def delete_tag_file(request, filename):
    file_path = os.path.join(TAG_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        messages.success(request, f"File '{filename}' deleted.")
    return redirect('tag_config_list')

# --- SYSTEM CONTROLS ---

def sync_tags(request):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        collector_dir = os.path.join(os.path.dirname(base_dir), 'collector')
        script_path = os.path.join(collector_dir, 'import_csv_tags.py')
        python_exe = get_python_executable()
        result = subprocess.run([python_exe, script_path], capture_output=True, text=True, cwd=collector_dir)
        messages.success(request, "Sync Successful!") if result.returncode == 0 else messages.error(request, "Sync Failed")
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    return redirect('dashboard')

def start_collector(request):
    if get_collector_process():
        messages.warning(request, "Already running.")
        return redirect('dashboard')
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        collector_dir = os.path.join(os.path.dirname(base_dir), 'collector')
        script_path = os.path.join(collector_dir, 'main.py')
        python_exe = get_python_executable()
        subprocess.Popen([python_exe, script_path], cwd=collector_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        messages.success(request, "Connection started.")
    except Exception as e:
        messages.error(request, f"Failed: {str(e)}")
    return redirect('dashboard')

def stop_collector(request):
    proc = get_collector_process()
    if proc:
        proc.terminate()
        messages.success(request, "Disconnected.")
    return redirect('dashboard')

def view_log(request):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        collector_dir = os.path.join(os.path.dirname(base_dir), 'collector')
        log_path = os.path.join(collector_dir, 'collector.log')
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                messages.info(request, f"--- Collector Log ---\n{''.join(f.readlines()[-30:])}")
    except Exception as e:
        messages.error(request, f"Read failed: {str(e)}")
    return redirect('dashboard')

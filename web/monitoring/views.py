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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAG_DIR = os.path.join(BASE_DIR, 'collector', 'Tag')
ENV_PATH = os.path.join(BASE_DIR, '.env')
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

# --- ENV CONFIGURATION ---

def edit_env(request):
    if request.method == 'POST':
        new_values = {
            'OPC_SERVER_URL': request.POST.get('OPC_SERVER_URL'),
            'POLLING_INTERVAL': request.POST.get('POLLING_INTERVAL'),
            'OPC_USER': request.POST.get('OPC_USER'),
            'OPC_PASSWORD': request.POST.get('OPC_PASSWORD'),
            'DB_TYPE': request.POST.get('DB_TYPE'),
            'DB_SQLITE_PATH': request.POST.get('DB_SQLITE_PATH'),
            'DB_NAME': request.POST.get('DB_NAME'),
            'DB_USER': request.POST.get('DB_USER'),
            'DB_PASSWORD': request.POST.get('DB_PASSWORD'),
            'DB_HOST': request.POST.get('DB_HOST'),
            'DB_PORT': request.POST.get('DB_PORT'),
        }
        
        lines = []
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, 'r') as f:
                lines = f.readlines()
        
        updated_lines = []
        seen_keys = set()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key = stripped.split('=')[0]
                if key in new_values:
                    updated_lines.append(f"{key}={new_values[key]}\n")
                    seen_keys.add(key)
                    continue
            updated_lines.append(line)
            
        for key, val in new_values.items():
            if key not in seen_keys and val: # Add if not seen and not empty
                updated_lines.append(f"{key}={val}\n")
                
        with open(ENV_PATH, 'w') as f:
            f.writelines(updated_lines)
            
        messages.success(request, "Configuration updated successfully!")
        return redirect('edit_env')

    env_data = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '=' in stripped:
                    parts = stripped.split('=', 1)
                    if len(parts) == 2:
                        env_data[parts[0]] = parts[1]
                    
    return render(request, 'monitoring/edit_env.html', {'env': env_data})

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
    return render(request, 'monitoring/tag_config.html', {'files': files})

def create_tag_file(request):
    if request.method == 'POST':
        filename = request.POST.get('filename', '').strip()
        if not filename:
            messages.error(request, "Filename is required.")
            return redirect('tag_config_list')
        if not filename.endswith('.csv'): filename += '.csv'
        file_path = os.path.join(TAG_DIR, filename)
        if os.path.exists(file_path):
            messages.error(request, "File already exists.")
            return redirect('tag_config_list')
        try:
            with open(file_path, 'w') as f: f.write(DEFAULT_CSV_HEADER)
            messages.success(request, f"File '{filename}' created.")
            return redirect('edit_tag_file', filename=filename)
        except Exception as e: messages.error(request, f"Failed: {str(e)}")
    return redirect('tag_config_list')

def upload_tag_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        file_path = os.path.join(TAG_DIR, uploaded_file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks(): destination.write(chunk)
        messages.success(request, f"File '{uploaded_file.name}' uploaded.")
    return redirect('tag_config_list')

def edit_tag_file(request, filename):
    file_path = os.path.join(TAG_DIR, filename)
    if request.method == 'POST':
        content = request.POST.get('content')
        with open(file_path, 'w') as f: f.write(content)
        messages.success(request, f"File '{filename}' saved.")
        return redirect('tag_config_list')
    with open(file_path, 'r') as f: content = f.read()
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
        collector_dir = os.path.join(BASE_DIR, 'collector')
        script_path = os.path.join(collector_dir, 'import_csv_tags.py')
        python_exe = get_python_executable()
        result = subprocess.run([python_exe, script_path], capture_output=True, text=True, cwd=collector_dir)
        messages.success(request, "Sync Successful!") if result.returncode == 0 else messages.error(request, f"Sync Failed: {result.stderr}")
    except Exception as e: messages.error(request, f"Error: {str(e)}")
    return redirect('dashboard')

def start_collector(request):
    if get_collector_process():
        messages.warning(request, "Already running.")
        return redirect('dashboard')
    try:
        collector_dir = os.path.join(BASE_DIR, 'collector')
        script_path = os.path.join(collector_dir, 'main.py')
        python_exe = get_python_executable()
        subprocess.Popen([python_exe, script_path], cwd=collector_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        messages.success(request, "Connection started.")
    except Exception as e: messages.error(request, f"Failed: {str(e)}")
    return redirect('dashboard')

def stop_collector(request):
    proc = get_collector_process()
    if proc:
        proc.terminate()
        messages.success(request, "Disconnected.")
    return redirect('dashboard')

def view_log(request):
    try:
        collector_dir = os.path.join(BASE_DIR, 'collector')
        log_path = os.path.join(collector_dir, 'collector.log')
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                messages.info(request, f"--- Collector Log ---\n{''.join(f.readlines()[-30:])}")
    except Exception as e: messages.error(request, f"Read failed: {str(e)}")
    return redirect('dashboard')

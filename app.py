import os
import sys
import csv
import json
import logging
import time
import urllib.request
import urllib.error
import tempfile
from flask import Flask, render_template, jsonify, request

# pythonw.exe での起動時に標準出力・エラー出力を無効化
if sys.executable.endswith("pythonw.exe"):
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

# ブラウザキャッシュ無効化
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')
PROJECTS_DIR = os.path.join(DATA_DIR, 'projects')
COMMON_DIR = os.path.join(DATA_DIR, 'common')

def get_project_dir(project_name):
    project_name = project_name or 'Sample'
    p_dir = os.path.join(PROJECTS_DIR, project_name)
    os.makedirs(p_dir, exist_ok=True)
    return p_dir

def read_csv_as_dicts(filepath):
    if not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_dicts_to_csv(filepath, fieldnames, data):
    dir_path = os.path.dirname(filepath)
    if dir_path: os.makedirs(dir_path, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

@app.route('/')
def index():
    prompt_path = os.path.join(COMMON_DIR, 'prompt_system.txt')
    default_prompt = ""
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            default_prompt = f.read()
    return render_template('index.html', ts=int(time.time()), default_system_prompt=default_prompt)

@app.route('/master_editor')
def master_editor():
    return render_template('master_editor.html', ts=int(time.time()))

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    return jsonify({"status": "ok"})

@app.route('/api/projects', methods=['GET'])
def get_projects():
    if not os.path.exists(PROJECTS_DIR): os.makedirs(os.path.join(PROJECTS_DIR, 'Sample'), exist_ok=True)
    return jsonify([d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))] or ['Sample'])

@app.route('/api/masters', methods=['GET'])
def get_masters():
    p_dir = get_project_dir(request.args.get('project', 'Sample'))
    return jsonify({
        'release': read_csv_as_dicts(os.path.join(p_dir, 'm_release.csv')),
        'character': read_csv_as_dicts(os.path.join(p_dir, 'm_character.csv')),
        'section': read_csv_as_dicts(os.path.join(p_dir, 'm_section.csv')),
        'member': read_csv_as_dicts(os.path.join(p_dir, 'm_member.csv')),
        'status': read_csv_as_dicts(os.path.join(p_dir, 'm_status.csv')),
        'task_template': read_csv_as_dicts(os.path.join(p_dir, 'm_task_template.csv')),
        'holiday': read_csv_as_dicts(os.path.join(p_dir, 'm_holiday.csv'))
    })

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    p_dir = get_project_dir(request.args.get('project', 'Sample'))
    tasks = []
    for f in [os.path.join(p_dir, x) for x in os.listdir(p_dir) if x.startswith('t_tasks_') and x.endswith('.csv')]:
        tasks.extend(read_csv_as_dicts(f))
    return jsonify(tasks)

@app.route('/api/tasks/save', methods=['POST'])
def save_tasks():
    try:
        p_dir = get_project_dir(request.args.get('project', 'Sample'))
        data = request.json
        fieldnames = ['task_id', 'release_id', 'char_id', 'section_id', 'task_name', 'member_id', 'start_date', 'end_date', 'progress', 'lane', 'dependencies', 'status_id']
        tasks_by_section = {}
        for task in data:
            for field in fieldnames:
                if field not in task: task[field] = ''
            sec_id = task.get('section_id')
            if sec_id not in tasks_by_section: tasks_by_section[sec_id] = []
            tasks_by_section[sec_id].append(task)
        for sec_id, tasks in tasks_by_section.items():
            write_dicts_to_csv(os.path.join(p_dir, f't_tasks_{sec_id}.csv'), fieldnames, tasks)
        return jsonify({'status': 'success'})
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/deadlines', methods=['GET'])
def get_deadlines():
    p_dir = get_project_dir(request.args.get('project', 'Sample'))
    return jsonify(read_csv_as_dicts(os.path.join(p_dir, 't_section_deadlines.csv')))

@app.route('/api/deadlines/save', methods=['POST'])
def save_deadlines():
    try:
        p_dir = get_project_dir(request.args.get('project', 'Sample'))
        write_dicts_to_csv(os.path.join(p_dir, 't_section_deadlines.csv'), ['release_id', 'char_id', 'section_id', 'deadline_date'], request.json)
        return jsonify({'status': 'success'})
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/annotations', methods=['GET'])
def get_annotations():
    p_dir = get_project_dir(request.args.get('project', 'Sample'))
    return jsonify(read_csv_as_dicts(os.path.join(p_dir, 't_annotations.csv')))

@app.route('/api/annotations/save', methods=['POST'])
def save_annotations():
    try:
        p_dir = get_project_dir(request.args.get('project', 'Sample'))
        data = request.json
        fieldnames = ['id', 'release_id', 'start_date', 'end_date', 'start_lane_id', 'end_lane_id', 'color', 'border_width', 'comment', 'position']
        for row in data:
            for field in fieldnames:
                if field not in row: row[field] = ''
        write_dicts_to_csv(os.path.join(p_dir, 't_annotations.csv'), fieldnames, data)
        return jsonify({'status': 'success'})
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/masters/save', methods=['POST'])
def save_masters():
    try:
        p_dir = get_project_dir(request.args.get('project', 'Sample'))
        data = request.json
        master_files = {
            'release': ('m_release.csv', ['release_id', 'release_name', 'art_deadline', 'branch_deadline', 'release_date', 'event_name']),
            'character': ('m_character.csv', ['char_id', 'char_name', 'costume_name', 'category', 'usage', 'event_id']),
            'section': ('m_section.csv', ['section_id', 'section_name', 'color', 'text_color']),
            'member': ('m_member.csv', ['member_id', 'member_name', 'display_name', 'section_id', 'bg_color', 'text_color']),
            'status': ('m_status.csv', ['status_id', 'status_name', 'color']),
            'task_template': ('m_task_template.csv', ['template_id', 'section_id', 'task_name', 'default_days']),
            'holiday': ('m_holiday.csv', ['holiday_date', 'holiday_name', 'holiday_type'])
        }
        
        # 単一マスタ形式 { master_type: 'xxx', data: [...] } に対応
        if isinstance(data, dict) and 'master_type' in data and 'data' in data:
            m_type = data['master_type']
            if m_type in master_files:
                fn, flds = master_files[m_type]
                write_dicts_to_csv(os.path.join(p_dir, fn), flds, data['data'])
                return jsonify({'status': 'success'})
        
        # 複数マスタ一括形式 { 'release': [...], 'character': [...] } に対応
        if isinstance(data, dict):
            for key, records in data.items():
                if key in master_files:
                    fn, flds = master_files[key]
                    write_dicts_to_csv(os.path.join(p_dir, fn), flds, records)
        return jsonify({'status': 'success'})
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def settings_api():
    filepath = os.path.join(COMMON_DIR, 'user_settings.json')
    if request.method == 'GET':
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f: return jsonify(json.load(f))
        return jsonify({})
    else:
        data = request.json
        existing = {}
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try: existing = json.load(f)
                except: pass
        existing.update(data)
        os.makedirs(COMMON_DIR, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(existing, f, ensure_ascii=False, indent=2)
        return jsonify({'status': 'success'})

@app.route('/api/restart', methods=['POST'])
def restart_server():
    if os.path.exists('WBSツール起動.bat'): os.system('start "" "WBSツール起動.bat"')
    os._exit(0)
    return jsonify({"status": "ok"})

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    os._exit(0)
    return jsonify({"status": "ok"})

@app.route('/api/llm/pricing', methods=['GET'])
def get_pricing():
    filepath = os.path.join(COMMON_DIR, 'm_llm_pricing.csv')
    return jsonify({"status": "success", "pricing": read_csv_as_dicts(filepath)})

if __name__ == '__main__':
    PORT = 55555
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        import threading, webbrowser
        def open_browser():
            time.sleep(1.5)
            webbrowser.open(f'http://127.0.0.1:{PORT}/')
        threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=PORT, debug=True, use_reloader=False, threaded=True)

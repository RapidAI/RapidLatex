#!/usr/bin/env python
"""
MathTranslate API Server
Provides REST API for document translation functionality
"""

import os
import uuid
import json
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import shutil
import zipfile
import tarfile
import gzip

# Import translation modules
from translate_arxiv import (
    process_local_archive,
    translate_dir,
    download_source_with_cache,
    zipdir,
    fallback_compile,
    loop_files
)
from translate import translate_single_tex_file
from config import config

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'api_output'
ALLOWED_EXTENSIONS = {'tex', 'pdf', 'zip', 'tar', 'gz', 'bz2', 'xz'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Task management
tasks = {}
task_lock = threading.Lock()

class TaskStatus:
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_task_id():
    """Generate unique task ID"""
    return str(uuid.uuid4())

def update_task_status(task_id, status, message=None, progress=None, result=None):
    """Update task status"""
    with task_lock:
        if task_id in tasks:
            tasks[task_id]['status'] = status
            tasks[task_id]['updated_at'] = datetime.now().isoformat()
            if message:
                tasks[task_id]['message'] = message
            if progress is not None:
                tasks[task_id]['progress'] = progress
            if result:
                tasks[task_id]['result'] = result

class TranslationOptions:
    """Translation options class"""
    def __init__(self, **kwargs):
        self.engine = kwargs.get('engine', 'google')
        self.language_from = kwargs.get('language_from', 'en')
        self.language_to = kwargs.get('language_to', 'zh-CN')
        self.compile = kwargs.get('compile', True)
        self.nocache = kwargs.get('nocache', False)
        self.notranslate = kwargs.get('notranslate', False)

def process_translation_task(task_id, input_path, options):
    """Process translation task in background thread"""
    try:
        update_task_status(task_id, TaskStatus.PROCESSING, "Starting translation...", 0)

        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = os.path.join(temp_dir, f"task_{task_id}")
            os.makedirs(working_dir)

            # Extract archive if needed
            if input_path.endswith(('.zip', '.tar.gz', '.tar.bz2', '.tar.xz')):
                update_task_status(task_id, TaskStatus.PROCESSING, "Extracting archive...", 10)
                if not process_local_archive(input_path, working_dir):
                    raise Exception("Failed to extract archive")
            else:
                # Copy single file
                update_task_status(task_id, TaskStatus.PROCESSING, "Preparing files...", 10)
                filename = os.path.basename(input_path)
                shutil.copy2(input_path, os.path.join(working_dir, filename))

            # Find main LaTeX files and translate
            update_task_status(task_id, TaskStatus.PROCESSING, "Analyzing LaTeX structure...", 20)

            # Change to working directory
            original_cwd = os.getcwd()
            os.chdir(working_dir)

            try:
                # Translate directory
                update_task_status(task_id, TaskStatus.PROCESSING, "Translating documents...", 30)
                complete_texs = translate_dir(working_dir, options)

                if not complete_texs:
                    raise Exception("No complete LaTeX files found")

                # Perform translation
                for i, basename in enumerate(complete_texs):
                    update_task_status(
                        task_id,
                        TaskStatus.PROCESSING,
                        f"Translating {basename}.tex...",
                        30 + (50 * (i + 1) / len(complete_texs))
                    )

                    translate_single_tex_file(
                        f"{basename}.tex",
                        f"{basename}.tex",
                        options.engine,
                        options.language_to,
                        options.language_from,
                        debug=False,
                        nocache=options.nocache,
                        threads=1
                    )

                # Compile if requested
                output_files = []
                if options.compile and complete_texs:
                    update_task_status(task_id, TaskStatus.PROCESSING, "Compiling LaTeX...", 80)

                    main_tex = complete_texs[0]  # Use first complete tex as main
                    try:
                        fallback_compile(f"{main_tex}.tex", working_dir)

                        # Find generated PDF
                        pdf_files = [f for f in loop_files(working_dir) if f.endswith('.pdf')]
                        for pdf_file in pdf_files:
                            output_filename = os.path.basename(pdf_file)
                            output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{task_id}_{output_filename}")
                            shutil.copy2(pdf_file, output_path)
                            output_files.append({
                                'type': 'pdf',
                                'filename': output_filename,
                                'path': f"{task_id}_{output_filename}"
                            })
                    except Exception as e:
                        print(f"Compilation failed: {e}")

                # Create output zip
                update_task_status(task_id, TaskStatus.PROCESSING, "Creating output package...", 90)
                output_zip = os.path.join(app.config['OUTPUT_FOLDER'], f"{task_id}.zip")
                zipdir(working_dir, output_zip)

                output_files.append({
                    'type': 'zip',
                    'filename': f"{task_id}.zip",
                    'path': f"{task_id}.zip"
                })

                # Task completed
                update_task_status(task_id, TaskStatus.COMPLETED, "Translation completed successfully!", 100, {
                    'files': output_files,
                    'translated_files': complete_texs
                })

            finally:
                os.chdir(original_cwd)

    except Exception as e:
        update_task_status(task_id, TaskStatus.FAILED, f"Translation failed: {str(e)}")
        print(f"Task {task_id} failed: {e}")

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/engines', methods=['GET'])
def get_engines():
    """Get available translation engines"""
    engines = ['google', 'tencent', 'tencentcloud', 'openai']

    # Add engine-specific information
    engine_info = {
        'google': {'name': 'Google Translate', 'description': 'Free Google translation service'},
        'tencent': {'name': 'Tencent Cloud', 'description': 'Tencent Cloud translation service'},
        'tencentcloud': {'name': 'Tencent Cloud', 'description': 'Tencent Cloud translation service'},
        'openai': {'name': 'OpenAI', 'description': 'OpenAI GPT translation service'}
    }

    return jsonify({
        'engines': [
            {
                'id': engine,
                'name': engine_info[engine]['name'],
                'description': engine_info[engine]['description']
            }
            for engine in engines
        ]
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file for translation"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Create task ID
    task_id = create_task_id()

    # Save uploaded file
    filename = secure_filename(file.filename)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
    file.save(upload_path)

    # Create task record
    with task_lock:
        tasks[task_id] = {
            'id': task_id,
            'status': TaskStatus.PENDING,
            'message': 'File uploaded, waiting to start translation...',
            'progress': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'input_filename': filename,
            'input_path': upload_path,
            'result': None
        }

    return jsonify({
        'task_id': task_id,
        'message': 'File uploaded successfully',
        'filename': filename
    })

@app.route('/api/arxiv/<arxiv_id>', methods=['POST'])
def translate_arxiv(arxiv_id):
    """Translate arxiv paper by ID"""
    # Create task ID
    task_id = create_task_id()

    # Get options from request
    data = request.get_json() or {}
    options = TranslationOptions(**data)

    # Create task record
    with task_lock:
        tasks[task_id] = {
            'id': task_id,
            'status': TaskStatus.PENDING,
            'message': 'ArXiv translation task created, waiting to start...',
            'progress': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'arxiv_id': arxiv_id,
            'options': vars(options),
            'result': None
        }

    # Start background task
    def arxiv_task():
        try:
            update_task_status(task_id, TaskStatus.PROCESSING, "Downloading from ArXiv...", 5)

            # Download arxiv paper
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = os.path.join(temp_dir, f"{arxiv_id}.tar.gz")
                download_source_with_cache(arxiv_id, download_path)

                # Process as local archive
                process_translation_task(task_id, download_path, options)

        except Exception as e:
            update_task_status(task_id, TaskStatus.FAILED, f"ArXiv download failed: {str(e)}")

    thread = threading.Thread(target=arxiv_task)
    thread.daemon = True
    thread.start()

    return jsonify({
        'task_id': task_id,
        'message': f'ArXiv translation task created for {arxiv_id}',
        'arxiv_id': arxiv_id
    })

@app.route('/api/translate/<task_id>', methods=['POST'])
def start_translation(task_id):
    """Start translation task for uploaded file"""
    with task_lock:
        if task_id not in tasks:
            return jsonify({'error': 'Task not found'}), 404

        task = tasks[task_id]
        if task['status'] != TaskStatus.PENDING:
            return jsonify({'error': 'Task already processed or in progress'}), 400

    # Get options from request
    data = request.get_json() or {}
    options = TranslationOptions(**data)

    # Update task with options
    task['options'] = vars(options)

    # Start background translation task
    thread = threading.Thread(
        target=process_translation_task,
        args=(task_id, task['input_path'], options)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'task_id': task_id,
        'message': 'Translation started',
        'options': vars(options)
    })

@app.route('/api/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get task status"""
    with task_lock:
        if task_id not in tasks:
            return jsonify({'error': 'Task not found'}), 404

        task = tasks[task_id].copy()
        # Remove sensitive information
        task.pop('input_path', None)

        return jsonify(task)

@app.route('/api/download/<task_id>/<filename>', methods=['GET'])
def download_file(task_id, filename):
    """Download translated file"""
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    # Check if file belongs to task (basic security)
    if not filename.startswith(f"{task_id}_") and filename != f"{task_id}.zip":
        return jsonify({'error': 'Access denied'}), 403

    return send_file(file_path, as_attachment=True)

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """List all tasks"""
    with task_lock:
        task_list = []
        for task_id, task in tasks.items():
            task_copy = task.copy()
            task_copy.pop('input_path', None)
            task_list.append(task_copy)

        # Sort by creation time (newest first)
        task_list.sort(key=lambda x: x['created_at'], reverse=True)

        return jsonify({
            'tasks': task_list,
            'total': len(task_list)
        })

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete task and associated files"""
    with task_lock:
        if task_id not in tasks:
            return jsonify({'error': 'Task not found'}), 404

        # Delete task
        del tasks[task_id]

    # Delete associated files
    try:
        # Delete uploaded file
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.startswith(f"{task_id}_"):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Delete output files
        for filename in os.listdir(app.config['OUTPUT_FOLDER']):
            if filename.startswith(f"{task_id}_"):
                os.remove(os.path.join(app.config['OUTPUT_FOLDER'], filename))

    except Exception as e:
        print(f"Error deleting files for task {task_id}: {e}")

    return jsonify({'message': 'Task deleted successfully'})

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 100MB'}), 413

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("MathTranslate API Server Starting...")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Output folder: {app.config['OUTPUT_FOLDER']}")
    print("Available endpoints:")
    print("  GET  /api/health - Health check")
    print("  GET  /api/engines - List translation engines")
    print("  POST /api/upload - Upload file")
    print("  POST /api/arxiv/<id> - Translate ArXiv paper")
    print("  POST /api/translate/<task_id> - Start translation")
    print("  GET  /api/status/<task_id> - Get task status")
    print("  GET  /api/download/<task_id>/<filename> - Download file")
    print("  GET  /api/tasks - List all tasks")
    print("  DELETE /api/tasks/<task_id> - Delete task")

    app.run(host='0.0.0.0', port=5000, debug=True)
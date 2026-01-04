"""
Flask web application for LEGO Set to STL converter.
Provides web interface for converting LEGO sets to 3D-printable STL files.
"""

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import zipfile
from io import BytesIO
import threading
from datetime import datetime

from rebrickable import RebrickableClient
from metadata import MetadataHandler
from converter import STLConverter


app = Flask(__name__)
app.config['SECRET_KEY'] = 'lego-stl-converter-secret-key'
app.config['SETS_DIR'] = 'sets'

# Initialize modules
rebrickable_client = RebrickableClient()
metadata_handler = MetadataHandler()
stl_converter = STLConverter()

# Store processing status for sets
processing_status = {}


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/api/validate/<set_number>')
def validate_set(set_number):
    """
    Validate if a LEGO set exists.
    
    Args:
        set_number: The LEGO set number (e.g., "10245")
        
    Returns:
        JSON with validation result
    """
    # Check if already processed
    if metadata_handler.set_exists(set_number):
        return jsonify({
            'valid': True,
            'exists': True,
            'message': f'Set {set_number} has already been processed'
        })
    
    # Validate with Rebrickable
    metadata = rebrickable_client.validate_set(set_number)
    
    if metadata:
        return jsonify({
            'valid': True,
            'exists': False,
            'set_name': metadata.get('name', 'Unknown'),
            'message': f'Set {set_number} found and ready to process'
        })
    else:
        return jsonify({
            'valid': False,
            'exists': False,
            'message': f'Set {set_number} not found'
        }), 404


@app.route('/api/process/<set_number>', methods=['POST'])
def process_set(set_number):
    """
    Process a LEGO set: fetch data, create metadata, convert to STL.
    
    Args:
        set_number: The LEGO set number
        
    Returns:
        JSON with processing result
    """
    # Check if already processed
    if metadata_handler.set_exists(set_number):
        return jsonify({
            'success': False,
            'message': f'Set {set_number} has already been processed',
            'redirect': f'/set/{set_number}'
        })
    
    # Check if already processing
    if set_number in processing_status and processing_status[set_number]['status'] == 'processing':
        return jsonify({
            'success': False,
            'message': f'Set {set_number} is already being processed'
        })
    
    # Initialize processing status
    processing_status[set_number] = {
        'status': 'processing',
        'progress': 0,
        'message': 'Starting...',
        'started_at': datetime.now().isoformat()
    }
    
    # Process in background thread
    thread = threading.Thread(
        target=process_set_background,
        args=(set_number,)
    )
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Processing set {set_number} started',
        'status_url': f'/api/status/{set_number}'
    })


def process_set_background(set_number: str):
    """
    Background task to process a set.
    
    Args:
        set_number: The LEGO set number
    """
    try:
        # Update status
        processing_status[set_number]['message'] = 'Fetching set data from Rebrickable...'
        processing_status[set_number]['progress'] = 10
        
        # Step 1: Fetch data from Rebrickable
        data = rebrickable_client.fetch_set_data(set_number)
        
        if not data:
            processing_status[set_number]['status'] = 'failed'
            processing_status[set_number]['message'] = 'Failed to fetch set data'
            return
        
        # Update status
        processing_status[set_number]['message'] = 'Creating metadata file...'
        processing_status[set_number]['progress'] = 30
        
        # Step 2: Create metadata
        success = metadata_handler.create_set_metadata(
            set_number,
            data['metadata'],
            data['parts']
        )
        
        if not success:
            processing_status[set_number]['status'] = 'failed'
            processing_status[set_number]['message'] = 'Failed to create metadata'
            return
        
        # Update status
        processing_status[set_number]['message'] = 'Converting parts to STL...'
        processing_status[set_number]['progress'] = 50
        
        # Step 3: Convert parts to STL
        metadata = metadata_handler.load_set_metadata(set_number)
        stats = stl_converter.convert_set(set_number, metadata['parts'])
        
        # Update final status
        processing_status[set_number]['status'] = 'completed'
        processing_status[set_number]['progress'] = 100
        processing_status[set_number]['message'] = f'Completed! Converted {stats["converted"]} parts'
        processing_status[set_number]['stats'] = stats
        processing_status[set_number]['completed_at'] = datetime.now().isoformat()
        
    except Exception as e:
        processing_status[set_number]['status'] = 'failed'
        processing_status[set_number]['message'] = f'Error: {str(e)}'
        print(f"Error processing set {set_number}: {e}")


@app.route('/api/status/<set_number>')
def get_status(set_number):
    """
    Get processing status for a set.
    
    Args:
        set_number: The LEGO set number
        
    Returns:
        JSON with current status
    """
    if set_number in processing_status:
        return jsonify(processing_status[set_number])
    else:
        return jsonify({
            'status': 'unknown',
            'message': 'No processing information available'
        })


@app.route('/set/<set_number>')
def view_set(set_number):
    """
    View a processed set with all parts and download options.
    
    Args:
        set_number: The LEGO set number
        
    Returns:
        Rendered template with set information
    """
    metadata = metadata_handler.load_set_metadata(set_number)
    
    if not metadata:
        return render_template('error.html', message=f'Set {set_number} not found'), 404
    
    # Check which STL files exist
    for part in metadata['parts']:
        part['stl_exists'] = stl_converter.stl_exists(set_number, part['part_num'])
    
    return render_template('set.html', set_data=metadata)


@app.route('/download/<set_number>/<part_number>')
def download_part(set_number, part_number):
    """
    Download a single STL file.
    
    Args:
        set_number: The LEGO set number
        part_number: The part number
        
    Returns:
        STL file download
    """
    stl_path = stl_converter.get_stl_path(set_number, part_number)
    
    if not os.path.exists(stl_path):
        return jsonify({'error': 'STL file not found'}), 404
    
    return send_file(
        stl_path,
        as_attachment=True,
        download_name=f'{set_number}_{part_number}.stl'
    )


@app.route('/download/<set_number>/zip')
def download_set_zip(set_number):
    """
    Download all STL files for a set as a ZIP archive.
    
    Args:
        set_number: The LEGO set number
        
    Returns:
        ZIP file download
    """
    metadata = metadata_handler.load_set_metadata(set_number)
    
    if not metadata:
        return jsonify({'error': 'Set not found'}), 404
    
    # Create ZIP file in memory
    memory_file = BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add .set.json metadata
        json_path = os.path.join(app.config['SETS_DIR'], set_number, '.set.json')
        zf.write(json_path, f'{set_number}/.set.json')
        
        # Add all STL files
        stl_dir = os.path.join(app.config['SETS_DIR'], set_number, 'stls')
        
        if os.path.exists(stl_dir):
            for filename in os.listdir(stl_dir):
                if filename.endswith('.stl'):
                    file_path = os.path.join(stl_dir, filename)
                    zf.write(file_path, f'{set_number}/stls/{filename}')
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{set_number}_stls.zip'
    )


@app.route('/api/sets')
def list_sets():
    """
    List all processed sets.
    
    Returns:
        JSON with list of sets
    """
    sets = []
    sets_dir = app.config['SETS_DIR']
    
    if os.path.exists(sets_dir):
        for set_number in os.listdir(sets_dir):
            metadata = metadata_handler.load_set_metadata(set_number)
            if metadata:
                sets.append({
                    'set_number': set_number,
                    'name': metadata['name'],
                    'total_parts': metadata['total_parts'],
                    'unique_parts': metadata['unique_parts']
                })
    
    return jsonify({'sets': sets})


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', message='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('error.html', message='Internal server error'), 500


if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(app.config['SETS_DIR'], exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    print("\n" + "="*60)
    print("LEGO Set to STL Converter")
    print("="*60)
    print("\nStarting server at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

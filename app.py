"""
🎬 YouTube ডাউনলোডার - Python Flask ব্যাকএন্ড
ওয়েবসাইট ক্রিয়েটর: Robbany Bagha
"""

import os
import re
import json
import subprocess
from flask import Flask, request, jsonify, render_template, send_file, after_this_request
from flask_cors import CORS
import yt_dlp
import tempfile
import shutil

app = Flask(__name__)
CORS(app)

# কনফিগারেশন
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# =============================================
# 🔧 হেলপার ফাংশন
# =============================================

def extract_video_id(url):
    """YouTube URL থেকে ভিডিও আইডি বের করে"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([^&\n?#]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_duration(seconds):
    """সেকেন্ডকে মিনিট:সেকেন্ড ফরম্যাটে রূপান্তর"""
    if not seconds:
        return '0:00'
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

def format_file_size(bytes):
    """বাইটকে এমবি বা জিবি ফরম্যাটে রূপান্তর"""
    if not bytes:
        return 'N/A'
    if bytes < 1024 * 1024:
        return f"{bytes / 1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes / (1024 * 1024 * 1024):.2f} GB"

# =============================================
# 📥 ভিডিও তথ্য আনা
# =============================================

def get_video_info(url):
    """yt-dlp ব্যবহার করে ভিডিওর সব তথ্য আনে"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'ignoreerrors': True,
        'no_check_certificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return None
            
            # ফরম্যাট লিস্ট তৈরি
            formats = []
            seen_qualities = set()
            
            for f in info.get('formats', []):
                # ভিডিও+অডিও সম্বলিত ফরম্যাট
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    quality = f.get('format_note', '') or f.get('height', 'N/A')
                    if quality and quality not in seen_qualities:
                        seen_qualities.add(quality)
                        formats.append({
                            'format_id': str(f.get('format_id', '')),
                            'quality': str(quality),
                            'ext': f.get('ext', 'mp4'),
                            'filesize': format_file_size(f.get('filesize', 0)),
                            'filesize_bytes': f.get('filesize', 0),
                            'resolution': f.get('resolution', 'N/A'),
                            'url': f.get('url', '')
                        })
            
            # কোয়ালিটি অনুযায়ী সাজানো (উচ্চ থেকে নিম্ন)
            quality_order = {
                '2160p': 0, '4K': 1, '1440p': 2, '2K': 3,
                '1080p': 4, '1080': 5, '720p': 6, '720': 7,
                '480p': 8, '480': 9, '360p': 10, '360': 11,
                '240p': 12, '240': 13, '144p': 14, '144': 15
            }
            formats.sort(key=lambda x: quality_order.get(x['quality'], 999))
            
            return {
                'title': info.get('title', 'ভিডিও'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': format_duration(info.get('duration')),
                'duration_seconds': info.get('duration', 0),
                'view_count': f"{info.get('view_count', 0):,}",
                'uploader': info.get('uploader', 'অজানা'),
                'formats': formats
            }
            
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

# =============================================
# ⬇️ ভিডিও ডাউনলোড
# =============================================

def download_video(url, format_id=None):
    """ভিডিও ডাউনলোড করে ফাইল পাথ রিটার্ন করে"""
    temp_dir = tempfile.mkdtemp()
    
    # yt-dlp অপশন
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'no_check_certificate': True,
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }
    
    # ফরম্যাট সিলেক্ট
    if format_id:
        ydl_opts['format'] = f'{format_id}+bestaudio/best'
    else:
        ydl_opts['format'] = 'best[ext=mp4]+bestaudio/best'
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # ফাইল চেক
            if not os.path.exists(filename):
                # অন্য এক্সটেনশন চেক
                for ext in ['.mp4', '.webm', '.mkv']:
                    test_file = filename.rsplit('.', 1)[0] + ext
                    if os.path.exists(test_file):
                        filename = test_file
                        break
            
            # ফাইনাল ফাইল নাম তৈরি
            safe_title = re.sub(r'[^\w\s-]', '', info.get('title', 'video'))
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            final_filename = f"{safe_title}.mp4"
            final_path = os.path.join(DOWNLOAD_FOLDER, final_filename)
            
            # টেম্প থেকে মুভ
            shutil.move(filename, final_path)
            
            # টেম্প ফোল্ডার ক্লিন
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return final_path, final_filename
            
    except Exception as e:
        print(f"Download error: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e

# =============================================
# 🚀 API রাউট
# =============================================

@app.route('/')
def index():
    """হোম পেজ"""
    return render_template('index.html', creator="Robbany Bagha")

@app.route('/api/info', methods=['POST'])
def api_info():
    """ভিডিও তথ্য API"""
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL প্রদান করুন'}), 400
    
    # YouTube লিংক চেক
    if not extract_video_id(url):
        return jsonify({'error': 'সঠিক YouTube লিংক দিন'}), 400
    
    info = get_video_info(url)
    if not info:
        return jsonify({'error': 'ভিডিও তথ্য পাওয়া যায়নি'}), 404
    
    return jsonify(info)

@app.route('/api/download', methods=['POST'])
def api_download():
    """ভিডিও ডাউনলোড API"""
    data = request.get_json()
    url = data.get('url', '').strip()
    format_id = data.get('format_id', '')
    
    if not url:
        return jsonify({'error': 'URL প্রদান করুন'}), 400
    
    try:
        file_path, filename = download_video(url, format_id)
        
        @after_this_request
        def cleanup(response):
            """ডাউনলোড শেষে ফাইল ডিলিট"""
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            return response
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({'error': f'ডাউনলোড ব্যর্থ: {str(e)}'}), 500

@app.route('/api/health')
def health():
    """হেলথ চেক"""
    return jsonify({'status': 'ok', 'creator': 'Robbany Bagha'})

# =============================================
# 🏃‍♂️ সার্ভার রান
# =============================================

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════╗
    ║  🎬 YouTube ডাউনলোডার                  ║
    ║  👨‍💻 ক্রিয়েটর: Robbany Bagha           ║
    ║  🌐 http://localhost:5000               ║
    ╚══════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)

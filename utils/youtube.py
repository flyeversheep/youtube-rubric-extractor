"""
YouTube transcript downloader using yt-dlp
"""
import subprocess
import json
import re
from typing import Optional, List, Dict


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def download_transcript(url: str, languages: List[str] = None) -> Optional[str]:
    """
    Download transcript/captions from YouTube video
    
    Args:
        url: YouTube video URL
        languages: Preferred languages in order (default: ['en', 'en-US', 'en-GB'])
    
    Returns:
        Transcript text or None if not available
    """
    if languages is None:
        languages = ['en', 'en-US', 'en-GB']
    
    video_id = extract_video_id(url)
    
    # Try auto-generated subtitles first, then manual
    for lang in languages:
        # Try auto-generated
        result = _try_download(url, lang, auto=True)
        if result:
            return result
        
        # Try manual captions
        result = _try_download(url, lang, auto=False)
        if result:
            return result
    
    # If no captions, try to get video info for title/description
    return _get_video_info_fallback(url)


def _try_download(url: str, lang: str, auto: bool = True) -> Optional[str]:
    """Attempt to download subtitles with specific language"""
    try:
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-subs' if not auto else '--write-auto-subs',
            '--sub-langs', lang,
            '--sub-format', 'json3',  # Structured format with timestamps
            '--print', '%(requested_subtitles.{}-{}.filepath)s'.format(lang, 'orig' if not auto else 'trans'),
            '-o', '/tmp/%(id)s.%(ext)s',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Parse the subtitle file path from output
            subtitle_path = result.stdout.strip().split('\n')[-1]
            if subtitle_path and subtitle_path.endswith('.json'):
                return _parse_json3_subtitles(subtitle_path)
                
    except Exception as e:
        print(f"Debug: Failed to download {lang} {'auto' if auto else 'manual'} subs: {e}")
    
    return None


def _parse_json3_subtitles(filepath: str) -> str:
    """Parse YouTube's JSON3 subtitle format into plain text with timestamps"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        segments = []
        for event in data.get('events', []):
            if 'segs' in event:
                text = ''.join(seg.get('utf8', '') for seg in event['segs'])
                if text.strip():
                    start_ms = event.get('tStartMs', 0)
                    start_time = _ms_to_timestamp(start_ms)
                    segments.append(f"[{start_time}] {text.strip()}")
        
        return '\n'.join(segments)
    except Exception as e:
        print(f"Debug: Failed to parse subtitles: {e}")
        return ""


def _ms_to_timestamp(ms: int) -> str:
    """Convert milliseconds to MM:SS format"""
    seconds = ms // 1000
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def _get_video_info_fallback(url: str) -> Optional[str]:
    """Get video title and description as fallback when no captions"""
    try:
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--print', '%(title)s\n%(description)s',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return f"# No transcript available\n\n{result.stdout}"
    except Exception:
        pass
    
    return None


def chunk_transcript(transcript: str, chunk_size: int = 3000, overlap: int = 500) -> List[str]:
    """
    Split transcript into overlapping chunks for LLM processing
    
    Args:
        transcript: Full transcript text
        chunk_size: Target size per chunk (characters)
        overlap: Overlap between chunks (characters)
    
    Returns:
        List of transcript chunks
    """
    if len(transcript) <= chunk_size:
        return [transcript]
    
    chunks = []
    start = 0
    
    while start < len(transcript):
        end = start + chunk_size
        
        # Try to end at a newline or sentence boundary
        if end < len(transcript):
            # Look for newline within last 200 chars
            newline_pos = transcript.rfind('\n', end - 200, end)
            if newline_pos != -1:
                end = newline_pos + 1
            else:
                # Look for sentence end
                sentence_end = transcript.rfind('. ', end - 200, end)
                if sentence_end != -1:
                    end = sentence_end + 2
        
        chunks.append(transcript[start:end].strip())
        start = end - overlap
    
    return chunks


def get_video_metadata(url: str) -> Dict:
    """Get video metadata (title, author, duration, etc.)"""
    try:
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--dump-json',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout.split('\n')[0])
            return {
                'title': data.get('title', 'Unknown'),
                'author': data.get('uploader', 'Unknown'),
                'duration': data.get('duration', 0),
                'upload_date': data.get('upload_date', 'Unknown'),
                'description': data.get('description', ''),
                'tags': data.get('tags', []),
                'url': url,
                'video_id': data.get('id', '')
            }
    except Exception as e:
        print(f"Debug: Failed to get metadata: {e}")
    
    return {'title': 'Unknown', 'author': 'Unknown', 'url': url}


if __name__ == '__main__':
    # Test
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print("Testing transcript download...")
    transcript = download_transcript(test_url)
    if transcript:
        print(f"Got {len(transcript)} characters")
        print("First 500 chars:")
        print(transcript[:500])
    else:
        print("No transcript available")

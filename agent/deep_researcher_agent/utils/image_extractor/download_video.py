import os
import argparse
import re
from yt_dlp import YoutubeDL

def clean_title(title):
    """
    Clean the video title by replacing all spaces and non-alphanumeric characters with underscores.
    """
    # Replace all non-alphanumeric characters (except for underscores) with underscores
    cleaned = re.sub(r'[^\w\d]', '_', title)
    # Replace consecutive underscores with a single underscore
    cleaned = re.sub(r'_+', '_', cleaned)
    # Remove leading/trailing underscores
    cleaned = cleaned.strip('_')
    return cleaned

def download_video(url, output_dir='.', cookies_file=None, cookies_browser=None, clean_filename=True):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    if clean_filename:
        # First extract info to get the title
        info_opts = {
            'verbose': True,
            'nocheckcertificate': True,
        }
        
        # Add cookies if provided
        if cookies_file:
            info_opts['cookiefile'] = cookies_file
        if cookies_browser:
            info_opts['cookiesfrombrowser'] = (cookies_browser,)
        
        # Extract video info to get the title
        with YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_title = info.get('title', 'video')
            clean_title_name = clean_title(raw_title)
        
        # Now download with clean filename
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=720][ext=mp4]',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(output_dir, f'{clean_title_name}.%(ext)s'),
            'verbose': True,
            'nocheckcertificate': True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        
        # Add cookies if provided
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file
        if cookies_browser:
            ydl_opts['cookiesfrombrowser'] = (cookies_browser,)
        
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    else:
        # Build an output template: <output_dir>/<video_title>.<ext>
        outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')
        # Add nocheckcertificate=True to skip SSL/TLS verification
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=720][ext=mp4]',
            'merge_output_format': 'mp4',
            'outtmpl': outtmpl,
            'verbose': True,
            'nocheckcertificate': True,
        }

        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file
        if cookies_browser:
            ydl_opts['cookiesfrombrowser'] = (cookies_browser,)

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

def main():
    parser = argparse.ArgumentParser(
        description="Download a YouTube video at 1080p/720p using yt-dlp with optional auth and no-cert-check."
    )
    parser.add_argument('url', help='Video URL to download')
    parser.add_argument('-o', '--output-dir', default='.',
                        help='Directory to save the downloaded video (default: current directory)')
    parser.add_argument('-c', '--cookies-file',
                        help='Path to a Netscape-format cookies.txt file')
    parser.add_argument('-cb', '--cookies-browser',
                        default = 'chrome',
                        help='Browser name for direct cookies extraction (e.g., firefox, chrome)')
    parser.add_argument('--clean-filename', default=True, type=bool,
                        help='Use cleaned filename')

    args = parser.parse_args()
    download_video(
        url=args.url,
        output_dir=args.output_dir,
        cookies_file=args.cookies_file,
        cookies_browser=args.cookies_browser,
        clean_filename=args.clean_filename
    )

if __name__ == '__main__':
    main()
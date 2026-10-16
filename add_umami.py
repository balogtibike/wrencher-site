"""
Run from D:\Zazzle\wrencherweb\
Adds Umami analytics script to all HTML pages and
adds data-umami-event="download-click" to all download buttons.
"""
import re
from pathlib import Path

UMAMI_TAG = '  <script defer src="https://cloud.umami.is/script.js" data-website-id="907d2de6-1e8d-4fe0-9528-f3a0af5a8998"></script>\n'

DOWNLOAD_URL = "WrencherSetup.exe"

files = list(Path('.').glob('*.html')) + list(Path('tools').glob('*.html'))

for f in files:
    content = f.read_text(encoding='utf-8')
    changed = False

    # 1. Add Umami script before </head> if not already present
    if 'cloud.umami.is' not in content:
        content = content.replace('</head>', UMAMI_TAG + '</head>', 1)
        changed = True

    # 2. Add data-umami-event to download buttons (links containing WrencherSetup.exe)
    if DOWNLOAD_URL in content and 'data-umami-event="download-click"' not in content:
        def add_event(m):
            tag = m.group(0)
            if 'data-umami-event' not in tag:
                tag = tag.replace('<a ', '<a data-umami-event="download-click" ', 1)
            return tag
        new_content = re.sub(
            r'<a [^>]*WrencherSetup\.exe[^>]*>',
            add_event,
            content
        )
        if new_content != content:
            content = new_content
            changed = True

    if changed:
        f.write_text(content, encoding='utf-8')
        print(f'updated: {f}')
    else:
        print(f'skip:    {f}')

print('\nDone.')
from pathlib import Path

tag = '  <script defer src="https://cdn.vercel-insights.com/v1/script.js"></script>\n'
files = list(Path('.').glob('*.html')) + list(Path('tools').glob('*.html'))

for f in files:
    content = f.read_text(encoding='utf-8')
    if 'vercel-insights' in content:
        print(f'skip: {f}')
        continue
    content = content.replace('</head>', tag + '</head>', 1)
    f.write_text(content, encoding='utf-8')
    print(f'updated: {f}')

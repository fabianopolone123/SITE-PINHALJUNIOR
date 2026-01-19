from pathlib import Path
from PyPDF2 import PdfReader
for path in Path('apostilas').glob('*.pdf'):
    reader = PdfReader(path)
    text = ''
    for page in reader.pages[:3]:
        text += page.extract_text() or ''
    print('#', path.name)
    print(text[:500].replace('\n',' '))
    print('---')

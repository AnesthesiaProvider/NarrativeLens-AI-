import urllib.request
import io
import json
from PIL import Image, ImageDraw

# Create image with text
img = Image.new('RGB', (600, 150), color=(255, 255, 255))
d = ImageDraw.Draw(img)
d.text((30, 60), 'WE MUST ATTACK AND DESTROY THEM ALL', fill=(0, 0, 0))
buf = io.BytesIO()
img.save(buf, format='JPEG')
img_bytes = buf.getvalue()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="image"; filename="test_meme.jpg"\r\n'
    f'Content-Type: image/jpeg\r\n\r\n'
).encode('utf-8') + img_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/analyze/meme',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
    method='POST'
)

with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode())
    print('HTTP', r.status)
    print('Extracted OCR:', data.get('ocr_text'))
    print('Classification:', json.dumps(data.get('classification'), indent=2))
    print('Vision results:', json.dumps(data.get('vision_results'), indent=2))

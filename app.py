from flask import Flask, render_template, request
import requests
import numpy as np
from PIL import Image
import io
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'static/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

palette = [
    (0, 0, 0), (128, 0, 0), (0, 128, 0), (0, 0, 128),
    (128, 128, 0), (128, 0, 128), (0, 128, 128), (255, 128, 0)
]

def colorize_mask(mask, palette):
    color_mask = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
    for class_idx, color in enumerate(palette):
        color_mask[mask == class_idx] = color
    return Image.fromarray(color_mask)

@app.route('/', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        file = request.files.get('image')
        if not file:
            return render_template('index.html', error="Aucun fichier choisi")
        try:
            image = Image.open(file)
            width, height = image.size
            left_half = image.crop((0, 0, width // 2, height))
            right_half = image.crop((width // 2, 0, width, height))
            left_filename = 'left_' + file.filename
            left_filepath = os.path.join(UPLOAD_FOLDER, left_filename)
            left_half.save(left_filepath)
            right_filename = 'right_' + file.filename
            right_filepath = os.path.join(UPLOAD_FOLDER, right_filename)
            right_half.save(right_filepath)
            left_half_bytes = io.BytesIO()
            left_half.save(left_half_bytes, format='JPEG')
            left_half_bytes.seek(0)
            files = {'image': left_half_bytes}

            # Appel à l'API interne (mettez `/segment` si dans le même service)
            response = requests.post('http://127.0.0.1:5000', files=files)

            if response.status_code != 200:
                return render_template('index.html', error="Erreur de segmentation")

            mask_data = response.json().get('mask')
            if not mask_data:
                return render_template('index.html', error="Masque non reçu")

            mask_array = np.array(mask_data, dtype=np.uint8)
            color_segmented_image = colorize_mask(mask_array, palette)
            segmented_filename = 'segmented_' + left_filename
            segmented_filepath = os.path.join(UPLOAD_FOLDER, segmented_filename)
            color_segmented_image.save(segmented_filepath)
            return render_template(
                'index.html',
                left_image_path=left_filename,
                right_image_path=right_filename,
                segmented_image_path=segmented_filename,
                error=None
            )
        except Exception as e:
            return render_template('index.html', error=f"Erreur : {str(e)}")
    return render_template('index.html', error=None)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))  # Pour Render
    app.run(host='0.0.0.0', port=port)

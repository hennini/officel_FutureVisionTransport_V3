from flask import Flask, render_template, request
import requests
import numpy as np
from PIL import Image
import io
import os



app = Flask(__name__)

# Chemin du dossier 'static/' pour stocker les images temporairement
UPLOAD_FOLDER = 'static/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Palette de couleurs pour chaque classe (exemple avec 8 classes)
palette = [
    (0, 0, 0),       # Classe 0 : noir (souvent pour l'arrière-plan)
    (128, 0, 0),     # Classe 1 : rouge
    (0, 128, 0),     # Classe 2 : vert
    (0, 0, 128),     # Classe 3 : bleu
    (128, 128, 0),   # Classe 4 : jaune
    (128, 0, 128),   # Classe 5 : violet
    (0, 128, 128),   # Classe 6 : cyan
    (255, 128, 0)    # Classe 7 : orange
]

def colorize_mask(mask, palette):
    """
    Convertit un masque de classe en une image en couleurs en utilisant la palette spécifiée.
    
    Parameters:
    - mask (numpy array): Masque de classes (grayscale).
    - palette (list of tuples): Palette de couleurs pour chaque classe.
    
    Returns:
    - Image colorisée en fonction des classes.
    """
    color_mask = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
    
    for class_idx, color in enumerate(palette):
        color_mask[mask == class_idx] = color
    
    return Image.fromarray(color_mask)

# Endpoint pour recevoir une image, obtenir le masque et afficher l'image segmentée
@app.route('/', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        file = request.files.get('image')  # Récupérer le fichier image

        if not file:
            return render_template('index.html', error="Aucun fichier choisi")

        try:
            # Charger l'image depuis le fichier
            image = Image.open(file)
            width, height = image.size

            # Diviser l'image en moitiés gauche et droite
            left_half = image.crop((0, 0, width // 2, height))
            right_half = image.crop((width // 2, 0, width, height))

            # Enregistrer les moitiés dans le dossier 'static/'
            left_filename = 'left_' + file.filename
            left_filepath = os.path.join(UPLOAD_FOLDER, left_filename)
            left_half.save(left_filepath)

            right_filename = 'right_' + file.filename
            right_filepath = os.path.join(UPLOAD_FOLDER, right_filename)
            right_half.save(right_filepath)

            # Envoyer la moitié gauche à l'API de segmentation
            left_half_bytes = io.BytesIO()
            left_half.save(left_half_bytes, format='JPEG')
            left_half_bytes.seek(0)  # Remettre le pointeur au début pour la lecture
            files = {'image': left_half_bytes}
            response = requests.post('http://127.0.0.1:5000/segment', files=files)
            #response = requests.post('/segment', files=files)

            # Vérifier que la réponse de l'API contient le masque
            if response.status_code != 200:
                return render_template('index.html', error="Erreur de segmentation")

            mask_data = response.json().get('mask')
            if not mask_data:
                return render_template('index.html', error="Masque non reçu")

            # Créer une image segmentée colorée à partir du masque reçu
            mask_array = np.array(mask_data, dtype=np.uint8)
            color_segmented_image = colorize_mask(mask_array, palette)

            # Sauvegarder l'image segmentée colorisée
            segmented_filename = 'segmented_' + left_filename
            segmented_filepath = os.path.join(UPLOAD_FOLDER, segmented_filename)
            color_segmented_image.save(segmented_filepath)

            # Passer les chemins des moitiés et de l'image segmentée au template HTML
            return render_template(
                'index.html',
                left_image_path=left_filename,
                right_image_path=right_filename,
                segmented_image_path=segmented_filename,
                error=None
            )
        except Exception as e:
            # Gérer les erreurs éventuelles
            return render_template('index.html', error=f"Erreur : {str(e)}")

    return render_template('index.html', error=None)

if __name__ == '__main__':
    app.run(port=8000, debug=True)

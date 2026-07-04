"""
Visual Data Processor
---------------------
Reprocesses images to extract face count and brightness.
Uses OpenCV Haar Cascade for face detection.
"""

import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import cv2
import numpy as np
import urllib.request
from app import db_connection
import pandas as pd


def extrair_features_visuais(url):
    """Extract visual features (faces, brightness) from an image URL."""
    try:
        req = urllib.request.urlopen(url, timeout=5)
        arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img is None:
            return 0, 127

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=8,
            minSize=(40, 40)
        )
        n_rostos = len(faces)
        brilho = int(np.mean(gray))

        return n_rostos, brilho
    except:
        return 0, 127


def processar_dataset_existente():
    """Reprocess all images in the database."""
    print("Fetching all images for reanalysis...")

    with db_connection.get_connection() as conn:
        query = """
            SELECT Post_ID_Social, Link_Imagem 
            FROM Dataset_Social_Real 
            WHERE Link_Imagem IS NOT NULL AND Link_Imagem != ''
        """
        df = pd.read_sql(query, conn)

    print(f"{len(df)} images ready for reanalysis.")

    for index, row in df.iterrows():
        url_img = row['Link_Imagem']
        post_id = str(row['Post_ID_Social']).replace('.0', '').strip()

        rostos, brilho = extrair_features_visuais(url_img)
        db_connection.execute_query(
            "UPDATE Dataset_Social_Real SET N_Rostos = ?, Brilho_Imagem = ? WHERE Post_ID_Social = ?",
            (rostos, brilho, post_id)
        )

        if rostos > 1:
            print(f"Detected {rostos} faces: {url_img}")

        if (index + 1) % 20 == 0:
            print(f"Processed {index + 1}/{len(df)} images...")

    print("Reanalysis complete!")


if __name__ == "__main__":
    processar_dataset_existente()

from flask import Flask, request, jsonify, send_from_directory
import subprocess
import os
import threading
import time
import traceback
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

last_request_time = time.time()
timeout = 600  # Timeout in secondi (600 secondi = 10 minuti)

# Variabile globale per memorizzare l'URL dell'oggetto 3D
def monitor_timeout():
    global last_request_time
    while True:
        if time.time() - last_request_time > timeout:
            print("Nessuna richiesta ricevuta. Spegnimento del server Flask.")
            os._exit(0) 
        time.sleep(60)

@app.route('/')
def home():
    return "Server Flask Funzionante!"

@app.route('/process', methods=['POST'])
def process_description():
    global last_request_time
    last_request_time = time.time() 

    description = request.form['description']
    use_less_than_15GB_str = request.form.get('use_less_than_15GB', 'False')
    use_less_than_15GB = use_less_than_15GB_str == 'True'

    # Path to Image and object source
    image_path = "/home/enrico/Scrivania/tesi/output/output_image.png"
    model_output_dir = "/home/enrico/Scrivania/tesi/stable-fast-3d-main/output"
    model_output_path = os.path.join(model_output_dir, "mesh.glb")
    
    try:
        print("Ricevuta descrizione:", description)
        print("Usa meno di 15GB:", use_less_than_15GB)

        if use_less_than_15GB:
            print("Eseguendo il primo modello, con meno di 24GB")
            result1 = subprocess.run(
                f"python FluxModel/runFlux.py \"Create a 3D high-Quality Render {description}\"",
                shell=True, check=True
            )
        else:
            print("Eseguendo il primo modello, con più di 24GB")
            result1 = subprocess.run(
                f"python FluxModel/runFluxOF.py \"Create a 3D high-Quality Render {description}\"",
                shell=True, check=True
            )
        print(f"Primo modello eseguito con successo: {result1}")

        # Check if the Image has been created 
        if not os.path.isfile(image_path):
            print(f"Immagine non creata: {image_path}")
            return jsonify({"error": "Immagine non creata"}), 500
        print(f"Immagine creata: {image_path}")

        # Second Model(Image to 3d Model)
        print("Eseguendo il secondo modello...")
        result2 = subprocess.run(
            f"python stable-fast-3d-main/run.py \"{image_path}\" --output-dir \"{model_output_dir}\"",
            shell=True, check=True
        )
        print(f"Secondo modello eseguito con successo: {result2}")

        # Building the object URL
        object_url = f"http://192.168.1.89:5000/objects/mesh.glb"
        print(f"URL del modello 3D: {object_url}")

        # Sending the response to Unity
        response = jsonify({"object_url": object_url})
        response.headers.add("Content-Type", "application/json")
        return response

    except subprocess.CalledProcessError as e:
        print("CalledProcessError:", e)
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print("Exception:", e)
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/objects/<path:filename>')
def serve_object(filename):
    directory_path = '/home/enrico/Scrivania/tesi/stable-fast-3d-main/output/0'

    # Servire il file
    response = send_from_directory(directory_path, filename)

    # Dopo aver servito il file, eseguire il comando di eliminazione della directory
    def remove_directory():
        try:
            shutil.rmtree(directory_path)
            print(f"Directory {directory_path} rimossa con successo.")
        except Exception as e:
            print(f"Errore durante la rimozione della directory: {e}")

    # Eseguire la rimozione della directory in background
    threading.Thread(target=remove_directory).start()

    return response

if __name__ == '__main__':
    timeout_thread = threading.Thread(target=monitor_timeout)
    timeout_thread.daemon = True 
    timeout_thread.start()
    app.run(host='0.0.0.0', port=5000)

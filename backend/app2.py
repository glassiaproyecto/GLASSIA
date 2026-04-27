"""
  Proyecto Integrador: Lentes inteligentes con reconocimiento de hardware
  Autoras: Adriana Cedillo · Valentina Cáceres
  Curso: 3.º E1 · 2026

  DESCRIPCIÓN GENERAL:
  Servidor web Flask que actúa como cerebro del sistema GlassIA.
  Recibe imágenes en tiempo real desde la cámara ESP32-CAM, las pasa
  por un modelo de inteligencia artificial (ResNet18) entrenado para
  clasificar componentes de hardware, y devuelve los resultados al
  navegador web. También envía el resultado a la pantalla OLED de
  los lentes.
"""

# IMPORTS — LIBRERÍAS NECESARIAS
from flask import Flask, jsonify, render_template
import torch
import torchvision.transforms as T
from PIL import Image
#import base64  
import requests
import io
import time

# INICIALIZACIÓN
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Usando: {DEVICE}")

MODEL_PATH = "modelo_completo_resnet18.pth"

#IP DE TU ESP32-CAM
#ESP32_CAM_URL = "http://192.168.18.174/capture"
#ESP32_CAM_URL = "http://192.168.1.10/capture"
ESP32_IP = "192.168.0.132"  # SOLO esto cambias
ESP32_CAM_URL = f"http://{ESP32_IP}/capture"

MIN_CONFIDENCE = 65.0

class_names = [
    'CPU', 'Ventilador', 'GPU', 'HDD',
    'Placa Madre', 'Fuente de Poder', 'RAM', 'SSD'
]

component_info = {
    "CPU": {
        "nombre": "Procesador (CPU)",
        "descripcion": "Es el cerebro de la computadora encargado de ejecutar instrucciones.",
        "funcion": "Procesa datos y coordina todas las operaciones del sistema.",
        "importancia": "Sin la CPU el computador no puede funcionar."
    },

    "Ventilador": {
        "nombre": "Ventilador (Fan)",
        "descripcion": "Sistema de enfriamiento que reduce la temperatura interna.",
        "funcion": "Evita el sobrecalentamiento de los componentes.",
        "importancia": "Mantiene el rendimiento y prolonga la vida útil del equipo."
    },

    "GPU": {
        "nombre": "Tarjeta Gráfica (GPU)",
        "descripcion": "Componente especializado en el procesamiento de gráficos.",
        "funcion": "Renderiza imágenes, videos y gráficos en pantalla.",
        "importancia": "Es esencial para juegos, diseño y tareas visuales."
    },

    "HDD": {
        "nombre": "Disco Duro (HDD)",
        "descripcion": "Unidad de almacenamiento mecánica basada en discos magnéticos.",
        "funcion": "Guarda datos de forma permanente.",
        "importancia": "Permite almacenar archivos, programas y el sistema operativo."
    },

    "Placa Madre": {
        "nombre": "Placa Madre (Motherboard)",
        "descripcion": "Tarjeta principal que conecta todos los componentes.",
        "funcion": "Permite la comunicación entre CPU, RAM, almacenamiento y otros dispositivos.",
        "importancia": "Es la base del sistema; sin ella no hay funcionamiento."
    },

    "Fuente de Poder": {
        "nombre": "Fuente de Poder (PSU)",
        "descripcion": "Componente que suministra energía eléctrica al sistema.",
        "funcion": "Convierte la corriente eléctrica para alimentar los componentes.",
        "importancia": "Garantiza un suministro estable y seguro de energía."
    },

    "RAM": {
        "nombre": "Memoria RAM",
        "descripcion": "Memoria temporal de alta velocidad.",
        "funcion": "Almacena datos que el sistema está utilizando en el momento.",
        "importancia": "Mejora la velocidad y fluidez del sistema."
    },

    "SSD": {
        "nombre": "Unidad de Estado Sólido (SSD)",
        "descripcion": "Dispositivo de almacenamiento rápido sin partes mecánicas.",
        "funcion": "Almacena datos de forma permanente con alta velocidad.",
        "importancia": "Reduce tiempos de carga y mejora el rendimiento general."
    }
}

# CARGA DEL MODELO
print("Cargando modelo...")

model = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False
)

model.eval()
model.to(DEVICE)

transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

print("Modelo listo\n")

# RUTAS
# Página principal (tu HTML)
@app.route("/")
def home():
    return render_template("pagina.html", ip=ESP32_IP)


# Ruta de prueba
#@app.route("/")
#def home():
    #return """
    #<h2>Servidor activo</h2>
    #<p>Ir a <a href='/live'>/live</a></p>

# PREDICCIÓN DESDE ESP32
from flask import Response

@app.route("/video")
def video():
    try:
        response = requests.get(
            ESP32_CAM_URL,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if response.status_code == 200:
            return Response(response.content, mimetype='image/jpeg')
        else:
            print("Error status:", response.status_code)
            return "No se pudo obtener imagen", 500

    except requests.exceptions.RequestException as e:
        print("Error conexión ESP32:", e)
        return "Error de conexión con ESP32", 500 

@app.route("/predict_esp32")
def predict_esp32():
    try:
        # Obtener imagen desde ESP32-CAM
        response = requests.get(ESP32_CAM_URL, timeout=5)

        if response.status_code != 200:
            return jsonify({"error": "No se pudo obtener imagen de la ESP32"})

        # Abre la imagen desde los bytes recibidos y la convierte a RGB
        img = Image.open(io.BytesIO(response.content)).convert("RGB")

        # Preprocesar la imagen 
        input_tensor = transform(img).unsqueeze(0).to(DEVICE)

        # Inferencia del modelo 
        with torch.no_grad():
            start = time.time()

            output = model(input_tensor)
            probabilities = torch.nn.functional.softmax(output[0], dim=0)

            confidence, predicted_idx = torch.max(probabilities, 0)

            inference_time = (time.time() - start) * 1000

        confidence_pct = float(confidence.item() * 100)
        predicted_class = class_names[predicted_idx.item()]

        # Top 3 predicciones
        top3_prob, top3_idx = torch.topk(probabilities, 3)
        top3 = [
            {
                "class": class_names[idx],
                "confidence": float(prob * 100)
            }
            for prob, idx in zip(top3_prob, top3_idx)
        ]

        # Verificar umbral de confianza y preparar respuesta
        if confidence_pct >= MIN_CONFIDENCE:
            info = component_info.get(predicted_class, {})

            # Enviar resultado a la pantalla OLED del ESP32 
            # Hace una petición GET al endpoint /display del ESP32 que controla la micro-pantalla OLED integrada en los lentes
            try:
                requests.get(
                    f"http://{ESP32_IP}/display?text={predicted_class}&conf={round(confidence_pct,1)}",
                    timeout=2
                )
            except:
                print("No se pudo enviar a OLED")

            # Retornar JSON al navegador 
            return jsonify({
                "prediction": predicted_class,
                "confidence": round(confidence_pct, 1),
                "recognized": True,
                "top3": top3,
                "info": info,
                "inference_time_ms": round(inference_time, 1)
            })

        else:
            #Envia a la OLED que no se reconoció nada
            try:
                requests.get(
                    f"http://{ESP32_IP}/display?text=NO&conf={round(confidence_pct,1)}",
                    timeout=2
                )
            except:
                print("No se pudo enviar a OLED")

            return jsonify({
                "prediction": "No reconocido",
                "confidence": round(confidence_pct, 1),
                "recognized": False,
                "message": "Confianza baja – acerca o enfoca mejor",
                "top3": top3,
                "inference_time_ms": round(inference_time, 1)
            })

    except Exception as e:
        # Captura cualquier error y lo retorna como JSON
        return jsonify({"error": str(e)})

# EJECUCIÓN
if __name__ == "__main__":
    app.run(
        debug=True,         # Muestra errores detallados y recarga automática
        use_reloader=False, # Evita cargar el modelo 2 veces
        host="0.0.0.0",     # Escucha en todas las interfaces de red 
        port=5000           # Puerto HTTP
    )

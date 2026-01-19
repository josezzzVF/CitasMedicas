🌱 *Sistema de Diagnóstico de Enfermedades en Hojas de Caña de Azúcar*
<p align="center"> <em>Aplicación basada en Deep Learning para la detección automática de enfermedades en hojas de caña de azúcar</em> </p>
📌 Descripción general

Este sistema permite identificar enfermedades en hojas de caña de azúcar a partir de imágenes RGB, utilizando Redes Neuronales Convolucionales (CNN) entrenadas previamente.
Está orientado a fines académicos, investigativos y de apoyo agrícola.

🎯 Objetivo del sistema

Detectar automáticamente enfermedades en hojas de caña de azúcar

Reducir el tiempo de diagnóstico manual

Apoyar la toma de decisiones en el sector agrícola

Brindar una herramienta sencilla e intuitiva al usuario

🧰 Requisitos del sistema
🔹 Hardware

Computadora con 8 GB de RAM mínimo (recomendado 16 GB)

Conexión a internet

🔹 Software

Python 3.9 o superior

Google Colab o entorno local

Navegador web actualizado

🔹 Librerías principales

TensorFlow / Keras

NumPy

OpenCV

Scikit-learn

Matplotlib

Streamlit

📂 Estructura del proyecto
📁 dataset/        → Imágenes organizadas por clase
📁 models/         → Modelos entrenados (.keras / .h5)
📁 notebooks/      → Entrenamiento y evaluación
📁 utils/          → Funciones auxiliares
📄 app_sugarcane.py → Aplicación Streamlit
📄 README.md       → Guía de usuario

🚀 Guía de uso rápido
1️⃣ Abrir el proyecto

Accede al notebook desde Google Colab

Monta Google Drive si el dataset o modelos están allí

2️⃣ Cargar el modelo

Ejecuta la celda de carga del modelo entrenado

Modelos disponibles:

CNN personalizada

DenseNet121

ResNet50

3️⃣ Ejecutar la aplicación Streamlit
streamlit run app_sugarcane.py

🖼️ Uso de la aplicación

Cargar una imagen (.jpg o .png) de la hoja

Visualizar la imagen en pantalla

Presionar Diagnosticar

Obtener:

Enfermedad detectada

Nivel de confianza del modelo

📊 Interpretación de resultados

Clase predicha → Enfermedad identificada

Probabilidad (%) → Confianza del modelo

Resultados con baja confianza deben revisarse manualmente

✅ Buenas prácticas

✔ Usar imágenes claras y bien iluminadas
✔ Evitar sombras o fondos complejos
✔ Capturar hojas completas
✔ Mantener una distancia adecuada

⚠️ Limitaciones

El sistema solo reconoce enfermedades entrenadas

No reemplaza la evaluación de un especialista

La precisión depende de la calidad del dataset

🔄 Mantenimiento y mejoras

Reentrenar el modelo al añadir nuevas clases

Actualizar librerías periódicamente

Evaluar con nuevos conjuntos de datos

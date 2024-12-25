# VampSurvWithVoiceAndHandGesture

**VampSurvWithVoiceAndHandGesture** es un proyecto innovador que permite controlar el juego "Vampire Survivors" utilizando comandos de voz y gestos de la mano. Este proyecto integra tecnologías de reconocimiento de voz y gestos con Python para proporcionar una experiencia de juego interactiva y accesible.

## Características Principales

- **Control por Voz**: Utiliza comandos de voz para mover el personaje, pausar/reanudar el juego, tomar capturas de pantalla y realizar otras acciones.
- **Control por Gestos**: Utiliza gestos de la mano para mover el cursor del ratón y realizar acciones en el juego.
- **Modo Arrastre**: Activa un modo de clic permanente mediante comandos de voz, perfecto para controlar personajes que siguen al cursor.
- **Compatibilidad**: Diseñado específicamente para el juego "Vampire Survivors", pero fácilmente adaptable a otros juegos o aplicaciones.

## Tecnologías Utilizadas

- **Python**: El lenguaje principal utilizado para la lógica del juego y los comandos.
- **Mediapipe**: Biblioteca utilizada para el reconocimiento de gestos de la mano.
- **Pyautogui**: Biblioteca utilizada para controlar el ratón y el teclado.
- **SpeechRecognition**: Biblioteca para el reconocimiento de voz.

## Instalación

1. Clona este repositorio:
   ```bash
   git clone https://github.com/Emilmrk/VampSurvWithVoiceAndHandGesture.git

2. Navega al directorio del proyecto:
   ```bash
   cd VampSurvWithVoiceAndHandGesture

3. Crea y activa un entorno virtual (opcional, pero recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate # En Windows, usa `venv\Scripts\activate`

4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   
5. Cambia la ruta del juego en game.py a la ruta donde tienes instalado "Vampire Survivors":
   ```bash
   pip install -r requirements.txt
   # Cambia esta línea:
   game_path = "E:\\Steam\\steamapps\\common\\Vampire Survivors\\VampireSurvivors.exe"
   # a la ruta de tu instalación del juego

6. Ejecuta el proyecto:
   ```bash
   python main.py



## Uso

1. **Iniciar el Juego**: Usa el comando de voz "abrir juego" para iniciar "Vampire Survivors".
2. **Control del Personaje**: Utiliza comandos de voz como "arriba", "abajo", "izquierda", "derecha", "enter" y "escape".
3. **Modo Arrastre**: Di "mover" para activar el modo arrastre y "detener" para desactivarlo.
4. **Captura de Pantalla**: Di "captura" para tomar una captura de pantalla.
5. **Salir del Programa**: Di "salir del programa" para cerrar el programa.


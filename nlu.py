"""
Módulo NLU (Natural Language Understanding) con Gemini API y rotación automática de modelos.
- Lista dinámicamente los modelos disponibles desde la API de Google.
- Ordena de más avanzado a más básico (gemini-4 > gemini-3.x > gemini-2.5 > ... > gemma).
- Si un modelo agota cuota/tokens (429 / RESOURCE_EXHAUSTED), lo pone en enfriamiento,
  vuelve a listar y cambia automáticamente al siguiente disponible.
- Cuando un modelo superior recupera su cuota tras el enfriamiento, vuelve a usarlo.
"""
import json
import re
import threading
import time
import requests
import config

ACCIONES_VALIDAS = {
    "abrir_juego",
    "cerrar_juego",
    "salir_programa",
    "modo_raton",
    "modo_wasd",
    "modo_flechas",
    "arriba",
    "abajo",
    "izquierda",
    "derecha",
    "mover",
    "detener",
    "doble_clic",
    "clic",
    "espacio",
    "enter",
    "escape",
    "captura",
    "ninguna",
}

_EXCLUIR_PALABRAS = (
    "tts",
    "image",
    "transcribe",
    "lyria",
    "nano-banana",
    "robotics",
    "computer-use",
    "deep-research",
    "antigravity",
    "customtools",
    "embedding",
    "aqa",
    "imagen",
    "veo",
    "audio",
    "omni",
)

_PROMPT_BASE = (
    "Eres el intérprete de comandos de voz de un sistema de control por voz y gestos para PC y videojuegos.\n"
    "El usuario habla en español, pero el micrófono/STT a veces comete errores fonéticos "
    "(ej. 'despacio' por 'espacio', 'harina' por 'arriba', 'serrar' por 'cerrar', 'clik' por 'clic', 'izquiero' por 'izquierda') "
    "o usa frases naturales (ej. 'pausa el juego', 'suelta el ratón', 'quiero usar las flechitas', 'saca una foto').\n"
    "Mapea el texto reconocido a UNA sola acción de esta lista exacta:\n"
    "abrir_juego, cerrar_juego, salir_programa, modo_raton, modo_wasd, modo_flechas, "
    "arriba, abajo, izquierda, derecha, mover, detener, doble_clic, clic, espacio, enter, escape, captura, ninguna.\n"
    "Si es ruido sin sentido o no corresponde a ninguna acción, responde 'ninguna'.\n"
    'Responde exclusivamente JSON válido con el formato: {"accion": "<nombre>"}\n'
    "Texto reconocido: "
)


def _puntuar_modelo(nombre: str) -> tuple:
    """
    Asigna una puntuación ordenable descendentemente para elegir el modelo más avanzado primero.
    """
    n = nombre.lower()
    familia = 2 if n.startswith("gemini-") else (1 if n.startswith("gemma-") else 0)

    # Extraer versión numérica principal (ej. 4, 3.8, 2.5)
    match_ver = re.search(r"(\d+)(?:\.(\d+))?", n)
    if match_ver:
        major = int(match_ver.group(1))
        minor = int(match_ver.group(2)) if match_ver.group(2) else 0
    elif "latest" in n:
        major, minor = 2, 9
    else:
        major, minor = 0, 0

    # Nivel dentro de la misma versión (pro / flagship > flash / estándar > lite)
    if "lite" in n:
        tier = 1
    elif "flash" in n:
        tier = 2
    elif "pro" in n or any(x in n for x in ("neon", "hydrogen", "carbon", "argon")):
        tier = 3
    else:
        tier = 2

    estable = 0 if "preview" in n else 1
    return (familia, major, minor, tier, estable, n)


class GeminiModelRouter:
    """Gestor dinámico de modelos Gemini con failover por cuota y recuperación automática."""

    def __init__(self, list_ttl_seconds: float = 900.0):
        self._lock = threading.Lock()
        self._modelos_ordenados: list[str] = []
        self._ultima_lista: float = 0.0
        self._list_ttl = list_ttl_seconds
        self._cooldowns: dict[str, float] = {}
        self._modelo_activo: str | None = None
        self._aviso_sin_cuota_emitido: bool = False

    def listar_modelos(self, api_key: str, force_refresh: bool = False) -> list[str]:
        """Consulta la API para obtener y ordenar los modelos válidos para generateContent."""
        ahora = time.time()
        with self._lock:
            if (
                not force_refresh
                and self._modelos_ordenados
                and (ahora - self._ultima_lista) < self._list_ttl
            ):
                return list(self._modelos_ordenados)

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            resp = requests.get(url, timeout=max(3.0, config.GEMINI_TIMEOUT_SECONDS))
            if resp.status_code != 200:
                return self._modelos_ordenados or ["gemini-2.5-flash"]

            candidatos = []
            for item in resp.json().get("models", []):
                methods = item.get("supportedGenerationMethods", [])
                if "generateContent" not in methods:
                    continue
                nombre = item.get("name", "").replace("models/", "").strip()
                n_low = nombre.lower()
                if not (n_low.startswith("gemini-") or n_low.startswith("gemma-")):
                    continue
                if any(ex in n_low for ex in _EXCLUIR_PALABRAS):
                    continue
                candidatos.append(nombre)

            candidatos.sort(key=_puntuar_modelo, reverse=True)

            if candidatos:
                with self._lock:
                    self._modelos_ordenados = candidatos
                    self._ultima_lista = time.time()
                return candidatos
        except Exception:
            pass

        with self._lock:
            return list(self._modelos_ordenados) if self._modelos_ordenados else ["gemini-2.5-flash"]

    def marcar_enfriamiento(self, modelo: str, segundos: float):
        """Pone un modelo en enfriamiento temporal tras agotar cuota o fallar."""
        with self._lock:
            self._cooldowns[modelo] = time.time() + segundos

    def obtener_disponibles(self, api_key: str, force_refresh: bool = False) -> list[str]:
        """Retorna los modelos ordenados que no están en enfriamiento (recupera los ya liberados)."""
        modelos = self.listar_modelos(api_key, force_refresh=force_refresh)
        modelo_fijo = getattr(config, "GEMINI_MODEL", "auto")
        if modelo_fijo and modelo_fijo.lower() != "auto" and modelo_fijo in modelos:
            modelos = [modelo_fijo] + [m for m in modelos if m != modelo_fijo]

        ahora = time.time()
        with self._lock:
            return [m for m in modelos if ahora >= self._cooldowns.get(m, 0.0)]

    def registrar_exito(self, modelo: str):
        with self._lock:
            if self._modelo_activo != modelo:
                self._modelo_activo = modelo
                print(f"[GEMINI] Modelo activo: {modelo}")


_router = GeminiModelRouter()


def _extraer_accion_de_respuesta(texto_respuesta: str) -> str | None:
    """Extrae el campo 'accion' incluso si el modelo envuelve el JSON en markdown."""
    if not texto_respuesta:
        return None
    limpio = texto_respuesta.strip()
    try:
        data = json.loads(limpio)
        accion = str(data.get("accion", "")).strip().lower()
        return accion if accion in ACCIONES_VALIDAS else None
    except Exception:
        pass

    match = re.search(r"\{[^{}]*\}", limpio, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            accion = str(data.get("accion", "")).strip().lower()
            return accion if accion in ACCIONES_VALIDAS else None
        except Exception:
            pass
    return None


def interpretar_comando_con_gemini(texto: str) -> str | None:
    """
    Consulta Gemini API usando el modelo más avanzado disponible con rotación automática
    si se agota la cuota, y recuperación automática cuando el modelo superior recupera cuota.
    """
    api_key = getattr(config, "GEMINI_API_KEY", "")
    if not api_key or not texto:
        return None

    disponibles = _router.obtener_disponibles(api_key)
    if not disponibles:
        if not _router._aviso_sin_cuota_emitido:
            _router._aviso_sin_cuota_emitido = True
            print("[GEMINI] Todos los modelos en enfriamiento temporal; usando solo comandos locales hasta que recuperen cuota.")
        return None

    intentados = set()
    cooldown_cuota = max(180.0, getattr(config, "GEMINI_COOLDOWN_SECONDS", 60.0))

    while disponibles:
        modelo = next((m for m in disponibles if m not in intentados), None)
        if modelo is None:
            break
        intentados.add(modelo)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        gen_config = {"temperature": 0.0, "maxOutputTokens": 256}
        if modelo.lower().startswith("gemini-"):
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": _PROMPT_BASE + texto}]}],
            "generationConfig": gen_config,
        }

        try:
            resp = requests.post(url, json=payload, timeout=config.GEMINI_TIMEOUT_SECONDS)

            if resp.status_code == 200:
                data = resp.json()
                contenido = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                accion = _extraer_accion_de_respuesta(contenido)
                _router._aviso_sin_cuota_emitido = False
                _router.registrar_exito(modelo)
                if accion and accion != "ninguna":
                    return accion
                return None

            body_low = resp.text.lower()
            if resp.status_code == 429 or "quota" in body_low or "resource_exhausted" in body_low:
                es_diario = "limit: 0" in body_low or "perday" in body_low
                _router.marcar_enfriamiento(modelo, 1800.0 if es_diario else cooldown_cuota)
                disponibles = _router.obtener_disponibles(api_key)
                continue

            if resp.status_code in (400, 403, 404, 503):
                _router.marcar_enfriamiento(modelo, 1800.0 if resp.status_code in (400, 404) else 120.0)
                disponibles = _router.obtener_disponibles(api_key)
                continue

        except requests.Timeout:
            _router.marcar_enfriamiento(modelo, 300.0)
            disponibles = _router.obtener_disponibles(api_key)
            continue
        except Exception:
            return None

    if not _router._aviso_sin_cuota_emitido:
        _router._aviso_sin_cuota_emitido = True
        print("[GEMINI] Modelos sin cuota temporalmente; usando comandos locales hasta recuperación.")
    return None


def precalentar_router():
    """Pre-lista y prueba el mejor modelo disponible en segundo plano al iniciar."""
    if getattr(config, "GEMINI_API_KEY", ""):
        threading.Thread(
            target=lambda: interpretar_comando_con_gemini("calibracion"),
            name="HiloGeminiWarmup",
            daemon=True,
        ).start()

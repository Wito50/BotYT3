import os
import asyncio
from telethon import TelegramClient, events, Button
from yt_dlp import YoutubeDL

# === CONFIGURACIÓN ===
API_ID = 28231389
API_HASH = '9d0dbb88eb4216565c5280a22788cbf9'
BOT_TOKEN = '7590978958:AAG_Q8rJZLu5ENVWytqdT9xJgW8DNCLTxTA'
COOKIE_PATH = os.path.expanduser('~/cookies.txt')
DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
pending_links = {}

# === Obtener tamaños estimados ===
def estimar_tamanos(url):
    ydl_opts = {
        'quiet': True,
        'cookiefile': COOKIE_PATH,
        'skip_download': True,
        'format': 'best',
        'dump_single_json': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formatos = info.get("formats", [])
        resultado = {}

        resoluciones = {
            "240": 240,
            "360": 360,
            "480": 480,
        }

        for key, height in resoluciones.items():
            for f in formatos:
                if f.get("height") == height:
                    size = f.get("filesize") or f.get("filesize_approx")
                    if size:
                        resultado[key] = round(size / (1024 * 1024), 1)  # MB
                        break

        # AUDIO
        for f in formatos:
            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                size = f.get("filesize") or f.get("filesize_approx")
                if size:
                    resultado["audio"] = round(size / (1024 * 1024), 1)
                    break

        return resultado

# === Descargar video o audio ===
def descargar_video(url, calidad):
    output_path = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')

    if calidad == "audio":
        ydl_opts = {
            'outtmpl': output_path,
            'quiet': True,
            'noplaylist': True,
            'cookiefile': COOKIE_PATH,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            'outtmpl': output_path,
            'quiet': True,
            'noplaylist': True,
            'cookiefile': COOKIE_PATH,
            'http_chunk_size': 1048576,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 60,
            'user_agent': 'Mozilla/5.0',
            'format': f'bestvideo[height={calidad}]+bestaudio[ext=m4a]/best[height<={calidad}]',
        }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        if calidad == "audio":
            path = path.rsplit('.', 1)[0] + ".mp3"
        print(f"✅ Descarga completada: {path}")
        return path

# === Botón con tamaño ===
def btn(label, key, tamanos):
    size = tamanos.get(key)
    txt = f"{label} – {size:.1f}MB" if size else f"{label} – ❓"
    return [Button.inline(txt, f"res{key}".encode())]

# === Recibir enlace ===
@bot.on(events.NewMessage(pattern=r'^https?://.*(youtube\.com|youtu\.be).*'))
async def recibir_enlace(event):
    user_id = event.sender_id
    url = event.raw_text.strip()
    pending_links[user_id] = url

    await bot.send_message(user_id, "🔍 Consultando tamaños estimados...")

    try:
        tamanos = estimar_tamanos(url)
    except Exception as e:
        await bot.send_message(user_id, f"❌ Error al obtener info: {e}")
        return

    botones = (
        btn("📺 240p", "240", tamanos) +
        btn("📺 360p", "360", tamanos) +
        btn("📺 480p", "480", tamanos) +
        btn("🎵 Audio", "audio", tamanos)
    )

    await bot.send_message(
        user_id,
        "🎚️ Elige calidad para descargar:",
        buttons=botones
    )

# === Procesar botón ===
@bot.on(events.CallbackQuery)
async def manejar_boton(event):
    user_id = event.sender_id
    data = event.data.decode()
    calidad = data.replace("res", "")
    url = pending_links.get(user_id)

    if not url:
        await event.answer("❌ Link no encontrado.", alert=True)
        return

    texto_opcion = "audio" if calidad == "audio" else f"{calidad}p"
    await event.edit(f"⏬ Descargando {texto_opcion}...")

    try:
        path = descargar_video(url, calidad)
        if not os.path.exists(path):
            await bot.send_message(user_id, "❌ No se encontró el archivo después de descargar.")
            return

        size = os.path.getsize(path) / (1024 * 1024)
        await bot.send_message(
            user_id,
            f"✅ Archivo descargado ({size:.1f}MB).\n📂 Guardado en: `{path}`"
        )

    except Exception as e:
        await bot.send_message(user_id, f"❌ Error: {str(e)}")

# === INICIO ===
print("🤖 Bot listo: descarga local con estimación de tamaño.")
bot.run_until_disconnected()

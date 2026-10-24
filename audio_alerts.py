import os
import time
import queue
import threading
import wave
from pathlib import Path
import numpy as np
import pygame
import pyttsx3

BASE_DIR = Path(__file__).resolve().parent
SOUNDS_DIR = BASE_DIR / "sounds"
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

# ----------------- SOUND GENERATOR & VERIFIER -----------------
def _synthesize_robotic_sound_assets():
    """Generates sci-fi robotic audio cues if not present"""
    sample_rate = 44100

    def _save_pcm(file_path, samples):
        samples = np.clip(samples, -1.0, 1.0)
        pcm = (samples * 32767).astype(np.int16)
        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())

    # 1. Robotic UI Chirp (AI prompt blip) - 0.12s
    f_chirp = SOUNDS_DIR / "robot_chirp.wav"
    if not f_chirp.exists():
        t = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
        freq = np.linspace(1200, 2400, len(t))
        sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * 25)
        sig += 0.35 * np.sin(4 * np.pi * freq * t) * np.exp(-t * 30)
        _save_pcm(f_chirp, sig * 0.7)

    # 2. Robotic Warning (Drowsiness Alert) - Dual high-tech pulse 0.35s
    f_warn = SOUNDS_DIR / "robot_warning.wav"
    if not f_warn.exists():
        t = np.linspace(0, 0.35, int(sample_rate * 0.35), False)
        def pulse(t_arr, t_start, f1, f2):
            mask = (t_arr >= t_start) & (t_arr < t_start + 0.14)
            dt = t_arr - t_start
            p = np.zeros_like(t_arr)
            val = np.sin(2 * np.pi * f1 * dt) + 0.5 * np.sin(2 * np.pi * f2 * dt) + 0.25 * np.sin(2 * np.pi * (f1 * 2) * dt)
            p[mask] = (val * np.exp(-dt * 18))[mask]
            return p
        sig = pulse(t, 0.0, 1046.5, 1318.5) + pulse(t, 0.15, 1318.5, 1568.0)
        _save_pcm(f_warn, sig * 0.8)

    # 3. Robotic Phone Distraction Alert - 0.4s cybernetic scanner sweep
    f_phone = SOUNDS_DIR / "robot_phone_alert.wav"
    if not f_phone.exists():
        t = np.linspace(0, 0.4, int(sample_rate * 0.4), False)
        sig = np.zeros_like(t)
        for t_st in [0.0, 0.12, 0.24]:
            mask = (t >= t_st) & (t < t_st + 0.09)
            dt = t - t_st
            f = 1600 - dt * 5000
            sub = np.sin(2 * np.pi * f * dt) + 0.4 * np.sin(2 * np.pi * (f * 1.5) * dt)
            sig[mask] += (sub * np.sin(np.pi * (dt / 0.09)))[mask]
        _save_pcm(f_phone, sig * 0.8)

    # 4. Robotic Boot / System Online - 0.9s ascending futuristic sweep
    f_boot = SOUNDS_DIR / "robot_boot.wav"
    if not f_boot.exists():
        t = np.linspace(0, 0.9, int(sample_rate * 0.9), False)
        f_sweep = 440 + 880 * (t / 0.9) ** 1.5
        carrier = np.sin(2 * np.pi * f_sweep * t)
        mod = 0.3 * np.sin(2 * np.pi * 35 * t)
        synth = np.sin(2 * np.pi * f_sweep * t + mod * 4) + 0.4 * np.sin(2 * np.pi * (f_sweep * 1.5) * t)
        env = np.minimum(t * 8, 1.0) * (1.0 - (t / 0.9) ** 1.8)
        _save_pcm(f_boot, synth * env * 0.75)

    # 5. Robotic Emergency Klaxon - 0.8s dual alternating oscillation
    f_emerg = SOUNDS_DIR / "robot_emergency.wav"
    if not f_emerg.exists():
        t = np.linspace(0, 0.8, int(sample_rate * 0.8), False)
        lfo = np.sin(2 * np.pi * 5 * t)
        f_inst = 900 + 350 * lfo
        sig = np.sin(2 * np.pi * f_inst * t) + 0.35 * np.sign(np.sin(2 * np.pi * f_inst * 0.5 * t))
        env = 0.5 * (1 + np.sin(2 * np.pi * 5 * t - np.pi / 2))
        _save_pcm(f_emerg, sig * env * 0.85)

    # 6. Robotic Safe / Recovery Chime - 0.35s pleasant ascending sci-fi chime
    f_safe = SOUNDS_DIR / "robot_safe.wav"
    if not f_safe.exists():
        t = np.linspace(0, 0.35, int(sample_rate * 0.35), False)
        def pulse_safe(t_arr, t_start, f1, f2):
            mask = (t_arr >= t_start) & (t_arr < t_start + 0.14)
            dt = t_arr - t_start
            p = np.zeros_like(t_arr)
            val = np.sin(2 * np.pi * f1 * dt) + 0.5 * np.sin(2 * np.pi * f2 * dt)
            p[mask] = (val * np.exp(-dt * 15))[mask]
            return p
        sig = pulse_safe(t, 0.0, 659.25, 987.77) + pulse_safe(t, 0.14, 880.0, 1318.5)
        _save_pcm(f_safe, sig * 0.7)

    # 7. Robotic Mayday Urgent Speech Alert ("Mayday! Mayday! Mayday! You are in danger!")
    f_mayday = SOUNDS_DIR / "robot_mayday.wav"
    if not f_mayday.exists():
        try:
            e = pyttsx3.init()
            e.setProperty("rate", 195)
            voices = e.getProperty("voices")
            if voices:
                e.setProperty("voice", voices[0].id)
            tmp_wav = SOUNDS_DIR / "tmp_mayday.wav"
            e.save_to_file("Mayday! Mayday! Mayday! You are in danger!", str(tmp_wav))
            e.runAndWait()

            with wave.open(str(tmp_wav), "rb") as wf:
                framerate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())

            data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            nonzero = np.where(np.abs(data) > 0.02)[0]
            if len(nonzero) > 0:
                start_idx = max(0, nonzero[0] - int(0.05 * framerate))
                end_idx = min(len(data), nonzero[-1] + int(0.08 * framerate))
                data = data[start_idx:end_idx]

            # 55 Hz Cybernetic ring modulation + metallic comb filter
            t_m = np.arange(len(data)) / framerate
            mod = 0.5 * (1.0 + np.sin(2 * np.pi * 55 * t_m))
            robotic = data * (0.4 + 0.6 * mod)

            delay = int(0.0032 * framerate)
            delayed = np.zeros_like(robotic)
            delayed[delay:] = robotic[:-delay] * 0.45
            robotic = np.clip(robotic + delayed, -1.0, 1.0)

            t_chirp = np.linspace(0, 0.15, int(framerate * 0.15), False)
            ch = (np.sin(2 * np.pi * 1400 * t_chirp) + 0.5 * np.sin(2 * np.pi * 2100 * t_chirp)) * np.exp(-t_chirp * 20)
            final_audio = np.concatenate([np.clip(ch * 0.6, -1.0, 1.0), robotic])
            _save_pcm(f_mayday, final_audio)

            if tmp_wav.exists():
                tmp_wav.unlink()
        except Exception as err:
            print(f"[Audio] Mayday generation note: {err}")


# Run generator on import
_synthesize_robotic_sound_assets()

# ----------------- PYGAME MIXER INITIALIZATION -----------------
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.set_num_channels(8)
except Exception as e:
    print(f"[Audio] Pygame mixer init note: {e}")

_sounds = {}
def _load_sound(key, filename):
    path = SOUNDS_DIR / filename
    if path.exists():
        try:
            snd = pygame.mixer.Sound(str(path))
            _sounds[key] = snd
            return snd
        except Exception as e:
            print(f"[Audio] Error loading sound {filename}: {e}")
    return None

_load_sound("chirp", "robot_chirp.wav")
_load_sound("warning", "robot_warning.wav")
_load_sound("phone", "robot_phone_alert.wav")
_load_sound("boot", "robot_boot.wav")
_load_sound("emergency", "robot_emergency.wav")
_load_sound("safe", "robot_safe.wav")
_load_sound("mayday", "robot_mayday.wav")

def play_sound(name, loops=0, volume=1.0):
    """Play a cached robotic sound asynchronously without blocking video loops"""
    snd = _sounds.get(name)
    if snd:
        try:
            snd.set_volume(volume)
            return snd.play(loops=loops)
        except Exception as e:
            print(f"[Audio] Play sound error: {e}")
    return None

def stop_sound(name):
    snd = _sounds.get(name)
    if snd:
        try:
            snd.stop()
        except Exception:
            pass

# ----------------- THREAD-SAFE ROBOTIC TTS WORKER -----------------
_tts_queue = queue.Queue()

def _tts_loop():
    engine = None
    try:
        engine = pyttsx3.init()
        # Calibrate for authoritative robotic delivery
        engine.setProperty("rate", 160)
        engine.setProperty("volume", 1.0)
        voices = engine.getProperty("voices")
        if voices:
            # Prefer English US voices like David or Zira
            engine.setProperty("voice", voices[0].id)
    except Exception as e:
        print(f"[TTS] Engine init error: {e}")

    while True:
        item = _tts_queue.get()
        if item is None:
            break
        text, prepend_chirp = item
        try:
            if prepend_chirp:
                play_sound("chirp", volume=0.85)
                time.sleep(0.12)
            if engine:
                engine.say(text)
                engine.runAndWait()
        except Exception as err:
            print(f"[TTS] Speech error: {err}")
        finally:
            _tts_queue.task_done()

_tts_thread = threading.Thread(target=_tts_loop, daemon=True)
_tts_thread.start()

def voice_alert(message, prepend_chirp=True):
    """Queues robotic voice alert with sci-fi audio chirp"""
    _tts_queue.put((message, prepend_chirp))

# ----------------- HIGH-LEVEL ROBOTIC SAFETY ALERTS -----------------
_last_drowsy_time = 0
_last_mayday_time = 0
_mayday_channel = None

def trigger_mayday_alert(cooldown=2.8):
    """
    Plays urgent robotic voice:
    'Mayday! Mayday! Mayday! You are in danger!'
    Triggered when driver eyes close.
    """
    global _last_mayday_time, _mayday_channel
    now = time.time()
    if now - _last_mayday_time > cooldown:
        if _mayday_channel and _mayday_channel.get_busy():
            _mayday_channel.stop()
        _mayday_channel = play_sound("mayday", volume=1.0)
        if _mayday_channel is None:
            play_sound("warning", volume=1.0)
            voice_alert("Mayday! Mayday! Mayday! You are in danger!", prepend_chirp=True)
        _last_mayday_time = now
        return True
    return False

def trigger_drowsy_beep(cooldown=0.6):
    """Plays non-blocking futuristic dual-pulse warning tone"""
    global _last_drowsy_time
    now = time.time()
    if now - _last_drowsy_time > cooldown:
        play_sound("warning", volume=1.0)
        _last_drowsy_time = now
        return True
    return False

def trigger_phone_warning():
    """Robotic tone + warning for phone distraction"""
    play_sound("phone", volume=1.0)
    voice_alert("Warning: Handheld mobile distraction detected. Keep both hands on the wheel.")

def trigger_sleepy_reminder():
    """Fatigue index notification"""
    play_sound("warning", volume=0.9)
    voice_alert("Warning: High driver fatigue index. Please pull over safely for a rest break.")

def trigger_safe_chime():
    """Pleasant confirmation chime when driver attention returns"""
    play_sound("safe", volume=0.6)

def trigger_system_boot():
    """Futuristic boot-up sound and status report"""
    play_sound("boot", volume=0.9)
    time.sleep(0.3)
    voice_alert("Safe Steer A.I. online. Driver safety radar engaged.", prepend_chirp=False)

def trigger_emergency_protocol(user_id, log_fn=None):
    """High-urgency emergency sequence for unresponsive driver"""
    # 1. Play robotic emergency klaxon
    klaxon_ch = play_sound("emergency", loops=3, volume=1.0)
    
    # 2. Sound car horn if available
    horn_path = BASE_DIR / "car_horn.mp3"
    if horn_path.exists():
        try:
            pygame.mixer.music.load(str(horn_path))
            pygame.mixer.music.play(-1)
            time.sleep(7)
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"[Audio] Horn playback note: {e}")
            time.sleep(3)
    else:
        time.sleep(3)

    if klaxon_ch:
        try:
            klaxon_ch.stop()
        except Exception:
            pass

    # 3. Spoken emergency announcement
    voice_alert("Critical emergency: Driver is unresponsive. Autonomous rescue telemetry dispatched.")
    if log_fn:
        try:
            log_fn(user_id, "Driver Unresponsive")
        except Exception as e:
            print(f"[Audio] Log callback error: {e}")

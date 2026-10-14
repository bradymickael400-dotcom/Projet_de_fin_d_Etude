#!/usr/bin/env python3
"""Crée une boîte ARGOS et publie 30 minutes de télémétrie simulée.

Exemple :
  python scripts/simulate_argos_box.py \
    --base-url http://127.0.0.1:5002 --username admin --password secret

Un jeton déjà obtenu peut remplacer les identifiants :
  python scripts/simulate_argos_box.py --token '...'
"""

from __future__ import annotations

import argparse
import array
import glob
import io
import math
import random
import shutil
import signal
import subprocess
import sys
import time
import uuid
import wave
from datetime import datetime, timezone

import requests


ROUTE = (
    ("Yaoundé", 3.8480, 11.5021),
    ("Awaé", 3.8330, 11.6830),
    ("Ayos", 3.9000, 12.5160),
    ("Abong-Mbang", 3.9830, 13.1830),
    ("Doumé", 4.2330, 13.4500),
    ("Bertoua", 4.5770, 13.6846),
)
DEFAULT_DURATION_SECONDS = 30 * 60
DEFAULT_INTERVAL_SECONDS = 2.0


class ApiError(RuntimeError):
    pass


class ComputerSensors:
    """Lecture sans privilèges des capteurs Linux et du microphone.

    Une zone thermique CPU/ACPI n'est pas une sonde d'ambiance. Elle n'est donc
    utilisée que si ``allow_system_temperature`` est demandé explicitement.
    """

    def __init__(self, audio_device: str = "default", microphone: bool = True,
                 audio_backend: str = "auto", temperature_source: str | None = None,
                 allow_system_temperature: bool = False,
                 fixed_temperature: float | None = None):
        self.audio_device = audio_device
        self.microphone = microphone
        self.audio_backend = audio_backend
        self.temperature_source = temperature_source
        self.allow_system_temperature = allow_system_temperature
        self.fixed_temperature = fixed_temperature
        self.sources: set[str] = set()
        self.warnings: set[str] = set()
        self.last_audio_error: str | None = None

    @staticmethod
    def _read_number(patterns: list[str], minimum: float, maximum: float,
                     divisors: tuple[float, ...] = (1.0, 1000.0)) -> float | None:
        for pattern in patterns:
            for path in sorted(glob.glob(pattern)):
                try:
                    raw = float(open(path, encoding="utf-8").read().strip())
                except (OSError, ValueError):
                    continue
                for divisor in divisors:
                    value = raw / divisor
                    if minimum <= value <= maximum:
                        return value
        return None

    @staticmethod
    def _read_temperature_path(path: str) -> float | None:
        try:
            raw = float(open(path, encoding="utf-8").read().strip())
        except (OSError, ValueError):
            return None
        for divisor in (1.0, 1000.0):
            value = raw / divisor
            if -80 <= value <= 120:
                return value
        return None

    def ambient_temperature(self) -> float | None:
        if self.fixed_temperature is not None:
            self.sources.add("température ambiante fournie en option")
            return self.fixed_temperature
        if self.temperature_source:
            value = self._read_temperature_path(self.temperature_source)
            if value is None:
                self.warnings.add(f"sonde de température illisible : {self.temperature_source}")
            else:
                self.sources.add(f"sonde de température ({self.temperature_source})")
            return value

        # Les périphériques IIO sont les candidats les plus plausibles pour une
        # vraie sonde environnementale intégrée/USB.
        value = self._read_number([
            "/sys/bus/iio/devices/iio:device*/in_temp_input",
            "/sys/bus/iio/devices/iio:device*/in_temp_raw",
        ], -80, 120)
        if value is not None:
            self.sources.add("sonde de température ambiante IIO")
            return value

        # hwmon n'est retenu automatiquement que si le libellé dit explicitement
        # qu'il s'agit de l'air/ambiance, jamais pour CPU, GPU, NVMe ou ACPI.
        for label_path in sorted(glob.glob("/sys/class/hwmon/hwmon*/temp*_label")):
            try:
                label = open(label_path, encoding="utf-8").read().strip().lower()
            except OSError:
                continue
            if not any(word in label for word in ("ambient", "air", "room", "external")):
                continue
            input_path = label_path.removesuffix("_label") + "_input"
            value = self._read_temperature_path(input_path)
            if value is not None:
                self.sources.add(f"sonde ambiante hwmon ({label})")
                return value

        if self.allow_system_temperature:
            value = self._read_number([
                "/sys/class/thermal/thermal_zone*/temp",
                "/sys/class/hwmon/hwmon*/temp*_input",
            ], -80, 120)
            if value is not None:
                self.sources.add("température interne ordinateur (non ambiante)")
                self.warnings.add(
                    "la température publiée vient d'un composant interne et ne représente pas précisément la pièce"
                )
                return value
        self.warnings.add(
            "aucune sonde de température ambiante détectée ; la température restera simulée"
        )
        return None

    def _audio_commands(self) -> list[tuple[str, list[str]]]:
        pulse_device = [] if self.audio_device == "default" else ["--device", self.audio_device]
        commands = {
            "alsa": ["arecord", "-q", "-D", self.audio_device, "-t", "raw",
                     "-f", "S16_LE", "-c", "1", "-r", "8000", "-d", "1"],
            "pulse": ["parec", "--raw", "--format=s16le", "--channels=1", "--rate=8000",
                      *pulse_device],
            "pipewire": ["pw-record", "--format", "s16", "--rate", "8000",
                         "--channels", "1", "-"],
        }
        order = ("alsa", "pulse", "pipewire") if self.audio_backend == "auto" else (self.audio_backend,)
        return [(name, commands[name]) for name in order if shutil.which(commands[name][0])]

    @staticmethod
    def _capture(command: list[str], backend: str) -> tuple[bytes, str]:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = process.communicate(timeout=2.2)
        except subprocess.TimeoutExpired:
            # parec/pw-record diffusent en continu : une seconde suffit pour le RMS.
            process.terminate()
            stdout, stderr = process.communicate(timeout=1)
        if process.returncode not in (0, -signal.SIGTERM) or len(stdout) < 800:
            detail = stderr.decode(errors="replace").strip().splitlines()
            raise OSError(detail[-1] if detail else f"capture {backend} vide")
        return stdout[:16000], backend

    def sound_level(self) -> int | None:
        """Capture environ 1 s et convertit le RMS signé 16 bits vers 0–4095."""
        if not self.microphone:
            return None
        errors = []
        for backend, command in self._audio_commands():
            try:
                raw_audio, used_backend = self._capture(command, backend)
            except (subprocess.SubprocessError, OSError) as exc:
                errors.append(f"{backend}: {exc}")
                continue
            samples = array.array("h")
            samples.frombytes(raw_audio[:len(raw_audio) // 2 * 2])
            if sys.byteorder != "little":
                samples.byteswap()
            if not samples:
                continue
            rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
            self.sources.add(f"microphone {used_backend} ({self.audio_device})")
            self.last_audio_error = None
            return max(0, min(4095, round(rms / 32768 * 4095 * 8)))
        self.last_audio_error = "; ".join(errors) or "aucun outil de capture audio installé"
        self.warnings.add(f"microphone inaccessible ({self.last_audio_error}) ; niveau sonore simulé")
        return None

    def capture_wav(self) -> bytes | None:
        """Capture une seconde PCM et l'encapsule en WAV pour l'événement."""
        if not self.microphone:
            return None
        for backend, command in self._audio_commands():
            try:
                raw_audio, _ = self._capture(command, backend)
            except (subprocess.SubprocessError, OSError):
                continue
            output = io.BytesIO()
            with wave.open(output, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(8000)
                wav_file.writeframes(raw_audio)
            return output.getvalue()
        return None

    def acceleration(self) -> tuple[float, float, float] | None:
        for x_path in sorted(glob.glob("/sys/bus/iio/devices/iio:device*/in_accel_x_raw")):
            base = x_path.removesuffix("in_accel_x_raw")
            try:
                raw = [float(open(base + f"in_accel_{axis}_raw", encoding="utf-8").read())
                       for axis in ("x", "y", "z")]
                try:
                    scale = float(open(base + "in_accel_scale", encoding="utf-8").read())
                except OSError:
                    scale = 1.0
                values = tuple(value * scale / 9.80665 for value in raw)
                if all(math.isfinite(value) and abs(value) <= 200 for value in values):
                    self.sources.add("accéléromètre IIO")
                    return values
            except (OSError, ValueError):
                continue
        return None

    def read(self) -> dict:
        measured: dict[str, float | int] = {}
        temperature = self.ambient_temperature()
        if temperature is not None:
            measured["temperature"] = temperature

        battery = self._read_number(
            ["/sys/class/power_supply/BAT*/capacity"], 0, 100, (1.0,)
        )
        if battery is not None:
            measured["battery"] = battery
            self.sources.add("batterie ordinateur")

        light = self._read_number([
            "/sys/bus/iio/devices/iio:device*/in_illuminance_raw",
            "/sys/bus/iio/devices/iio:device*/in_illuminance_input",
        ], 0, 1_000_000, (1.0,))
        if light is not None:
            measured["light"] = min(4095, round(light))
            self.sources.add("capteur de luminosité IIO")

        pressure = self._read_number([
            "/sys/bus/iio/devices/iio:device*/in_pressure_input",
        ], 300, 1200, (1.0, 10.0, 100.0, 1000.0))
        if pressure is not None:
            measured["pressure"] = pressure
            self.sources.add("capteur de pression IIO")

        humidity = self._read_number([
            "/sys/bus/iio/devices/iio:device*/in_humidityrelative_input",
        ], 0, 100, (1.0, 1000.0))
        if humidity is not None:
            measured["humidity"] = humidity
            self.sources.add("capteur d'humidité IIO")

        sound = self.sound_level()
        if sound is not None:
            measured["sound"] = sound
        acceleration = self.acceleration()
        if acceleration is not None:
            measured["accelerationX"], measured["accelerationY"], measured["accelerationZ"] = acceleration
        return measured


class CameraDoorSensor:
    """Déduit l'ouverture de porte d'une webcam volontairement occultée."""

    def __init__(self, device: str = "auto", dark_threshold: float = 12.0,
                 confirmations: int = 2, enabled: bool = True):
        self.device = device
        self.dark_threshold = dark_threshold
        self.confirmations = confirmations
        self.enabled = enabled
        self.dark_count = 0
        self.door_open = False
        self.last_brightness: float | None = None
        self.last_error: str | None = None

    def resolved_device(self) -> str | None:
        if not self.enabled:
            return None
        if self.device != "auto":
            return self.device
        devices = sorted(glob.glob("/dev/video*"))
        return devices[0] if devices else None

    def read(self) -> bool | None:
        device = self.resolved_device()
        if not device:
            self.last_error = "aucune webcam /dev/video* détectée"
            return None
        if not shutil.which("ffmpeg"):
            self.last_error = "ffmpeg absent"
            return None
        command = [
            "ffmpeg", "-loglevel", "error", "-f", "v4l2", "-i", device,
            "-frames:v", "1", "-vf", "scale=160:120,format=gray",
            "-f", "rawvideo", "-",
        ]
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=4, check=True)
            if not result.stdout:
                raise OSError("image vide")
            self.last_brightness = sum(result.stdout) / len(result.stdout)
            self.dark_count = self.dark_count + 1 if self.last_brightness <= self.dark_threshold else 0
            # L'état ouvert n'est validé qu'après plusieurs images noires, mais
            # revient immédiatement à fermé dès que la caméra voit de la lumière.
            self.door_open = self.dark_count >= self.confirmations
            self.last_error = None
            return self.door_open
        except (subprocess.SubprocessError, OSError) as exc:
            self.last_error = str(exc)
            return None


class FirmwareState:
    """État mutable du firmware simulé, piloté par les commandes ARGOS."""

    def __init__(self):
        self.container_id: str | None = None
        self.distance_threshold = 50.0
        self.security_enabled = True
        self.audio_recording_enabled = False
        self.audio_listening_enabled = False
        self.flame_detection_enabled = True
        self.force_alarm_once = False

    def apply(self, command: dict) -> dict:
        command_type = command.get("type")
        payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        if command_type == "ASSIGN_CONTAINER":
            value = payload.get("containerId") or payload.get("container_id")
            if not value:
                raise ValueError("containerId absent")
            self.container_id = str(value).upper()
        elif command_type == "CLEAR_CONTAINER":
            self.container_id = None
        elif command_type == "SET_DISTANCE_THRESHOLD":
            value = float(payload.get("distanceCm"))
            if not 5 <= value <= 400:
                raise ValueError("distanceCm hors limites")
            self.distance_threshold = value
        elif command_type == "SET_SECURITY_MODE":
            self.security_enabled = _command_bool(payload, "enabled")
        elif command_type == "SET_AUDIO_LISTENING":
            self.audio_listening_enabled = _command_bool(payload, "enabled")
        elif command_type == "SET_AUDIO_RECORDING":
            self.audio_recording_enabled = _command_bool(payload, "enabled")
        elif command_type == "SET_FLAME_DETECTION":
            self.flame_detection_enabled = _command_bool(payload, "enabled")
        elif command_type in ("REQUEST_POSITION", "REQUEST_STATUS"):
            pass
        elif command_type == "TRIGGER_LOCAL_ALERT":
            self.force_alarm_once = True
        else:
            raise ValueError(f"commande non supportée : {command_type}")
        return {
            "applied": True,
            "type": command_type,
            "containerId": self.container_id,
            "securityEnabled": self.security_enabled,
            "audioRecordingEnabled": self.audio_recording_enabled,
            "audioListeningEnabled": self.audio_listening_enabled,
            "flameDetectionEnabled": self.flame_detection_enabled,
            "distanceThresholdCm": self.distance_threshold,
        }


def _command_bool(payload: dict, name: str) -> bool:
    value = payload.get(name)
    if not isinstance(value, bool):
        raise ValueError(f"{name} booléen requis")
    return value


def _route_position(progress: float, duration: float) -> dict:
    """Interpole le trajet routier simplifié Yaoundé–Bertoua."""
    progress = max(0.0, min(1.0, progress))
    lengths = []
    for (_, lat1, lon1), (_, lat2, lon2) in zip(ROUTE, ROUTE[1:]):
        mean_lat = math.radians((lat1 + lat2) / 2)
        lengths.append(math.hypot((lat2 - lat1) * 111.32,
                                  (lon2 - lon1) * 111.32 * math.cos(mean_lat)))
    target = progress * sum(lengths)
    travelled = 0.0
    segment = len(lengths) - 1
    ratio = 1.0
    for index, length in enumerate(lengths):
        if target <= travelled + length:
            segment = index
            ratio = (target - travelled) / length if length else 0
            break
        travelled += length
    name1, lat1, lon1 = ROUTE[segment]
    name2, lat2, lon2 = ROUTE[segment + 1]
    latitude = lat1 + (lat2 - lat1) * ratio
    longitude = lon1 + (lon2 - lon1) * ratio
    heading = (math.degrees(math.atan2(
        (lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2)), lat2 - lat1
    )) + 360) % 360
    # Le temps de démonstration est accéléré, mais la télémétrie conserve une
    # vitesse routière crédible afin de ne pas déclencher une survitesse partout.
    speed = 62.0 + 8.0 * math.sin(progress * math.pi * 5)
    return {"latitude": latitude, "longitude": longitude, "heading": heading,
            "speed": speed, "from": name1, "to": name2,
            "nearAbongMbang": abs(progress - sum(lengths[:3]) / sum(lengths)) < 0.018}


def response_json(response: requests.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not response.ok:
        raise ApiError(data.get("error") or f"HTTP {response.status_code}: {response.text[:200]}")
    return data


def login(session: requests.Session, base_url: str, username: str, password: str) -> dict:
    response = session.post(
        f"{base_url}/api/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    data = response_json(response)
    token = data.get("access_token")
    if not token:
        raise ApiError("La connexion n'a renvoyé aucun access_token")
    if data.get("role") not in ("superadmin", "owner"):
        raise ApiError("La création d'une boîte exige un compte superadmin ou propriétaire")
    return data


def create_box(session: requests.Session, base_url: str, owner_id: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "container_id": None,
        "proprietaire_id": owner_id,
        "type_boite": "simulation-30-min",
        "version": "simulator-1.0",
        "battery_capacity": 100,
        "expected_duration": 30,
        "deployment_date": now.date().isoformat(),
        "temp_max": 32,
        "temp_min": -10,
        "humi_max": 75,
        "choc_max": 5,
        "pression_min": 995,
        "vitesse_max": 90,
        "angle_max": 30,
        "distance_cm": 50,
        # Ces valeurs satisfont le contrat de création. Aucun ESP physique
        # n'est contacté : le simulateur utilise directement les identifiants retournés.
        "wifi_ssid": "ARGOS-SIMULATION",
        "wifi_password": "",
        "api_base_url": base_url,
        "access_point_url": "http://192.168.4.1",
        "setup_key": "ARGOS-PROVISION-2026",
    }
    return response_json(session.post(
        f"{base_url}/api/black-boxes/create", json=payload, timeout=30
    ))


def enroll(session: requests.Session, base_url: str, configuration: dict) -> dict:
    return response_json(session.post(
        f"{base_url}/api/iot/enroll",
        json={
            "deviceUid": configuration["deviceUid"],
            "enrollmentToken": configuration["enrollmentToken"],
        },
        timeout=15,
    ))["credentials"]


def telemetry(device_uid: str, black_box_id: int, sequence: int, elapsed: float,
              physical: dict, firmware: FirmwareState, duration: float) -> dict:
    # Variations progressives et bruit léger afin d'obtenir des graphiques réalistes.
    temperature = physical.get("temperature", 27.0 + 1.4 * math.sin(elapsed / 180) + random.uniform(-0.15, 0.15))
    humidity = physical.get("humidity", 68.0 + 3.0 * math.sin(elapsed / 240 + 0.8) + random.uniform(-0.4, 0.4))
    pressure = physical.get("pressure", 1009.0 + 1.2 * math.sin(elapsed / 300) + random.uniform(-0.15, 0.15))
    camera_door = physical.get("doorOpen")
    distance = (firmware.distance_threshold + 20.0 if camera_door else 28.0) + random.uniform(-1.0, 1.0)
    route = _route_position(elapsed / duration, duration)
    if route["nearAbongMbang"]:
        shock = 7.2 + random.uniform(-0.15, 0.15)
    elif "accelerationX" in physical:
        magnitude = math.sqrt(sum(float(physical[key]) ** 2 for key in
                                  ("accelerationX", "accelerationY", "accelerationZ")))
        shock = abs(magnitude - 1.0)
    else:
        shock = max(0.0, random.gauss(0.035, 0.018))
    flame = False
    door_open = bool(camera_door) if camera_door is not None else distance > firmware.distance_threshold
    security_alarm = firmware.force_alarm_once or (
        firmware.security_enabled and (door_open or (firmware.flame_detection_enabled and flame))
    )
    firmware.force_alarm_once = False
    return {
        "messageId": str(uuid.uuid4()),
        "type": "telemetry",
        "deviceUid": device_uid,
        "blackBoxId": black_box_id,
        "containerId": firmware.container_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence,
        "position": {
            "latitude": round(route["latitude"], 6),
            "longitude": round(route["longitude"], 6),
            "accuracy": 5.0,
            "speed": round(route["speed"], 1),
            "heading": round(route["heading"], 1),
            "source": "SIM_YAOUNDE_BERTOUA",
        },
        "sensors": {
            "temperature": round(temperature, 2),
            "humidity": round(humidity, 2),
            "shock": round(shock, 3),
            "pressure": round(pressure, 2),
            "flameDetected": flame,
            "doorOpen": door_open,
            "batteryLevel": round(physical.get("battery", max(85.0, 100.0 - elapsed / 1800 * 2)), 2),
            "lightLevel": physical.get("light", random.randint(500, 650)),
            "soundLevel": physical.get("sound", random.randint(250, 500)),
            "distanceCm": round(distance, 2),
            "accelerationX": round(physical.get("accelerationX", random.gauss(0, 0.012)), 3),
            "accelerationY": round(physical.get("accelerationY", random.gauss(0, 0.012)), 3),
            "accelerationZ": round(physical.get("accelerationZ", 1 + random.gauss(0, 0.015)), 3),
            "securityAlarm": security_alarm,
        },
        "modes": {
            "securityEnabled": firmware.security_enabled,
            "audioRecordingEnabled": firmware.audio_recording_enabled,
            "audioListeningEnabled": firmware.audio_listening_enabled,
            "flameDetectionEnabled": firmware.flame_detection_enabled,
        },
        "quality": {
            "dhtValid": True,
            "mpuValid": True,
            "gpsValid": True,
            "distanceValid": True,
            "sdReady": True,
            "pressureMeasured": True,
            "batteryMeasured": "battery" in physical,
            "timestampSource": "SIMULATOR_SYSTEM_CLOCK",
        },
        "computerSensors": {
            "temperaturePhysical": "temperature" in physical,
            "humidityPhysical": "humidity" in physical,
            "pressurePhysical": "pressure" in physical,
            "batteryPhysical": "battery" in physical,
            "lightPhysical": "light" in physical,
            "microphonePhysical": "sound" in physical,
            "accelerationPhysical": "accelerationX" in physical,
            "doorCameraPhysical": "doorOpen" in physical,
        },
    }


def upload_event_audio(session: requests.Session, base_url: str, api_key: str,
                       device_uid: str, audio_content: bytes,
                       started_at: str) -> str | None:
    response = session.post(
        f"{base_url}/api/iot/audio",
        headers={"X-Device-Key": api_key},
        data={"deviceUid": device_uid, "durationSeconds": "1", "startedAt": started_at},
        files={"audio": ("evenement_abong_mbang.wav", audio_content, "audio/wav")},
        timeout=20,
    )
    return response_json(response).get("recordingUid")


def acknowledge_command(session: requests.Session, base_url: str, api_key: str,
                        device_uid: str, command_uid: str, status: str,
                        result: dict | None = None, error: str | None = None) -> None:
    payload = {
        "commandUid": command_uid,
        "deviceUid": device_uid,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result or {},
    }
    if error:
        payload.update({"errorCode": "SIMULATOR_COMMAND_ERROR", "errorMessage": error})
    response_json(session.post(
        f"{base_url}/api/iot/acknowledgements",
        headers={"X-Device-Key": api_key}, json=payload, timeout=15,
    ))


def poll_commands(session: requests.Session, base_url: str, api_key: str,
                  device_uid: str, firmware: FirmwareState,
                  processed: set[str]) -> None:
    response = session.get(
        f"{base_url}/api/iot/devices/{device_uid}/commands",
        headers={"X-Device-Key": api_key}, timeout=15,
    )
    commands = response_json(response).get("commands", [])
    for command in commands:
        command_uid = str(command.get("commandUid") or "")
        if not command_uid or command_uid in processed:
            continue
        try:
            result = firmware.apply(command)
            acknowledge_command(session, base_url, api_key, device_uid,
                                command_uid, "SUCCEEDED", result=result)
            print(f"[COMMANDE] {command.get('type')} appliquée ({command_uid})")
        except (TypeError, ValueError) as exc:
            acknowledge_command(session, base_url, api_key, device_uid,
                                command_uid, "FAILED", error=str(exc))
            print(f"[COMMANDE] {command.get('type')} échouée : {exc}")
        processed.add(command_uid)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5002")
    parser.add_argument("--username", help="Compte superadmin ou propriétaire")
    parser.add_argument("--password", help="Mot de passe ARGOS")
    parser.add_argument("--token", help="Bearer token ARGOS existant")
    parser.add_argument("--owner-id", help="ID propriétaire à rattacher (utile avec --token)")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_SECONDS,
                        help="Durée en secondes (défaut : 1800)")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS,
                        help="Intervalle entre mesures (défaut : 2 s)")
    parser.add_argument("--audio-device", default="default",
                        help="Source audio ALSA/PulseAudio (défaut : default)")
    parser.add_argument("--audio-backend", choices=("auto", "alsa", "pulse", "pipewire"),
                        default="auto", help="Moteur de capture (défaut : détection automatique)")
    parser.add_argument("--no-microphone", action="store_true",
                        help="Désactive la capture du microphone")
    parser.add_argument("--temperature-source",
                        help="Fichier sysfs d'une vraie sonde ambiante (valeur en °C ou milli-°C)")
    parser.add_argument("--ambient-temperature", type=float,
                        help="Température ambiante fixe si aucune sonde n'est disponible")
    parser.add_argument("--allow-system-temperature", action="store_true",
                        help="Utilise la température CPU/ACPI en dernier recours (non ambiante)")
    parser.add_argument("--camera-device", default="auto",
                        help="Webcam V4L2, ex. /dev/video0 (défaut : détection automatique)")
    parser.add_argument("--camera-dark-threshold", type=float, default=12.0,
                        help="Luminosité 0–255 sous laquelle la caméra est couverte (défaut : 12)")
    parser.add_argument("--camera-confirmations", type=int, default=2,
                        help="Nombre d'images noires avant porte ouverte (défaut : 2)")
    parser.add_argument("--no-camera", action="store_true",
                        help="Désactive le test de porte par webcam")
    parser.add_argument("--check-sensors", action="store_true",
                        help="Teste microphone et température puis quitte, sans contacter ARGOS")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.duration <= 0 or args.interval < 0.2:
        raise ApiError("duration doit être positive et interval >= 0.2 seconde")
    if args.ambient_temperature is not None and not -80 <= args.ambient_temperature <= 120:
        raise ApiError("ambient-temperature doit être comprise entre -80 et 120 °C")
    if not 0 <= args.camera_dark_threshold <= 255 or args.camera_confirmations < 1:
        raise ApiError("seuil caméra invalide ou confirmations inférieures à 1")

    computer = ComputerSensors(
        args.audio_device, not args.no_microphone, args.audio_backend,
        args.temperature_source, args.allow_system_temperature, args.ambient_temperature,
    )
    camera = CameraDoorSensor(
        args.camera_device, args.camera_dark_threshold,
        args.camera_confirmations, not args.no_camera,
    )
    if args.check_sensors:
        measured = computer.read()
        door = camera.read()
        if door is not None:
            measured["doorOpen"] = door
        print("Mesures physiques : " + (str(measured) if measured else "aucune"))
        print("Sources : " + (", ".join(sorted(computer.sources)) or "aucune"))
        if camera.last_brightness is not None:
            print(f"Webcam : luminosité={camera.last_brightness:.1f}/255, porte={'ouverte' if door else 'fermée'}")
        elif not args.no_camera:
            print(f"AVERTISSEMENT : webcam inaccessible ({camera.last_error})")
        for warning in sorted(computer.warnings):
            print(f"AVERTISSEMENT : {warning}")
        return 0 if measured else 2

    if not args.token and not (args.username and args.password):
        raise ApiError("Fournissez --token ou --username et --password")

    base_url = args.base_url.rstrip("/")
    session = requests.Session()
    identity = None if args.token else login(session, base_url, args.username, args.password)
    token = args.token or identity["access_token"]
    owner_id = args.owner_id
    if identity and identity.get("role") == "owner":
        owner_id = identity.get("user_id")
    session.headers.update({"Authorization": f"Bearer {token}"})

    created = create_box(session, base_url, owner_id)
    configuration = created["device_configuration"]
    credentials = enroll(session, base_url, configuration)
    device_uid = credentials["deviceUid"]
    black_box_id = int(credentials["blackBoxId"])
    api_key = credentials["apiKey"]

    print(f"Boîte #{black_box_id} créée — {device_uid}")
    print("Trajet simulé : Yaoundé → Awaé → Ayos → Abong-Mbang → Doumé → Bertoua")
    print(f"Simulation pendant {args.duration}s, une mesure toutes les {args.interval}s")
    first_physical = computer.read()
    first_door = camera.read()
    if first_door is not None:
        first_physical["doorOpen"] = first_door
    if first_physical:
        print("Capteurs physiques détectés : " + ", ".join(sorted(computer.sources)))
    else:
        print("Aucun capteur physique accessible : utilisation des valeurs simulées.")
    if camera.resolved_device():
        print(f"Webcam de porte : {camera.resolved_device()} (couverte = porte ouverte)")
    elif not args.no_camera:
        print(f"AVERTISSEMENT : webcam inaccessible ({camera.last_error})")
    for warning in sorted(computer.warnings):
        print(f"AVERTISSEMENT : {warning}")

    stop = False
    def request_stop(_signum, _frame):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    started = time.monotonic()
    next_send = started
    sequence = 1
    sent = 0
    firmware = FirmwareState()
    processed_commands: set[str] = set()
    event_audio_uploaded = False
    while not stop and time.monotonic() - started < args.duration:
        now = time.monotonic()
        if now < next_send:
            time.sleep(min(0.2, next_send - now))
            continue
        try:
            poll_commands(session, base_url, api_key, device_uid, firmware, processed_commands)
        except (requests.RequestException, ApiError) as exc:
            print(f"AVERTISSEMENT : commandes temporairement indisponibles ({exc})")
        physical = first_physical if sent == 0 else computer.read()
        if sent > 0:
            door = camera.read()
            if door is not None:
                physical["doorOpen"] = door
        payload = telemetry(device_uid, black_box_id, sequence, now - started,
                            physical, firmware, args.duration)
        response = session.post(
            f"{base_url}/api/iot/telemetry",
            headers={"X-Device-Key": api_key},
            json=payload,
            timeout=15,
        )
        data = response_json(response)
        if (not event_audio_uploaded and payload["sensors"]["shock"] > 5
                and firmware.audio_recording_enabled):
            audio_content = computer.capture_wav()
            if audio_content:
                recording_uid = upload_event_audio(
                    session, base_url, api_key, device_uid, audio_content, payload["timestamp"]
                )
                event_audio_uploaded = True
                print(f"[AUDIO] événement d'Abong-Mbang enregistré ({recording_uid})")
            else:
                print("AVERTISSEMENT : choc détecté mais microphone inaccessible pour l'enregistrement")
        sent += 1
        physical_names = ",".join(sorted(physical)) or "aucun"
        print(f"[{sent:04d}] séquence={sequence} HTTP={response.status_code} "
              f"status={data.get('status')} porte={'OUVERTE' if payload['sensors']['doorOpen'] else 'fermée'} "
              f"alarme={'ON' if payload['sensors']['securityAlarm'] else 'off'} physiques={physical_names}")
        sequence += 1
        next_send += args.interval

    print(f"Simulation terminée : {sent} mesures envoyées à la boîte #{black_box_id}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ApiError, requests.RequestException, KeyError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)

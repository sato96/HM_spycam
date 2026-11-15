#!/usr/bin/python3

import threading
import time
from PIL import Image
import numpy as np
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from picamera2.outputs import FileOutput
from libcamera import Transform
from libcamera import controls
import time
import json
from HM_notification import Msg



class spycam(object):
	def __init__(self, th = 7, fileConfig = 'config/config.json'):
		#vanno gestiti e caricati i parametri di luminosità etc
		self._fileName = fileConfig
		self._lsize = (320, 240)
		self.realodConfig()
		self._picam2 = None
		if self._recording:
			t0 = threading.Thread(target=self.start)
			t0.start()
 
	@property
	def thresh(self):
		return self._thresh
	

	@thresh.setter
	def thresh(self, new_value):
		if new_value == "default":
			self._thresh = 25
		else:
			self._thresh = int(new_value)
		j = {"threshold":self._thresh}
		self._saveConfig(j)

	def _saveConfig(self, updates):
		try:
			# Lread existing content
			with open(self._fileName, 'r') as file:
				data = json.load(file)

			# Aupdate only the specified fields
			data.update(updates)

			# wyritre back to the file
			with open(self._fileName, 'w') as file:
				json.dump(data, file, indent=4)
		except FileNotFoundError:
			with open(self._fileName, 'w') as file:
				json.dump(updates, file, indent=4)
		except Exception as e:
			raise Exception(f"Error saving config: {e}")


	def realodConfig(self):
		with open(self._fileName, "r") as file:
			config = json.load(file)	
		self._thresh = config["threshold"]
		self._url = config["url"]
		self._service = config.get("service", "cameraModule")
		self._topic = config["topic"]
		self._sender = Msg(self._service, self._url, self._topic)
		self._recording = False if config.get("status", "off") == "off" else True
		self._timeSleep = config.get("timeSleep", 0.1)
		self._flipImg = config.get("flipImg", False)
		self._colorScheme = config.get("colorScheme", "BW")
		# Rilevamento movimento: 'threshold' = differenza per-pixel (0-255) dopo rimozione luminosita' globale
		self._areaPct = float(config.get("areaPct", 1.5))      # % minima di pixel cambiati
		self._minFrames = int(config.get("minFrames", 2))      # frame consecutivi richiesti
		# regioni da ignorare, coordinate sul frame lores 320x240: [[x0,y0,x1,y1], ...]
		self._ignore = config.get("ignoreRegions", [])
		self._mask = self._buildMask()


	def _prepare(self, y):
		"""Riduce il rumore (media su blocchi 4x4 -> 80x60) e toglie la luminosita' media,
		cosi' le variazioni globali di esposizione/luce non generano falsi positivi."""
		h, w = y.shape
		b = y.astype(np.float32).reshape(h // 4, 4, w // 4, 4).mean(axis=(1, 3))
		return b - b.mean()

	def _buildMask(self):
		mask = np.ones((self._lsize[1] // 4, self._lsize[0] // 4), dtype=bool)
		for x0, y0, x1, y1 in self._ignore:
			mask[int(y0) // 4:-(-int(y1) // 4), int(x0) // 4:-(-int(x1) // 4)] = False
		if not mask.any():  # evita maschera vuota
			mask[:] = True
		return mask

	def getConfig(self):
		with open(self._fileName, 'r') as file:
			return json.load(file)

	def start(self):
		if not self._recording:
			self._recording = True
			self._saveConfig({"status":"on"})
			self._record()
		return True

	def _record(self):	
		self._picam2 = Picamera2()
		color = "YUV420" if self._colorScheme == "BW" else "RGB888"
		video_config = self._picam2.create_video_configuration(
			main={"size": (1280, 720), "format": color}, 
			lores={"size": self._lsize, "format": "YUV420"},  # For motion detection - luminance only
			transform=Transform(vflip=self._flipImg)
		)
		self._picam2.configure(video_config)
		self._encoder = H264Encoder(1000000)	
		self._picam2.start()
		if self._colorScheme == "BW":
			self._picam2.set_controls({
			"Saturation": 0.0,
			"AwbMode": controls.AwbModeEnum.Auto
			})
		time.sleep(2)  # Allow camera to warm up
		w, h = self._lsize
		prev = None
		encoding = False
		ltime = 0
		hits = 0
		encoding_start_time = 0
		max_recording_duration = 30
		try:
			while self._recording:
				try:
					# using YUV420, get only y plane (luminance)
					cur = self._picam2.capture_array("lores")
					# y plane is in the first h rows
					cur = self._prepare(cur[:h, :w])
					
				except Exception as e:
					continue
				
				if prev is not None:
					changed = (np.abs(cur - prev) > self._thresh)[self._mask].mean() * 100
					hits = hits + 1 if changed > self._areaPct else 0
					if hits >= self._minFrames:
						if not encoding:
							video_filename = f"video/motion.mp4"
							self._encoder.output = FfmpegOutput(video_filename)
							self._picam2.start_encoder(self._encoder)
							encoding = True
							encoding_start_time = time.time()
						ltime = time.time()
						if encoding and (time.time() - encoding_start_time) > max_recording_duration:
							self._picam2.stop_encoder()
							encoding = False
							self._sender.video = video_filename
							self._sender.sendMsg()
							time.sleep(2)	
					else:
						if encoding and time.time() - ltime > 2.0:
							self._picam2.stop_encoder()
							encoding = False							
							recording_duration = time.time() - encoding_start_time
							if recording_duration > 1.0:
								self._sender.video = video_filename
								self._sender.sendMsg()
				
				prev = cur.copy()
				time.sleep(self._timeSleep)
				
		except Exception as e:
			if encoding:
				try:
					self._picam2.stop_encoder()
				except:
					pass
		finally:
			self._picam2.stop()
			self._picam2.close()
			self._recording = False

	def stop(self):
		self._recording = False
		self._saveConfig({"status":"off"})

	def pic(self):
		s = None
		try:
			if self._recording:
				if self._colorScheme == "RGB":
					img = self._picam2.capture_image()
					s = img
					#gray_img = img.convert("L")
					#s = gray_img
				else:
					frame = self._picam2.capture_array("main")
            
					# In YUV420, i primi 'altezza' righe sono la luminanza (B/N)
					h, w = 720, 1280 
					y_channel = frame[:h, :w]
					
					# Crea l'immagine PIL direttamente dai dati della luminanza
					s = Image.fromarray(y_channel, mode='L')
			else:
				self._picam2 = Picamera2()
				self._picam2.configure(self._picam2.create_still_configuration(main={"size": (1280, 720)},transform=Transform(vflip=self._flipImg)))
				self._picam2.start()
				time.sleep(1)
				img = self._picam2.capture_image()
				#gray_img = img.convert("L") 
				s = img
				self._picam2.stop()
				self._picam2.close()
				print("Picture taken")
		except Exception as e:
			raise Exception(f"Error capturing image: {e}")
		print(s)
		return s
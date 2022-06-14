import time
from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.frameNbr = 0
		self.lostPacket = 0
		self.receivePacket = 0
		self.packetLossRate = StringVar()
		self.packetLossRate.set("0.0%")
		self.videoDataRate = StringVar()
		self.videoDataRate.set("0.00kps")
		self.fps = StringVar()
		self.fps.set("0.00")
		self.totalDataIn1Sec = 0
		self.counter = 0
		self.connectToServer()
		self.createWidgets()
		self.setupMovie()

	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

        # Create a label to display the packet loss rate
		self.lTitle = LabelFrame(self.master, height=1, text="Packet loss rate")
		self.lTitle.grid(row=3, column=0, columnspan=1, padx=3, pady=3)
  
		self.lossRateLabel = Label(self.lTitle, height=1, textvariable=self.packetLossRate)
		self.lossRateLabel.grid(row=0, column=0, columnspan=1, padx=3, pady=3)

		# Create a label to display the video data rate
		self.vTitle = LabelFrame(self.master, height=1, text="Video data rate")
		self.vTitle.grid(row=3, column=1, columnspan=2, padx=0, pady=0)
  
		self.dataRateLabel = Label(self.vTitle, height=1, textvariable=self.videoDataRate)
		self.dataRateLabel.grid(row=0, column=0, columnspan=2, padx=3, pady=3)
  
  		# Create a label to display the video FPS
		self.vTitle = LabelFrame(self.master, height=30, text="FPS")
		self.vTitle.grid(row=3, column=3, columnspan=10,padx=3, pady=3)
    
		self.fpsLabel = Label(self.vTitle, height=1, textvariable=self.fps)
		self.fpsLabel.grid(row=0, column=10, columnspan=10, padx=3, pady=3)

	def setupMovie(self):
		"""Setup button handler."""
	#TODO
		self.teardownAcked = 0
		self.frameNbr = 0
		if (self.state == self.INIT):
			self.sendRtspRequest(self.SETUP)
	

	def exitClient(self):
		"""Teardown button handler."""
	#TODO
		self.sendRtspRequest(self.TEARDOWN)
		self.master.destroy()

		if self.requestSent != -1:
				filepath = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
				with Image.open(filepath) as im:
					x, y = im.size
				totalsize = x*y
				if totalsize < 2073600:
					os.remove(filepath)


	def pauseMovie(self):
		"""Pause button handler."""
	#TODO
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	

	def playMovie(self):
		"""Play button handler."""
	#TODO
		if self.state == self.READY:
			threading.Thread(target=self.listenRtp).start()
			self.check = threading.Event()
			self.check.clear()
			self.sendRtspRequest(self.PLAY)
	

	def listenRtp(self):		
		"""Listen for RTP packets."""
	#TODO
		self.time = float(time.time())
		while True:
			try:
				datagram = self.rtpSocket.recv(32768)

				if datagram:
					data = RtpPacket()
					data.decode(datagram)
					seq_number_curr = data.seqNum()
					if seq_number_curr > self.frameNbr:
						self.frameNbr = seq_number_curr
						img_file = self.writeFrame(data.getPayload())
						self.updateMovie(img_file)

				# Calculate the packet loss rate
					prev = self.frameNbr
					self.frameNbr = data.seqNum()

					diff = self.frameNbr - prev - 1
					if diff >= 0 :
						self.lostPacket += diff
						if diff == 1:
							print("Lost 1 packet")
						elif diff > 1:
							print("Lost", diff, "packets")
       
					self.receivePacket += 1	
					print("Receive packer number", self.frameNbr)
						
					lostRate = float(self.lostPacket) / (self.lostPacket + self.receivePacket) * 100
					self.packetLossRate.set(str(round(lostRate, 2)) + "%")		

				# Calculate the video data rate and fps
					currTime = float(time.time())
					self.totalDataIn1Sec += len(data.getPacket())
					self.counter += 1
					
					if (currTime - self.time > 1.0) :		
						dataRate = self.totalDataIn1Sec * 8 / (1024 * (currTime - self.time)) 
						fps = self.counter / (currTime - self.time)
						self.videoDataRate.set(str(round(dataRate, 2)) + "kps")
						self.fps.set(str(round(fps, 2)))
						self.time = currTime
						self.totalDataIn1Sec = 0
						self.counter = 0	

			except:
				# Pause listen when choose Pause button
				if self.check.is_set():
					self.totalDataIn1Sec = 0
					self.counter = 0
					break
				# Close socket when choose Teardown button
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					self.teardownAcked = 0
					self.lostPacket = 0
					self.receivePacket = 0
					self.frameNbr = 0
					self.totalDataIn1Sec = 0
					self.counter = 0
					break
		

	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
	#TODO
		img_name = CACHE_FILE_NAME+ str(self.sessionId) + CACHE_FILE_EXT
		with open(img_name,'wb') as file_object:
			file_object.write(data)
		return img_name
	

	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
	#TODO
		img_object = Image.open(imageFile)
		img = ImageTk.PhotoImage(img_object)
		self.label.configure(image=  img, height=300)
		self.label.image = img


	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
	#TODO
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr,self.serverPort))
		except:
			tkinter.messagebox.showwarning('Error',f"Connect to {self.serverAddr} fail")


	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------

		if requestCode == self.SETUP and self.state == self.INIT:
			# Create thread to start receive RTSP reply from server, calling recvRtspReply function
			threading.Thread(target=self.recvRtspReply).start()
			# Update rtspSeq number
			self.rtspSeq += 1
			# Create request to send to server
			request = 'SETUP ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Transport: RTP/UDP; client_port= ' + str(self.rtpPort)

			# Update request to sent to server through requestSent attribute
			self.requestSent = self.SETUP

		elif requestCode == self.PLAY and self.state == self.READY:
			# Update rtspSeq number
			self.rtspSeq += 1

			# Create request to send to server
			request = 'PLAY ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Session: ' + str(self.sessionId)

			# Update request to sent to server through requestSent attribute
			self.requestSent = self.PLAY

		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			self.rtspSeq += 1

			request = 'PAUSE ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Session: ' + str(self.sessionId)

			self.requestSent = self.PAUSE

		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			self.rtspSeq += 1
			request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\n'
			request += 'CSeq: ' + str(self.rtspSeq) + '\n'
			request += 'Session: ' + str(self.sessionId)

			self.requestSent = self.TEARDOWN

		# elif requestCode == self.FORWARD and self.state == self.READY:
		# 	self.rtspSeq += 1
		# 	request = 'FORWARD ' + self.fileName + ' RTSP/1.0'
		# 	request += 'CSeq: ' + str(self.rtspSeq) + '\n'
		# 	request += 'Session: ' + str(self.sessionId)
		# 	self.requestSent = self.FORWARD

		# elif requestCode == self.REWIND and self.state == self.READY:
		# 	self.rtspSeq += 1
		# 	request = 'REWIND ' + self.fileName + ' RTSP/1.0\n'
		# 	request += 'CSeq: ' + str(self.rtspSeq) + '\n'
		# 	request += 'Session: ' + str(self.sessionId)
		# 	self.requestSent = self.REWIND
		else:
			return

		# Send the RTSP request using rtspSocket.
		# self.rtspSocket.send(request.)
		self.rtspSocket.send(request.encode('utf-8'))

		print('\nData sent:\n' + request)
	
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply: 
				self.parseRtspReply(reply.decode("utf-8"))
			
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break


	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""

		lines = data.split('\n')

		if 'Description' in lines[1]:
			for line in lines:
				print(line)
			return

		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						self.state = self.READY
						# Open RTP port.
						self.openRtpPort()
					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING
					elif self.requestSent == self.PAUSE:
						self.state = self.READY
						# The play thread exits. A new thread is created on resume.
						self.check.set()
					elif self.requestSent == self.TEARDOWN:
						self.state = self.INIT
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1
	

	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)

		try:
			# Bind the socket to the address using the RTP port given by the client user
			self.rtpSocket.bind(("", self.rtpPort))
		except:
			tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)
		

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		#TODO
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
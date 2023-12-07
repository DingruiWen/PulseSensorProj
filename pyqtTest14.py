import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene, QLabel
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath, QColor
from PyQt5.QtCore import Qt, QTimer, QPointF
import numpy as np
import random
from PyQt5.QtWidgets import QGraphicsPixmapItem,QMessageBox
from pyqtgraph import PlotWidget
from PyQt5.QtGui import QTransform
from PyQt5.QtCore import QThread,pyqtSignal
import time
import socket
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QRect,QRectF


data = 0
bpm = 0

class BluetoothThread(QThread):
    data_received = pyqtSignal(str)
    
    def run(self):
        global data
        hostMACAddress = 'D8:3A:DD:3C:DF:DE'
        port= 4
        backlog = 1
        size = 1024

        print('Waiting for connection...')
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        print('Socket created')
        s.bind((hostMACAddress, port))
        print('socket bound')
        s.listen(backlog)
        print('heard')

        while 1:
            client, address = s.accept()
            print('client made')
            while 1:
                message = client.recv(size)
                if message:
                    data = int(float(message.decode('utf-8')))
                    print(data)
                    message = 'received'
                    client.send(message.encode())

class HeartRateApp(QMainWindow):
    
    def __init__(self):        
        super().__init__()
        self.initUI()
        self.heart_scale = 1
        self.bluetooth_data = None  

        # Create BluetoothThread
        self.bluetooth_thread = BluetoothThread()
        self.bluetooth_thread.data_received.connect(self.update_bluetooth_data)

        # Start BluetoothThread
        self.bluetooth_thread.start()
        
    def initUI(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # create bpm graph
        self.heart_rate_plot = PlotWidget(self)
        self.heart_rate_plot.hide()
        self.heart_rate_plot.setBackground('w')  # Set background color to white
        self.heart_rate_plot.showGrid(x=True, y=True, alpha=0.5)
        self.heart_rate_plot.plotItem.getAxis('left').setPen('k')  # Set left axis color to black
        self.heart_rate_plot.plotItem.getAxis('bottom').setPen('k')  # Set bottom axis color to black
        layout.addWidget(self.heart_rate_plot)

       
        # create bpm display
        self.heart_scene = QGraphicsScene()
        self.heart_view = QGraphicsView(self.heart_scene)
        initial_bpm = 80  
        self.heart_pixmap = HeartPixmap()
        self.heart_scene.addItem(self.heart_pixmap)
        layout.addWidget(self.heart_view)

         # three labels we show
        self.metrics_label = QLabel('BPM: 0 HRSTD: 0 RMSSD: 0', self)
        layout.addWidget(self.metrics_label)

        # initialize data
        self.bpm_data = np.array([])
        self.show_plot = False

        # start the timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timerEvent)
        self.timer.start(1000)

        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('Heart Rate Monitor')

    def timerEvent(self):
      global data
      try:
          print('This is my data: ', data)
          new_bpm = data
          self.bpm_data = np.append(self.bpm_data, new_bpm)

          if len(self.bpm_data) > 60:
              self.bpm_data = self.bpm_data[-60:]
          self.updateHeartRatePlot()
          self.updateUI()
          self.calculateAndDisplayMetrics()
          self.heart_pixmap.updateBPM(new_bpm)


      except ValueError:
          print("Invalid data received from Bluetooth")

    def update_bluetooth_data(self):
        global data
        self.bluetooth_data = data

    def updateUI(self):
        self.updateHeartRatePlot()
        self.calculateAndDisplayMetrics()
        self.metrics_label.adjustSize()
        
    def updateHeartRatePlot(self):
        self.heart_rate_plot.clear()
        self.heart_rate_plot.plot(self.bpm_data, pen='r')

    def calculateAndDisplayMetrics(self):
        if len(self.bpm_data) > 1:
            bpm = self.bpm_data[-1]
            hrstd = np.std(self.bpm_data)
            rmssd = np.sqrt(np.mean(np.diff(self.bpm_data) ** 2))

            metrics_text = 'BPM: {} HRSTD: {:.2f} RMSSD: {:.2f}'.format(
                int(bpm), hrstd, rmssd
            )
            self.metrics_label.setText(metrics_text)

    def toggleGraphics(self):
        if self.show_plot:
          self.heart_rate_plot.hide()
          self.heart_view.show()
          self.show_plot = False 
        else:
          self.heart_view.hide()
          self.heart_rate_plot.show()
          self.show_plot = True
    def mousePressEvent(self, event):
        self.toggleGraphics()








class HeartPixmap(QGraphicsPixmapItem):
    def __init__(self):
        super().__init__(QPixmap())
        self.setScale(1.0)
        self.drawHeart(1.0)  # 在初始化时调用drawHeart方法以初始化pixmap

    def drawHeart(self, scale):
        global bpm
        pixmap = QPixmap(300, 300)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        heart_path = QPainterPath()
        #change color
        color = self.getColorBasedOnBPM()
        center = pixmap.rect().center()
        radius = int(min(center.x(), center.y()) * scale)

        painter.setBrush(color)

        painter.drawEllipse(center, radius, radius)
        #print number

        bpm_text = str(bpm)  # Assuming `data` contains the BPM value
        font = QFont("Arial", 20)
        painter.setPen(Qt.white)
        painter.setFont(font)
        text_rect = QRect(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
        painter.drawText(text_rect, Qt.AlignCenter, bpm_text)

        # Check BPM condition and display a warning
        if bpm > 100:
            warning_font = QFont("Arial", 20, QFont.Bold)
            painter.setFont(warning_font)
            painter.setPen(Qt.yellow)

            # Adjust the position of the warning text within the bounding rectangle
            warning_text_rect = QRectF(text_rect)
            warning_text_rect.translate(0, 0.5 * radius)

            warning_text = "Caution: BPM exceeds 100!"
            painter.drawText(warning_text_rect, Qt.AlignCenter, warning_text)


        painter.end()

        super().setPixmap(pixmap)

    def getColorBasedOnBPM(self):
        global bpm
        if bpm <= 60:
            return QColor(0, 0, 255)  # Blue for BPM <= 60
        elif bpm <= 100:
            return QColor(0, 255, 0)  # Green for 60 < BPM <= 100
        else:
            return QColor(255, 0, 0)  # Red for BPM > 100

    def updateBPM(self, new_bpm):
        # Update the BPM value and redraw the heart
        global bpm
        bpm = new_bpm
        self.drawHeart(1.0)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeartRateApp()
    ex.show()
    sys.exit(app.exec_())

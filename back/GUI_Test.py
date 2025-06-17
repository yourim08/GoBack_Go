import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QDesktopWidget, QPushButton, QGraphicsDropShadowEffect
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt, QEvent, QPoint, QPropertyAnimation


class MainPage(QWidget) :
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def shadowEffect(widget):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(5) 
        shadow.setXOffset(1)    
        shadow.setYOffset(1.5)  
        shadow.setColor(QColor(0, 0, 0, 38)) # rgba(0,0,0,0.15)
        widget.setGraphicsEffect(shadow)

    def initUI(self):
        self.setWindowTitle("GoBack_Go")       
 
        # 이미지 로드
        self.MainBox = QLabel(self)
        self.HeartUp = QLabel(self)
        self.HeartDown = QLabel(self)
        
        main_box = QPixmap('img/main_box.png') 
        heart_up = QPixmap('img/main_heartUp.png')
        heart_down = QPixmap('img/main_heartDown.png')

        self.MainBox.setPixmap(main_box)
        self.HeartUp.setPixmap(heart_up)
        self.HeartDown.setPixmap(heart_down)

        self.MainBox.setGeometry(668, 186, main_box.width(), main_box.height()) 

        # 애니메이션
        self.heartUp_move = QPropertyAnimation(self.HeartUp, b"pos") 
        self.heartDown_move = QPropertyAnimation(self.HeartDown, b"pos") 
        self.heartUp_move.setDuration(1000)
        self.heartDown_move.setDuration(1000)
            
        self.heartUp_move.setStartValue(QPoint(0, -40)) 
        self.heartDown_move.setStartValue(QPoint(0, 1020))
        self.heartUp_move.setEndValue(QPoint(0, 25)) 
        self.heartDown_move.setEndValue(QPoint(0, 944))

        self.heartUp_move.start()
        self.heartDown_move.start()

        # 버튼
        self.StartBtn = QPushButton("시작하기", self)
        self.LetterBtn = QPushButton("편지보기", self)
        
        self.StartBtn.setStyleSheet("""
            QPushButton {
                border-radius: 30px;
                background: #FFDEE2;
                color: #6C5B5E;
                font-family: NanumMyeongjo;
                font-size: 20px;
                font-style: normal;
                font-weight: 900;
                line-height: normal;
            }
            QPushButton:hover { 
                background: #FFC0CB; 
            }
            QPushButton:pressed { 
                background: #FFA7B9;
            }
        """)

        self.LetterBtn.setStyleSheet("""
            QPushButton {
                border-radius: 30px;
                background: #FEF7CD;
                color: #6C5B5E;
                font-family: NanumMyeongjo;
                font-size: 20px;
                font-style: normal;
                font-weight: 800;
                line-height: normal;
            }
            QPushButton:hover { 
                background: #FFF3AA; 
            }
            QPushButton:pressed { 
                background: #FFA7B9;
            }
        """)    
        self.StartBtn.setGeometry(707, 654, 511, 65) 
        self.LetterBtn.setGeometry(707, 751, 511, 65)
        MainPage.shadowEffect(self.StartBtn)
        MainPage.shadowEffect(self.LetterBtn)
        # 배경색 & 전체화면
        self.setStyleSheet("background-color: #FFF1F3;")         
        self.showFullScreen()

# 실행?
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainPage()
    sys.exit(app.exec_())
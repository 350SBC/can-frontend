import cv2
import sys
from PyQt6.QtWidgets import QWidget, QLabel, QGridLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap


class VideoGridWidget(QWidget):
    def __init__(self, camera_indices=None, update_interval=30, parent=None, auto_detect=True, max_scan=16):
        super().__init__(parent)
        self.auto_detect = auto_detect
        self.max_scan = max_scan
        if camera_indices is None and auto_detect:
            camera_indices = self.detect_cameras(max_scan)
        elif camera_indices is None:
            camera_indices = [0]
        self.camera_indices = camera_indices
        self.captures = []
        self.labels = []
        self.grid = QGridLayout(self)
        self.setLayout(self.grid)
        self._init_cameras()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(update_interval)

    @staticmethod
    def detect_cameras(max_scan=16):
        available = []
        for idx in range(max_scan):
            cap = cv2.VideoCapture(idx)
            if cap is not None and cap.isOpened():
                available.append(idx)
                cap.release()
        return available

    def _init_cameras(self):
        self.captures = []
        self.labels = []
        num_cams = len(self.camera_indices)
        if num_cams == 0:
            label = QLabel(self)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setText("No cameras detected")
            self.labels.append(label)
            self.grid.addWidget(label, 0, 0)
            return
        grid_size = int(num_cams ** 0.5 + 0.9999)  # ceil(sqrt(num_cams))
        for idx, cam_idx in enumerate(self.camera_indices):
            cap = cv2.VideoCapture(cam_idx)
            if cap is not None and cap.isOpened():
                self.captures.append(cap)
                label = QLabel(self)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.labels.append(label)
                row = idx // grid_size
                col = idx % grid_size
                self.grid.addWidget(label, row, col)
            else:
                if cap is not None:
                    cap.release()

    def update_frames(self):
        for cap, label in zip(self.captures, self.labels):
            ret, frame = cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pix = QPixmap.fromImage(img)
                label.setPixmap(pix.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                label.setText("No Signal")

    def closeEvent(self, event):
        for cap in self.captures:
            cap.release()
        event.accept()

    def set_cameras(self, camera_indices):
        # Dynamically change cameras
        for cap in self.captures:
            cap.release()
        for label in self.labels:
            self.grid.removeWidget(label)
            label.deleteLater()
        self.camera_indices = camera_indices
        self._init_cameras()

# Example usage:
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    # Try to open up to 4 cameras (indices 0-3)
    widget = VideoGridWidget(camera_indices=list(range(4)))
    widget.resize(800, 600)
    widget.show()
    sys.exit(app.exec())

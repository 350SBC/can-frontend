import cv2
import sys
from PyQt6.QtWidgets import QWidget, QLabel, QGridLayout, QMenu
from PyQt6.QtGui import QAction
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
        self.layout_mode = "single"  # "single", "1x2", "2x4"
        self.active_camera = 0
        self.grid = QGridLayout(self)
        self.grid.setSpacing(0)
        self.setLayout(self.grid)
        self._init_cameras()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(update_interval)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        if len(self.camera_indices) > 1:
            # Show all layout options except the current one
            layout_options = [
                ("single", "Switch to Single Camera"),
                ("1x2", "Switch to Grid (1x2)"),
                ("2x1", "Switch to Grid (2x1)"),
                ("2x4", "Switch to Grid (2x4)")
            ]
            for mode, label in layout_options:
                if mode != self.layout_mode:
                    action = QAction(label, self)
                    action.triggered.connect(lambda checked, m=mode: self.set_layout_mode(m))
                    menu.addAction(action)
        if self.layout_mode == "single" and len(self.camera_indices) > 1:
            for idx, cam_idx in enumerate(self.camera_indices):
                cam_action = QAction(f"Show Camera {cam_idx}", self)
                cam_action.triggered.connect(lambda checked, i=idx: self.set_active_camera(i))
                menu.addAction(cam_action)
        menu.exec(pos)

    def contextMenuEvent(self, event):
        self.show_context_menu(event.globalPos())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # QMouseEvent: use globalPosition().toPoint()
            self.show_context_menu(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            # In single mode, left click toggles to next camera
            if self.layout_mode == "single":
                if len(self.camera_indices) > 1:
                    self.active_camera = (self.active_camera + 1) % len(self.camera_indices)
                    self._init_cameras()
                else:
                    # Show message if only one camera
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Camera Switch", "No other cameras available to view.")

    def set_layout_mode(self, mode):
        self.layout_mode = mode
        self._init_cameras()

    def set_active_camera(self, idx):
        self.active_camera = idx
        self._init_cameras()

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
        # Release old
        for cap in self.captures:
            cap.release()
        for label in self.labels:
            self.grid.removeWidget(label)
            label.deleteLater()
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
        if self.layout_mode == "single" or num_cams == 1:
            idx = self.active_camera if self.active_camera < num_cams else 0
            cam_idx = self.camera_indices[idx]
            cap = cv2.VideoCapture(cam_idx)
            if cap is not None and cap.isOpened():
                self.captures.append(cap)
                label = QLabel(self)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.labels.append(label)
                self.grid.addWidget(label, 0, 0)
            else:
                if cap is not None:
                    cap.release()
        elif self.layout_mode == "1x2":
            show_cams = self.camera_indices[:2]
            for i, cam_idx in enumerate(show_cams):
                cap = cv2.VideoCapture(cam_idx)
                if cap is not None and cap.isOpened():
                    self.captures.append(cap)
                    label = QLabel(self)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.labels.append(label)
                    self.grid.addWidget(label, 0, i)
                else:
                    if cap is not None:
                        cap.release()
        elif self.layout_mode == "2x1":
            show_cams = self.camera_indices[:2]
            for i, cam_idx in enumerate(show_cams):
                cap = cv2.VideoCapture(cam_idx)
                if cap is not None and cap.isOpened():
                    self.captures.append(cap)
                    label = QLabel(self)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.labels.append(label)
                    self.grid.addWidget(label, i, 0)
                else:
                    if cap is not None:
                        cap.release()
        elif self.layout_mode == "2x4":
            show_cams = self.camera_indices[:8]
            for i, cam_idx in enumerate(show_cams):
                cap = cv2.VideoCapture(cam_idx)
                if cap is not None and cap.isOpened():
                    self.captures.append(cap)
                    label = QLabel(self)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.labels.append(label)
                    row = i // 4
                    col = i % 4
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
                label.setPixmap(pix.scaled(label.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
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

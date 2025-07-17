#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手動標註軟體
使用 PyQt5 開發的圖像標註工具，支援矩形框選、類別選擇、XML儲存等功能。
"""

import sys
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QComboBox, 
                            QFileDialog, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QPixmap, QFont, QColor
from pathlib import Path


class ColorManager:
    """顏色管理器：為每個標註類別分配顏色（排除正紅色 #FF0000）"""
    
    def __init__(self):
        # 預定義的顏色池（排除正紅色）
        self.color_pool = [
            "#3498DB", "#2ECC71", "#F39C12", "#9B59B6", "#E74C3C",
            "#1ABC9C", "#34495E", "#F1C40F", "#E67E22", "#95A5A6",
            "#8E44AD", "#27AE60", "#2980B9", "#D35400", "#7F8C8D",
            "#16A085", "#C0392B", "#8F44AD", "#2C3E50", "#F4D03F"
        ]
        self.category_colors = {}
        
    def get_color_for_category(self, category):
        """為類別分配顏色"""
        if category not in self.category_colors:
            if len(self.category_colors) < len(self.color_pool):
                # 從預定義顏色池中選取
                self.category_colors[category] = self.color_pool[len(self.category_colors)]
            else:
                # 如果類別數量超過預定義顏色，隨機生成（排除正紅色）
                while True:
                    color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
                    if color != "#FF0000":  # 排除正紅色
                        self.category_colors[category] = color
                        break
        return self.category_colors[category]
    
    def get_default_color(self):
        """獲取預設顏色（正紅色）"""
        return "#FF0000"


class AnnotationData:
    """標註資料結構"""
    
    def __init__(self, x, y, width, height, category=""):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.category = category
        
    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'category': self.category
        }


class AnnotationManager:
    """標註管理器：負責儲存/讀取 XML"""
    
    def __init__(self, xml_dir):
        self.xml_dir = Path(xml_dir)
        self.xml_dir.mkdir(exist_ok=True)
    
    def save_annotations(self, image_path, annotations, image_size):
        """儲存標註資料為 XML 檔案"""
        image_name = Path(image_path).name
        xml_path = self.xml_dir / f"{Path(image_path).stem}.xml"
        
        # 建立 XML 結構
        annotation = ET.Element("annotation")
        
        # 新增檔案資訊
        filename = ET.SubElement(annotation, "filename")
        filename.text = image_name
        
        size = ET.SubElement(annotation, "size")
        width = ET.SubElement(size, "width")
        width.text = str(image_size[0])
        height = ET.SubElement(size, "height")
        height.text = str(image_size[1])
        depth = ET.SubElement(size, "depth")
        depth.text = "3"
        
        # 新增物件標註
        for ann in annotations:
            if ann.category:  # 只儲存有類別的標註
                obj = ET.SubElement(annotation, "object")
                
                name = ET.SubElement(obj, "name")
                name.text = ann.category
                
                bndbox = ET.SubElement(obj, "bndbox")
                xmin = ET.SubElement(bndbox, "xmin")
                xmin.text = str(int(ann.x))
                ymin = ET.SubElement(bndbox, "ymin")
                ymin.text = str(int(ann.y))
                xmax = ET.SubElement(bndbox, "xmax")
                xmax.text = str(int(ann.x + ann.width))
                ymax = ET.SubElement(bndbox, "ymax")
                ymax.text = str(int(ann.y + ann.height))
        
        # 美化 XML 並儲存
        rough_string = ET.tostring(annotation, 'unicode')
        reparsed = minidom.parseString(rough_string)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(reparsed.toprettyxml(indent="  "))
    
    def load_annotations(self, image_path):
        """從 XML 檔案載入標註資料"""
        xml_path = self.xml_dir / f"{Path(image_path).stem}.xml"
        annotations = []
        
        if xml_path.exists():
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                for obj in root.findall("object"):
                    name = obj.find("name").text
                    bndbox = obj.find("bndbox")
                    xmin = int(bndbox.find("xmin").text)
                    ymin = int(bndbox.find("ymin").text)
                    xmax = int(bndbox.find("xmax").text)
                    ymax = int(bndbox.find("ymax").text)
                    
                    width = xmax - xmin
                    height = ymax - ymin
                    
                    annotations.append(AnnotationData(xmin, ymin, width, height, name))
            except Exception as e:
                print(f"載入 XML 檔案錯誤: {e}")
        
        return annotations


class ImageCanvas(QWidget):
    """圖片畫布：顯示圖片、處理滑鼠事件、繪製方框"""
    
    annotation_changed = pyqtSignal()  # 標註變更信號
    
    def __init__(self, color_manager):
        super().__init__()
        self.color_manager = color_manager
        self.pixmap = None
        self.annotations = []
        self.current_annotation = None
        self.drawing = False
        self.start_point = QPoint()
        self.selected_category = ""
        
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: white; border: 2px solid #6C584C;")
        
        # 設定可以接收鍵盤事件和焦點
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
    
    def set_image(self, image_path):
        """設定要顯示的圖片"""
        self.pixmap = QPixmap(image_path)
        if self.pixmap.isNull():
            return False
        
        # 縮放圖片以適應畫布
        self.scale_pixmap()
        self.update()
        return True
    
    def scale_pixmap(self):
        """縮放圖片以適應畫布大小"""
        if self.pixmap:
            self.scaled_pixmap = self.pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    def set_annotations(self, annotations):
        """設定標註資料"""
        self.annotations = annotations
        self.update()
    
    def set_selected_category(self, category):
        """設定選中的類別"""
        self.selected_category = category
    
    def get_image_rect(self):
        """獲取圖片在畫布中的實際位置和大小"""
        if not hasattr(self, 'scaled_pixmap'):
            return QRect()
        
        widget_size = self.size()
        pixmap_size = self.scaled_pixmap.size()
        
        x = (widget_size.width() - pixmap_size.width()) // 2
        y = (widget_size.height() - pixmap_size.height()) // 2
        
        return QRect(x, y, pixmap_size.width(), pixmap_size.height())
    
    def widget_to_image_coords(self, widget_point):
        """將畫布座標轉換為圖片座標"""
        if not self.pixmap:
            return QPoint()
        
        image_rect = self.get_image_rect()
        if not image_rect.contains(widget_point):
            return QPoint()
        
        # 計算相對於圖片的座標
        rel_x = widget_point.x() - image_rect.x()
        rel_y = widget_point.y() - image_rect.y()
        
        # 轉換為原始圖片座標
        scale_x = self.pixmap.width() / image_rect.width()
        scale_y = self.pixmap.height() / image_rect.height()
        
        return QPoint(int(rel_x * scale_x), int(rel_y * scale_y))
    
    def image_to_widget_coords(self, image_point):
        """將圖片座標轉換為畫布座標"""
        if not self.pixmap:
            return QPoint()
        
        image_rect = self.get_image_rect()
        
        scale_x = image_rect.width() / self.pixmap.width()
        scale_y = image_rect.height() / self.pixmap.height()
        
        widget_x = int(image_point.x() * scale_x) + image_rect.x()
        widget_y = int(image_point.y() * scale_y) + image_rect.y()
        
        return QPoint(widget_x, widget_y)
    
    def mousePressEvent(self, event):
        """滑鼠按下事件"""
        # 設定焦點以接收鍵盤事件
        self.setFocus()
        
        if event.button() == Qt.LeftButton and self.pixmap:
            # 防呆機制：沒有選擇類別時不能標註
            if not self.selected_category:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self.parent(), "提醒", "請先在右側下拉選單中選擇標註類別！")
                return
            
            image_rect = self.get_image_rect()
            if image_rect.contains(event.pos()):
                self.drawing = True
                self.start_point = event.pos()
                self.current_annotation = None
    
    def mouseMoveEvent(self, event):
        """滑鼠移動事件"""
        if self.drawing and self.pixmap and self.selected_category:
            self.update()
    
    def mouseReleaseEvent(self, event):
        """滑鼠釋放事件"""
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            
            # 防呆機制：確保有選擇類別
            if not self.selected_category:
                self.current_annotation = None
                self.update()
                return
            
            # 計算矩形區域
            end_point = event.pos()
            rect = QRect(self.start_point, end_point).normalized()
            
            # 檢查矩形是否有效（面積大於最小值）
            if rect.width() > 10 and rect.height() > 10:
                # 轉換為圖片座標
                start_img = self.widget_to_image_coords(rect.topLeft())
                end_img = self.widget_to_image_coords(rect.bottomRight())
                
                if not start_img.isNull() and not end_img.isNull():
                    width = abs(end_img.x() - start_img.x())
                    height = abs(end_img.y() - start_img.y())
                    
                    # 建立新標註
                    annotation = AnnotationData(
                        min(start_img.x(), end_img.x()),
                        min(start_img.y(), end_img.y()),
                        width,
                        height,
                        self.selected_category
                    )
                    
                    self.annotations.append(annotation)
                    self.annotation_changed.emit()
            
            self.current_annotation = None
            self.update()
    
    def paintEvent(self, event):
        """繪製事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 繪製圖片
        if hasattr(self, 'scaled_pixmap'):
            image_rect = self.get_image_rect()
            painter.drawPixmap(image_rect, self.scaled_pixmap)
        
        # 繪製已有的標註
        for annotation in self.annotations:
            self.draw_annotation(painter, annotation)
        
        # 繪製正在繪製的矩形
        if self.drawing and self.selected_category:  # 只有選擇類別時才顯示正在繪製的矩形
            current_pos = self.mapFromGlobal(self.cursor().pos())
            rect = QRect(self.start_point, current_pos).normalized()
            
            # 使用選中類別的顏色
            color = self.color_manager.get_color_for_category(self.selected_category)
            
            pen = QPen(QColor(color), 4, Qt.SolidLine)  # 增加線條粗細到4
            painter.setPen(pen)
            painter.drawRect(rect)
    
    def draw_annotation(self, painter, annotation):
        """繪製單個標註"""
        # 轉換為畫布座標
        top_left = self.image_to_widget_coords(QPoint(annotation.x, annotation.y))
        bottom_right = self.image_to_widget_coords(
            QPoint(annotation.x + annotation.width, annotation.y + annotation.height))
        
        rect = QRect(top_left, bottom_right)
        
        # 設定顏色
        if annotation.category:
            color = self.color_manager.get_color_for_category(annotation.category)
        else:
            color = self.color_manager.get_default_color()
        
        pen = QPen(QColor(color), 4, Qt.SolidLine)  # 增加線條粗細到4
        painter.setPen(pen)
        painter.drawRect(rect)
        
        # 繪製類別標籤
        if annotation.category:
            painter.setFont(QFont("Arial", 14, QFont.Bold))  # 增加字體大小和粗體
            painter.setPen(QPen(QColor(color), 2))  # 增加文字筆刷粗細
            painter.drawText(rect.topLeft() + QPoint(4, -8), annotation.category)
    
    def resizeEvent(self, event):
        """視窗大小變更事件"""
        super().resizeEvent(event)
        if self.pixmap:
            self.scale_pixmap()
    
    def keyPressEvent(self, event):
        """鍵盤事件：刪除選中的標註"""
        if event.key() == Qt.Key_Delete and self.annotations:
            # 刪除最後一個標註
            self.annotations.pop()
            self.annotation_changed.emit()
            self.update()
            print(f"已刪除標註，目前標註數量: {len(self.annotations)}")  # 調試用
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """主視窗：處理匯入資料夾、控制按鈕、下拉選單"""
    
    def __init__(self):
        super().__init__()
        self.color_manager = ColorManager()
        self.annotation_manager = None
        self.categories = []
        self.image_list = []
        self.current_image_index = -1
        self.current_folder = ""
        
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        """初始化使用者介面"""
        self.setWindowTitle("Image Labeling Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # 建立主要元件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主要佈局
        main_layout = QHBoxLayout(main_widget)
        
        # 左側圖片區域
        self.image_canvas = ImageCanvas(self.color_manager)
        self.image_canvas.annotation_changed.connect(self.on_annotation_changed)
        
        # 右側控制區域
        control_widget = self.create_control_panel()
        
        # 下方按鈕區域
        bottom_widget = self.create_bottom_panel()
        
        # 佈局設定
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.image_canvas, 1)
        left_layout.addWidget(bottom_widget)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        
        main_layout.addWidget(left_widget, 3)
        main_layout.addWidget(control_widget, 1)
    
    def create_control_panel(self):
        """建立右側控制面板"""
        control_widget = QWidget()
        layout = QVBoxLayout(control_widget)
        layout.setSpacing(15)
        
        # 匯入資料夾按鈕
        self.import_btn = QPushButton("匯入資料夾")
        self.import_btn.setObjectName("importBtn")
        self.import_btn.clicked.connect(self.import_folder)
        layout.addWidget(self.import_btn)
        
        # 類別選擇
        category_title = QLabel("標註類別:")
        category_title.setObjectName("titleLabel")
        layout.addWidget(category_title)
        self.category_combo = QComboBox()
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        layout.addWidget(self.category_combo)
        
        # 當前圖片資訊
        self.image_info_label = QLabel("請先匯入資料夾")
        self.image_info_label.setObjectName("infoLabel")
        layout.addWidget(self.image_info_label)
        
        # 標註統計
        self.annotation_stats_label = QLabel("標註數量: 0")
        self.annotation_stats_label.setObjectName("infoLabel")
        layout.addWidget(self.annotation_stats_label)
        
        # 操作說明
        help_title = QLabel("操作說明:")
        help_title.setObjectName("titleLabel")
        layout.addWidget(help_title)
        
        help_text = QLabel("""1. 先匯入包含label.txt的資料夾
2. 必須選擇標註類別才能標註
3. 滑鼠左鍵拖拽框選區域
4. Delete 鍵刪除最後一個標註
5. 切換圖片時自動儲存""")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        
        layout.addStretch()
        return control_widget
    
    def create_bottom_panel(self):
        """建立下方按鈕面板"""
        bottom_widget = QWidget()
        layout = QHBoxLayout(bottom_widget)
        
        self.prev_btn = QPushButton("上一張")
        self.prev_btn.setObjectName("navBtn")
        self.prev_btn.clicked.connect(self.prev_image)
        self.prev_btn.setEnabled(False)
        
        self.next_btn = QPushButton("下一張")
        self.next_btn.setObjectName("navBtn")
        self.next_btn.clicked.connect(self.next_image)
        self.next_btn.setEnabled(False)
        
        # 完成按鈕（只在最後一張時顯示）
        self.finish_btn = QPushButton("完成標註")
        self.finish_btn.setObjectName("navBtn")
        self.finish_btn.clicked.connect(self.finish_annotation)
        self.finish_btn.setVisible(False)
        
        layout.addWidget(self.prev_btn)
        layout.addStretch()
        layout.addWidget(self.next_btn)
        layout.addWidget(self.finish_btn)
        
        return bottom_widget
    
    def apply_styles(self):
        """套用莫蘭迪色系樣式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #EAE0D5;
                color: #6C584C;
            }
            QPushButton {
                background-color: #A3B18A;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #8F9779;
            }
            QPushButton:pressed {
                background-color: #7A8268;
            }
            QPushButton:disabled {
                background-color: #C4C4C4;
                color: #888888;
            }
            /* 匯入資料夾按鈕特殊樣式 */
            QPushButton#importBtn {
                padding: 20px;
                font-size: 18px;
                min-height: 30px;
            }
            /* 導航按鈕特殊樣式 */
            QPushButton#navBtn {
                padding: 16px 24px;
                font-size: 24px;
                font-weight: bold;
                min-height: 30px;
                min-width: 120px;
            }
            QComboBox {
                background-color: #B7B7A4;
                color: #6C584C;
                border: 2px solid #6C584C;
                padding: 10px;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6C584C;
            }
            QLabel {
                color: #6C584C;
                font-size: 16px;
            }
            /* 標題標籤樣式 */
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #6C584C;
            }
            /* 資訊標籤樣式 */
            QLabel#infoLabel {
                font-size: 16px;
                font-weight: bold;
                color: #6C584C;
            }
        """)
    
    def import_folder(self):
        """匯入資料夾"""
        folder = QFileDialog.getExistingDirectory(self, "選擇資料夾", "")
        if not folder:
            return
        
        self.current_folder = folder
        
        # 檢查必要檔案
        label_file = Path(folder) / "label.txt"
        img_folder = Path(folder) / "img"
        
        if not label_file.exists():
            QMessageBox.warning(self, "錯誤", "找不到 label.txt 檔案！")
            return
        
        if not img_folder.exists():
            QMessageBox.warning(self, "錯誤", "找不到 img 資料夾！")
            return
        
        # 讀取類別
        try:
            with open(label_file, 'r', encoding='utf-8') as f:
                self.categories = [line.strip() for line in f if line.strip()]
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"讀取 label.txt 失敗: {e}")
            return
        
        # 更新類別下拉選單
        self.category_combo.clear()
        self.category_combo.addItem("(請選擇類別)")
        self.category_combo.addItems(self.categories)
        
        # 掃描圖片檔案
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.image_list = []
        
        # 掃描所有圖片檔案（不區分大小寫）
        for file_path in img_folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                self.image_list.append(file_path)
        
        self.image_list.sort()
        
        if not self.image_list:
            QMessageBox.warning(self, "錯誤", "img 資料夾中沒有找到圖片檔案！")
            return
        
        # 初始化標註管理器
        xml_folder = Path(folder) / "xml"
        self.annotation_manager = AnnotationManager(xml_folder)
        
        # 載入第一張圖片
        self.current_image_index = 0
        self.load_current_image()
        
        # 啟用按鈕
        self.update_navigation_buttons()
        
        QMessageBox.information(self, "成功", f"成功載入 {len(self.image_list)} 張圖片和 {len(self.categories)} 個類別！")
    
    def load_current_image(self):
        """載入當前圖片"""
        if self.current_image_index < 0 or self.current_image_index >= len(self.image_list):
            return
        
        # 儲存前一張圖片的標註
        if hasattr(self, 'previous_image_path') and self.annotation_manager:
            self.save_current_annotations()
        
        # 載入新圖片
        image_path = self.image_list[self.current_image_index]
        if self.image_canvas.set_image(str(image_path)):
            # 清空當前標註並載入新的標註
            self.image_canvas.annotations = []  # 先清空標註
            
            if self.annotation_manager:
                annotations = self.annotation_manager.load_annotations(str(image_path))
                self.image_canvas.set_annotations(annotations)
            
            # 重設畫布狀態
            self.image_canvas.drawing = False
            self.image_canvas.current_annotation = None
            
            # 更新介面
            self.update_image_info()
            self.update_annotation_stats()
            self.previous_image_path = str(image_path)
            
            # 強制重繪畫布
            self.image_canvas.update()
    
    def save_current_annotations(self):
        """儲存當前圖片的標註"""
        if (hasattr(self, 'previous_image_path') and 
            self.annotation_manager and 
            hasattr(self.image_canvas, 'pixmap') and 
            self.image_canvas.pixmap):
            
            image_size = (self.image_canvas.pixmap.width(), self.image_canvas.pixmap.height())
            self.annotation_manager.save_annotations(
                self.previous_image_path, 
                self.image_canvas.annotations, 
                image_size
            )
    
    def prev_image(self):
        """上一張圖片"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()
            self.update_navigation_buttons()
    
    def next_image(self):
        """下一張圖片"""
        if self.current_image_index < len(self.image_list) - 1:
            self.current_image_index += 1
            self.load_current_image()
            self.update_navigation_buttons()
    
    def update_navigation_buttons(self):
        """更新導航按鈕狀態"""
        has_images = len(self.image_list) > 0
        is_first = self.current_image_index <= 0
        is_last = self.current_image_index >= len(self.image_list) - 1
        
        self.prev_btn.setEnabled(has_images and not is_first)
        self.next_btn.setEnabled(has_images and not is_last)
        
        # 只在最後一張圖片時顯示完成按鈕
        self.finish_btn.setVisible(has_images and is_last)
    
    def update_image_info(self):
        """更新圖片資訊顯示"""
        if self.image_list:
            current_name = self.image_list[self.current_image_index].name
            info = f"圖片: {current_name}\n({self.current_image_index + 1}/{len(self.image_list)})"
            self.image_info_label.setText(info)
        else:
            self.image_info_label.setText("請先匯入資料夾")
    
    def update_annotation_stats(self):
        """更新標註統計顯示"""
        count = len(self.image_canvas.annotations)
        self.annotation_stats_label.setText(f"標註數量: {count}")
    
    def on_category_changed(self, category):
        """類別選擇變更事件"""
        if category == "(請選擇類別)":
            self.image_canvas.set_selected_category("")
        else:
            self.image_canvas.set_selected_category(category)
    
    def on_annotation_changed(self):
        """標註變更事件"""
        self.update_annotation_stats()
    
    def keyPressEvent(self, event):
        """主視窗鍵盤事件處理"""
        if event.key() == Qt.Key_Delete:
            # 將Delete鍵事件傳遞給圖片畫布
            self.image_canvas.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """關閉程式前儲存當前標註"""
        if hasattr(self, 'previous_image_path') and self.annotation_manager:
            self.save_current_annotations()
        event.accept()

    def finish_annotation(self):
        """完成標註"""
        # 保存當前圖片的標註
        if hasattr(self, 'previous_image_path') and self.annotation_manager:
            self.save_current_annotations()
        
        # 顯示完成訊息
        if self.annotation_manager:
            xml_path = self.annotation_manager.xml_dir
            QMessageBox.information(
                self, 
                "標註完成！", 
                f"所有標註已完成並儲存！\n\nXML 檔案儲存位置:\n{xml_path.absolute()}\n\n程式將重新初始化。"
            )
        
        # 重新初始化程式
        self.reset_to_initial_state()
    
    def reset_to_initial_state(self):
        """重置程式到初始狀態"""
        # 清空所有資料
        self.annotation_manager = None
        self.categories = []
        self.image_list = []
        self.current_image_index = -1
        self.current_folder = ""
        
        # 重置 UI 元件
        self.category_combo.clear()
        self.category_combo.addItem("(請選擇類別)")
        
        # 清空圖片畫布
        self.image_canvas.pixmap = None
        if hasattr(self.image_canvas, 'scaled_pixmap'):
            delattr(self.image_canvas, 'scaled_pixmap')
        self.image_canvas.annotations = []
        self.image_canvas.drawing = False
        self.image_canvas.current_annotation = None
        self.image_canvas.selected_category = ""
        self.image_canvas.update()
        
        # 重置按鈕狀態
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.finish_btn.setVisible(False)
        
        # 重置標籤顯示
        self.image_info_label.setText("請先匯入資料夾")
        self.annotation_stats_label.setText("標註數量: 0")
        
        # 清除previous_image_path
        if hasattr(self, 'previous_image_path'):
            delattr(self, 'previous_image_path')


def main():
    """主程式進入點"""
    app = QApplication(sys.argv)
    app.setApplicationName("Image Labeling Tool")
    
    # 設定應用程式字體
    font = QFont("Microsoft JhengHei", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

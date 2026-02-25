# -*- coding: utf-8 -*-
import sys
import os
import csv
import re
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PIL import Image
import io
import threading  # 用于后台加载
import pandas as pd
from pprint import pprint
import json
import copy
import shutil
import json
import os
import time
from tqdm import tqdm  # pip install tqdm
from typing import Dict, Any, Optional
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
from datetime import datetime
import struct
import binascii
import webbrowser

class ConfigManager:
    """最简配置管理器 - 只管理路径配置"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        # 加载配置
        self.config = self.load_config()
        self.dep_stats_file = "dependency_stats.csv"  # 新增
        # 加载得分配置
        self.score_config = self.config.get('score_weights', self._get_default_score_config())
        
        # 语言配置
        self.language = self.config.get('Eng', 'zh_CN')
        self.language_file = os.path.join(os.getcwd(),"Files",f"{self.language}.xml")

        # 解析后的路径存储
        self.paths: Dict[str, str] = {}
        self._parse_paths()

        # 新增：磁盘检测标志
        self.paths_on_different_drives = self.check_paths_on_different_drives()

    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                raise
    
    def _resolve_variables(self, path: str) -> str:
        """解析路径中的变量 ${variable}"""
        if '${' not in path:
            return path
        
        # 递归替换所有变量
        while '${' in path:
            start = path.find('${')
            end = path.find('}', start)
            if end == -1:
                break
            
            var_name = path[start+2:end]
            # 查找变量值
            var_value = self._get_var_value(var_name)
            if var_value:
                path = path[:start] + var_value + path[end+1:]
            else:
                # 变量未找到，保持原样
                break
        
        return path
    
    def _get_var_value(self, var_name: str) -> Optional[str]:
        """获取变量值"""
        # 优先从paths中查找
        if var_name in self.config.get('paths', {}):
            return self.config['paths'][var_name]
        
        # 特殊处理output_base_dir的变量
        if var_name == 'output_base_dir':
            return self.config.get('paths', {}).get('output_base_dir')
        
        return None
    
    def _parse_paths(self) -> None:
        """解析所有路径"""
        paths_config = self.config.get('paths', {})
        
        for key, raw_path in paths_config.items():
            # 解析变量
            resolved_path = self._resolve_variables(str(raw_path))
            
            # 转换为绝对路径（如果是相对路径）
            if not os.path.isabs(resolved_path):
                resolved_path = os.path.abspath(resolved_path)
            
            # 标准化路径分隔符
            resolved_path = resolved_path.replace('/', '\\')
            
            self.paths[key] = resolved_path
    
    def get_path(self, key: str, default: Optional[str] = None) -> str:
        """获取路径"""
        return self.paths.get(key, default or "")
    def get_current_thumbnail_size(self):
        return self.config['current_thumbnail_size']
    def get_current_HoverImageViewer_size(self):
        return self.config['current_HoverImageViewer_size']

    def get_packages_per_page(self):
        return self.config['packages_per_page']
    def get_window_size(self):
        return [self.config['window']["width"],self.config['window']["height"]]
    def get_columns(self):
        return self.config['columns']
    def get_columns1(self):
        return self.config['columns筛选']
    def max_figuresize(self):
        return self.config['max_figuresize']
    def get_back_ground_color(self):
        return self.config['back_ground_color']
    def get_font_color(self):
        return self.config['font_color']
    def get_font_size(self):
        return self.config['font_size']
    def __getattr__(self, name: str) -> str:
        """通过属性方式访问路径"""
        if name in self.paths:
            return self.paths[name]
        raise AttributeError(f"ConfigManager没有属性 '{name}'")
    def get_dep_stats_path(self):
        """获取依赖统计文件路径"""
        return self.dep_stats_file
    def _get_default_score_config(self):
        """获取默认的得分权重配置"""
        return {
            "no_dependencies": 100,
            "per_reference": 1,
            "per_image": 5,
            
            "tag_weights": {
                "资产": 50,
                "衣服": 50,
                "衣服预设": 10,
                "纹理": 500,
                "皮肤预设": 10,
                "插件": 50,
                "插件预设": 10,
                "姿势": 50,
                "头发": 50,
                "头发预设": 10,
                "外观json": 5,
                "外观预设": 5,
                "声音": 300,
                "场景": 1000,
                "SubScene": 10,
                "General": 10,
                "变形": 100
            }
        }
    
    def get_score_weights(self):
        """获取得分权重配置"""
        return self.score_config
    def set_language(self, language_code: str):
        """设置语言"""
        self.language = language_code
        self.language_file = f"{language_code}.xml"
        
        # 保存到配置文件
        self.config['language'] = language_code
        # self.save_config()

    def check_paths_on_different_drives(self):
        """检查output_base_dir和var_scan_dir是否在不同磁盘"""
        try:
            # 获取磁盘驱动器字母
            def get_drive_letter(path):
                path = os.path.abspath(path)
                # 获取驱动器根目录（如 "C:\"）
                drive = os.path.splitdrive(path)[0]
                return drive.upper()
            
            output_drive = get_drive_letter(self.get_path('output_base_dir', ''))
            var_scan_drive = get_drive_letter(self.get_path('var_scan_dir', ''))
            
            # 如果两个路径都存在且驱动器不同，返回True
            if output_drive and var_scan_drive and output_drive != var_scan_drive:
                # print(f"检测到不同磁盘: output在{output_drive}, VAR在{var_scan_drive}")
                return True
            
            return False
        except Exception as e:
            print(f"检测磁盘时出错: {e}")
            return False
        
    # 添加一个属性方法供外部访问
    def are_paths_on_different_drives(self):
        """获取磁盘检测结果"""
        return self.paths_on_different_drives

class LanguageDialog(QDialog):
    """语言选择对话框"""
    def __init__(self, current_language="zh_CN", parent=None):
        super().__init__(parent)
        self.current_language = current_language
        self.selected_language = current_language
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("选择语言 / Select Language")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        
        # 语言选项
        language_group = QGroupBox("语言 / Language")
        language_layout = QVBoxLayout()
        
        self.chinese_radio = QRadioButton("简体中文 (Simplified Chinese)")
        self.english_radio = QRadioButton("English (英语)")
        
        if self.current_language == "zh_CN":
            self.chinese_radio.setChecked(True)
        else:
            self.english_radio.setChecked(True)
        
        language_layout.addWidget(self.chinese_radio)
        language_layout.addWidget(self.english_radio)
        language_group.setLayout(language_layout)
        
        layout.addWidget(language_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定 / OK")
        cancel_btn = QPushButton("取消 / Cancel")
        
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def accept(self):
        """确认选择"""
        if self.chinese_radio.isChecked():
            self.selected_language = "zh_CN"
        else:
            self.selected_language = "en_US"
        
        super().accept()



class LanguageManager:
    """语言管理器"""
    
    def __init__(self, language_file="zh_CN.xml"):
        self.language_file = language_file
        self.strings: Dict[str, str] = {}
        self.load_language(language_file)
    
    def load_language(self, language_file):
        """加载语言文件"""
        try:
            tree = ET.parse(language_file)
            root = tree.getroot()
            
            # 清空现有字符串
            self.strings.clear()
            
            # 加载所有字符串
            for string_elem in root.findall('string'):
                name = string_elem.get('name')
                text = string_elem.text or ""
                self.strings[name] = text
            
            print(f"Loaded language file: {language_file}, {len(self.strings)} strings")
            
        except Exception as e:
            print(f"Error loading language file {language_file}: {e}")
            # 如果加载失败，使用默认字符串
            self.load_default_strings()
    
    def load_default_strings(self):
        """加载默认字符串（中文）"""
        self.strings = {
            'window_title': 'Virt-A-Mate Supernova',
            'search_placeholder': '搜索包名、作者或标签...',
            'sort_label': '排序:',
            # ... 其他默认字符串 ...
        }
    
    def get_text(self, key: str, *args) -> str:
        """获取翻译文本，支持格式化参数"""
        if key in self.strings:
            text = self.strings[key]
            try:
                return text.format(*args)
            except:
                return text
        else:
            return f"[{key}]"
    
    def switch_language(self, language_code: str):
        """切换语言"""
        language_files = {
            'zh_CN': 'zh_CN.xml',
            'en_US': 'en_US.xml'
        }
        
        if language_code in language_files:
            self.load_language(language_files[language_code])
            return True
        return False

class ThumbnailWidget(QWidget):
    """缩略图控件 - 使用原始尺寸"""
    clicked = pyqtSignal(str)
    size_changed = pyqtSignal()  # 新增：大小改变信号

    def __init__(self, image_path, package_name, author, tags, image_count, dep_count, version, 
                 reference_count=0, score=0,processed_time="", parent=None):  # 新增score参数
        super().__init__()
        self.config = ConfigManager("config.json")
        self.image_path = image_path
        self.package_name = package_name
        self.author = author
        self.tags = tags
        self.image_count = image_count
        self.dep_count = dep_count
        self.version = version
        self.is_selected = False  # 新增：选择状态
        self.full_identifier = f"{author}.{package_name}.{version}"  # 新增：完整标识符
        self.target_size = self.config.get_current_thumbnail_size()  # 默认大小
        # 加载AI特征
        self.ai_features = self.load_ai_features()
        self.ai_description = self.get_ai_description()  # 获取AI描述

        # 新增：悬停相关属性
        self.hover_viewer = None  # 悬停时显示的图片查看器
        self.hover_timer = QTimer()  # 用于延迟显示
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.show_hover_viewer)
        # 新增：悬停控制属性
        self._hover_enabled = True  # 默认为启用
        self._hover_blocked = False  # 新增：悬停是否被阻止
        self._hover_viewer_open = False  # 新增：悬停查看器是否已打开
        self._in_image_label = False  # 新增：标记鼠标是否在图片标签区域内

        self.data_dir = "data"
        self.reference_count = reference_count  # 新增：引用次数
        self.parent_window = parent  # 保存父窗口引用
        self.score = score  # 新增：包的得分

        # 新增：分析类别相关属性
        self.analysis_tags = []
        self.analysis_text = ""
        self.load_analysis_tags()  # 加载分析标签

        # 新增：分析类别相关属性
        self.analysis_tags = []
        self.analysis_text = ""
        self.creation_date = ""  # 新增：创建日期
        self.load_analysis_tags()  # 加载分析标签和日

        # 新增：处理时间
        self.processed_time = processed_time

        self.initUI()
        
    def initUI(self):
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)
        # 设置父控件的背景色

        # 添加选择按钮（位于右上角）
        self.select_btn = QCheckBox()
        self.select_btn.setFixedSize(50, 50)
        self.select_btn.setStyleSheet("""
        QCheckBox {
            background-color: rgba(255, 255, 255, 200);
            border: 3px solid #0078d7;
            border-radius: 6px;
        }
        QCheckBox::indicator {
            width: 50px;
            height: 50px;
            border-radius: 0px;
        }
        QCheckBox::indicator:unchecked {
            background-color: white;
            border: 50px solid #999;
        }
        QCheckBox::indicator:checked {
            background-color: #0078d7;
            border: 50px solid #0056b3;
        }
    """)
        self.select_btn.stateChanged.connect(self.on_select_changed)
        
        # 使用覆盖布局将按钮放在右上角
        overlay_widget = QWidget()
        overlay_layout = QVBoxLayout(overlay_widget)
        overlay_layout.setContentsMargins(0, 0, 0, 0)

        
        # 将按钮放在右上角
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.select_btn)
        overlay_layout.addLayout(button_layout)
        
        # 图片标签 - 不设置固定尺寸，根据图片自适应
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.mousePressEvent = self.mouse_press_event
        # 重写 enterEvent 和 leaveEvent
        self.image_label.enterEvent = self.image_label_enter_event
        self.image_label.leaveEvent = self.image_label_leave_event
        overlay_layout.addWidget(self.image_label, 1)
        
        layout.addWidget(overlay_widget, 0, Qt.AlignCenter)
        
        # 包名
        self.name_label = QLabel(self.package_name+f".{self.version}")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.name_label.mousePressEvent = lambda e: self.copy_to_clipboard(self.author+"."+self.package_name+f".{self.version}")
        layout.addWidget(self.name_label)
        
        # 作者
        self.author_label = QLabel(f"作者: {self.author}")
        self.author_label.setAlignment(Qt.AlignCenter)
        self.author_label.setStyleSheet("font-size: 15px;")
        self.author_label.mousePressEvent = lambda e: self.copy_to_clipboard(self.author)
        layout.addWidget(self.author_label)
        
        # 在统计信息部分添加引用次数显示
        # 新增：被引用次数
        self.ref_label = QLabel(f"⭐ {self.reference_count}")
        self.ref_label.setStyleSheet("font-size: 15px; color: #ff9900;")
        self.ref_label.setToolTip(f"被 {self.reference_count} 个其他包引用")
        self.ref_label.mousePressEvent = lambda e: self.show_reference_popup()

        # 标签
        tags_text = self.format_tags(self.tags)
        self.tags_label = QLabel(f"标签: {tags_text}")
        self.tags_label.setAlignment(Qt.AlignCenter)
        self.tags_label.setWordWrap(True)
        self.tags_label.setStyleSheet("font-size: 15px;")
        self.tags_label.mousePressEvent = lambda e: self.copy_to_clipboard(tags_text)
        layout.addWidget(self.tags_label)
        
        # +++ 新增：AI特征描述 +++
        if self.ai_description:
            self.ai_label = QLabel(f"AI特征: {self.ai_description}")
            self.ai_label.setAlignment(Qt.AlignCenter)
            self.ai_label.setWordWrap(True)  # 允许换行
            self.ai_label.setMaximumHeight(60)  # 限制高度，防止占用太多空间
            self.ai_label.setStyleSheet("""
                font-size: 15px; 
                border-radius: 4px; 
                padding: 14px;
                margin: 0px;
            """)
            # 添加工具提示显示完整描述
            full_desc = self.ai_features.get(f".{self.full_identifier}", "") or \
                       self.ai_features.get(self.full_identifier, "")
            if full_desc:
                self.ai_label.setToolTip(full_desc)
            self.ai_label.mousePressEvent = lambda e: self.copy_to_clipboard(self.ai_description)
            layout.addWidget(self.ai_label)
        else:
            # 如果没有AI描述，显示占位符（可选）
            self.ai_label = QLabel("")
            layout.addWidget(self.ai_label)

        # 统计信息
        stats_layout = QHBoxLayout()
        stats_layout.addStretch()
        self.count_label = QLabel(f"📸 {self.image_count}")
        self.count_label.setStyleSheet("font-size: 15px; color: #0078d7;")
        self.dep_label = QLabel(f"🔗 {self.dep_count}")
        self.dep_label.setStyleSheet("font-size: 15px; color: #0078d7;")

        # 修改为：
        self.dep_label = QLabel(f"🔗 {self.dep_count}")
        self.dep_label.setStyleSheet("font-size: 15px; color: #0078d7;")
        self.dep_label.setToolTip(f"有 {self.dep_count} 个依赖项")
        self.dep_label.mousePressEvent = lambda e: self.show_dependency_details()

         # +++ 新增：得分显示 +++
        self.score_label = QLabel(f"得分: {self.score}")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                background: linear-gradient(135deg, #ffd700, #ffa500);
                padding: 5px 10px;
                border-radius: 12px;
                border: 2px solid #ff8c00;
            }
        """)
        # 设置工具提示显示得分详情
        self.score_label.setToolTip("点击查看得分详情")
        self.score_label.mousePressEvent = lambda e: self.show_score_details()
        layout.addWidget(self.score_label)

         # +++ 新增：分析类别显示 +++
        self.analysis_label = QLabel(self.analysis_text)
        self.analysis_label.setAlignment(Qt.AlignCenter)
        self.analysis_label.setWordWrap(True)  # 允许换行
        self.analysis_label.setMaximumHeight(40)  # 限制高度
        self.analysis_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #6610f2;
                background: linear-gradient(135deg, #f0f0ff, #e0e0ff);
                padding: 4px 8px;
                border-radius: 8px;
                border: 1px solid #c0c0ff;
                margin-top: 3px;
                margin-bottom: 5px;
                font-weight: bold;
            }
            QLabel:hover {
                background: linear-gradient(135deg, #e0e0ff, #d0d0ff);
                border: 1px solid #a0a0ff;
            }
        """)

        # +++ 新增：创建日期显示 +++
        formatted_date = self.format_creation_date(self.creation_date)
        self.date_label = QLabel(f"📅 {formatted_date}")
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #17a2b8;
                background: linear-gradient(135deg, #f0fdff, #e0f7ff);
                padding: 3px 6px;
                border-radius: 6px;
                border: 1px solid #b3ecff;
                margin-top: 2px;
                font-weight: bold;
            }
            QLabel:hover {
                background: linear-gradient(135deg, #e0f7ff, #d0f0ff);
                border: 1px solid #99e6ff;
            }
        """)

        # 在处理时间后面添加显示
        self.processed_time_label = QLabel(f"添加日期: {self.format_processed_time(self.processed_time)}")
        self.processed_time_label.setAlignment(Qt.AlignCenter)
        self.processed_time_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #17a2b8;
                background: linear-gradient(135deg, #f0fdff, #e0f7ff);
                padding: 3px 6px;
                border-radius: 6px;
                border: 1px solid #b3ecff;
                margin-top: 2px;
                font-weight: bold;
            }
            QLabel:hover {
                background: linear-gradient(135deg, #e0f7ff, #d0f0ff);
                border: 1px solid #99e6ff;
            }
        """)

        stats_layout.addWidget(self.count_label)
        stats_layout.addWidget(QLabel(" | "))
        stats_layout.addWidget(self.dep_label)
        stats_layout.addStretch()
        stats_layout.addWidget(QLabel(" | "))
        stats_layout.addWidget(self.ref_label)
        layout.addWidget(self.analysis_label)
        layout.addWidget(self.date_label)
        layout.addWidget(self.processed_time_label)
        layout.addLayout(stats_layout)
        


        self.load_image()
        # 设置控件样式
        self.update_style()

    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(str(text))
        
        # 可选：显示一个简短的提示
        # 可以使用状态栏或者一个小弹窗，这里使用简单的方式
        print(f"已复制到剪贴板: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        # 或者添加一个视觉反馈（改变背景色）
        sender = self.sender() if hasattr(self, 'sender') else None
        if sender and hasattr(sender, 'setStyleSheet'):
            original_style = sender.styleSheet()
            sender.setStyleSheet(original_style + " background-color: #e8f4ff;")
            QTimer.singleShot(300, lambda: sender.setStyleSheet(original_style))

    def update_style(self):
        """更新控件样式"""
        if self.is_selected:
            self.setStyleSheet("""
                QWidget {
                    background: linear-gradient(135deg, #e8f4ff, #d4ebff);
                    border: 3px solid #0078d7;
                    border-radius: 10px;
                }
                QLabel {
                    font-weight: bold;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background: white;
                    border: 2px solid #e0e0e0;
                    border-radius: 10px;
                }
                QWidget:hover {
                    border: 2px solid #0078d7;
                }
            """)

    def set_target_size(self, size):
        """设置目标大小"""
        self.target_size = size
        self.load_image()
        self.size_changed.emit()  # 发出大小改变信号

    def format_tags(self, tags_str):
        if not tags_str or tags_str == "无":
            return "无"
        tags = [tag.strip() for tag in tags_str.split(',')]
        if len(tags) > 5:  # 显示更多标签
            return ",".join(tags[:5]) + "..."
        return ",".join(tags)
    
    def load_image(self):
        if self.image_path and os.path.exists(self.image_path):
            try:
                # 使用QPixmap直接加载
                pixmap = QPixmap(self.image_path)
                
                if not pixmap.isNull():
                    original_size = pixmap.size()
                    
                    # 根据目标大小计算缩放
                    if original_size.width() > original_size.height():
                        # 宽图
                        new_width = self.target_size
                        new_height = int(original_size.height() * (self.target_size / original_size.width()))
                    else:
                        # 高图或方图
                        new_height = self.target_size
                        new_width = int(original_size.width() * (self.target_size / original_size.height()))
                    
                    # 确保最小尺寸
                    new_width = max(new_width, 100)
                    new_height = max(new_height, 100)
                    
                    # 缩放图片
                    scaled_pixmap = pixmap.scaled(
                        new_width, 
                        new_height, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled_pixmap)
                    self.image_label.setFixedSize(new_width, new_height)
                    
                    # 保存原始图片信息用于显示
                    self.image_label.setToolTip(f"原始尺寸: {original_size.width()}x{original_size.height()}")
                else:
                    self.show_placeholder()
            except Exception as e:
                print(f"加载图片失败: {e}")
                self.show_placeholder()
        else:
            self.show_placeholder()

    
    def show_placeholder(self):
        """显示占位图"""
        # 根据目标大小创建占位图
        placeholder_size = self.target_size
        
        # 创建占位图
        placeholder = QPixmap(placeholder_size, placeholder_size)
        placeholder.fill(QColor(240, 240, 240))
        
        painter = QPainter(placeholder)
        
        # 绘制边框
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawRect(10, 10, placeholder_size - 20, placeholder_size - 20)
        
        # 绘制图标
        font = painter.font()
        font_size = max(24, placeholder_size // 15)  # 根据大小调整字体
        font.setPointSize(font_size)
        painter.setFont(font)
        painter.setPen(QColor(180, 180, 180))
        
        # 计算文字位置
        painter.drawText(placeholder.rect(), Qt.AlignCenter, "📷")
        
        # 绘制文字
        font.setPointSize(max(10, placeholder_size // 40))
        painter.setFont(font)
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(QRect(0, placeholder_size - 40, placeholder_size, 30), 
                        Qt.AlignCenter, "无预览图")
        
        painter.end()
        
        self.image_label.setPixmap(placeholder)
        self.image_label.setFixedSize(placeholder_size, placeholder_size)
    
    def mouse_press_event(self, event):
        self.clicked.emit(self.image_path)
    
    def on_select_changed(self, state):
        """选择状态改变"""
        self.is_selected = (state == Qt.Checked)
        self.update_selection_style()

    def update_selection_style(self):
        """更新选择样式"""
        if self.is_selected:
            self.setStyleSheet("""
                QWidget {
                    background: linear-gradient(135deg, #e8f4ff, #d4ebff);
                    border: 3px solid #0078d7;
                    border-radius: 10px;
                }
                QLabel {
                    font-weight: bold;
                }
                QCheckBox {
                    border: 2px solid #0056b3;
                }
            """)
            # 添加选中标记
            self.name_label.setText(f"✓ {self.package_name}.{self.version}")
        else:
            self.setStyleSheet("""
                QWidget {
                    background: white;
                    border: 2px solid #e0e0e0;
                    border-radius: 10px;
                }
                QWidget:hover {
                    border: 2px solid #0078d7;
                }
            """)
            # 恢复原始文本
            self.name_label.setText(f"{self.package_name}.{self.version}")
    
    def load_ai_features(self):
        """加载AI特征文件"""
        ai_feature_file = os.path.join(os.getcwd(), "Files", "AI_包特征.txt")
        ai_features = {}
        
        if os.path.exists(ai_feature_file):
            try:
                with open(ai_feature_file, 'r', encoding='gb18030') as f:
                    lines = f.readlines()
                    
                    for line in lines:
                        line = line.strip()
                        if line:  # 以点开头的是包标识符
                            parts = line.split(':', 1)  # 只分割第一个冒号
                            if len(parts) == 2:
                                # print(parts)
                                pkg_id = parts[0].strip()
                                description = parts[1].strip()
                                ai_features[pkg_id] = description
                                
            except Exception as e:
                print(f"加载AI特征文件失败: {e}")
                
        return ai_features
    
    def get_ai_description(self):
        """获取当前包的AI描述"""
        # 尝试不同的标识符格式
        possible_ids = [
        f".{self.full_identifier}",           # 带点的格式：.author.package_name.version
        f"{self.full_identifier}",            # 不带点的格式：author.package_name.version
        f".{self.package_name}.{self.version}", # 可能不包含作者的带点格式
        f"{self.package_name}.{self.version}",  # 可能不包含作者的不带点格式
        ]
        for pkg_id in possible_ids:
            # print(pkg_id)
            if pkg_id in self.ai_features:
                description = self.ai_features[pkg_id]
                # 如果描述太长，进行截断
                # if len(description) > 80:
                #     description = description[:77] + "..."
                return description
        
        return None  # 没有找到对应的描述
    
    def image_label_enter_event(self, event):
        """image_label的鼠标进入事件"""
        super(QLabel, self.image_label).enterEvent(event)
        
        # 标记鼠标进入图片标签区域
        self._in_image_label = True
        
        # 如果悬停被禁用或被阻止，直接返回
        if not self._hover_enabled or self._hover_blocked or self._hover_viewer_open:
            return
        
        # 如果图片数量小于1000，启动计时器显示查看器
        if int(self.image_count) > 0 and int(self.image_count) < 2000:
            self.hover_timer.start(500)  # 500毫秒后显示，避免过于敏感

    def image_label_leave_event(self, event):
        """image_label的鼠标离开事件"""
        super(QLabel, self.image_label).leaveEvent(event)
        
        # 标记鼠标离开图片标签区域
        self._in_image_label = False
        
        # 停止计时器
        if hasattr(self, 'hover_timer'):
            self.hover_timer.stop()
        
        # 延迟检查是否需要关闭悬停查看器
        QTimer.singleShot(300, self.check_close_hover_viewer)
    
    def check_close_hover_viewer(self):
        """检查是否需要关闭悬停查看器"""
        # 如果鼠标已经离开图片标签区域，并且悬停查看器已打开，则关闭它
        if not self._in_image_label and self._hover_viewer_open and self.hover_viewer:
            # 检查鼠标是否在悬停查看器上
            cursor_pos = QCursor.pos()
            if self.hover_viewer:
                viewer_rect = self.hover_viewer.geometry()
                viewer_rect_with_margin = viewer_rect.adjusted(-20, -20, 20, 20)  # 增加一些边界容差
                
                if not viewer_rect_with_margin.contains(cursor_pos):
                    self.close_hover_viewer()

    def show_hover_viewer(self):
        """显示悬停查看器 - 限制在image_label范围内"""
        # 如果悬停被禁用或被阻止，直接返回
        if not self._hover_enabled or self._hover_blocked or self._hover_viewer_open:
            return

        # 检查鼠标是否仍在image_label区域内
        if not self._in_image_label:
            return

        # 获取包的所有图片
        images, image_types = self.get_package_images()
        
        if not images:
            print("没有找到图片")
            return
        
        print(f"显示悬停查看器，图片数量: {len(images)}")
        
        # 标记悬停查看器已打开
        self._hover_viewer_open = True
        
        # 创建查看器，传递当前widget作为parent
        self.hover_viewer = HoverImageViewer(images, image_types, self)
        
        # 获取鼠标位置
        cursor_pos = QCursor.pos()
        
        # 获取屏幕大小
        screen = QApplication.primaryScreen().availableGeometry()
        
        # 计算窗口位置（在鼠标下方显示）
        viewer_size = self.hover_viewer.size()
        
        # 获取image_label的全局位置
        label_global_pos = self.image_label.mapToGlobal(QPoint(0, 0))
        
        # 计算位置：在image_label下方显示
        x = max(0, min(cursor_pos.x() - viewer_size.width() // 2, screen.width() - viewer_size.width()))
        y = max(0, min(cursor_pos.y() - viewer_size.height() // 2, screen.height() - viewer_size.height()))

        
        # 移动窗口到指定位置
        self.hover_viewer.move(x, y)
        
        # 连接悬停查看器关闭信号
        self.hover_viewer.viewer_closed.connect(self.on_hover_viewer_closed)
        
        # 显示窗口
        self.hover_viewer.show()

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.image_path)

    def get_package_images(self):
        """获取当前包的所有图片"""
        images = []
        image_types = []
        
        if not self.package_name or not os.path.exists(self.data_dir):
            return images, image_types
            
        package_dir = os.path.join(self.data_dir, f"{self.author}_{self.package_name}_")
        if not os.path.exists(package_dir):
            return images, image_types
        
        type_mapping = {
            'subscene': 'subscene',
            'clothing_preset': '衣服预设',
            r'hair\preset': '头发预设',
            'skin': '皮肤预设',
            'scene': '场景',
            'clothing': '衣服',
            'hair': '头发',
            'pose': '姿势',
            'appearance': '外观预设',
            'texture': '纹理',
            'plugin': '插件',
            'assets': '资产'
        }
        
        # 限制搜索深度，提高性能
        max_depth = 2000
        def search_images(root, depth=0):
            if depth > max_depth:
                return
                
            try:
                for entry in os.listdir(root):
                    full_path = os.path.join(root, entry)
                    if os.path.isdir(full_path):
                        search_images(full_path, depth + 1)
                    elif entry.lower().endswith(('.jpg', '.jpeg', '.png')):
                        images.append(full_path)
                        
                        # 确定图片类型
                        img_lower = full_path.lower()
                        img_type = "其他"
                        for keyword, type_name in type_mapping.items():
                            if keyword in img_lower:
                                img_type = type_name
                                break
                        image_types.append(img_type)
            except:
                pass
        
        search_images(package_dir)
        return images, image_types

    def on_hover_viewer_closed(self):
        """悬停查看器关闭时的处理"""
        print("悬停查看器已关闭")
        self._hover_viewer_open = False
        self._hover_blocked = True  # 暂时阻止悬停检测
        
        # 延迟一段时间后重新启用悬停检测，防止立即再次触发
        QTimer.singleShot(500, self.enable_hover_detection)

    def enable_hover_detection(self):
        """重新启用悬停检测"""
        self._hover_blocked = False
        print("悬停检测已重新启用")

    def close_hover_viewer(self):
        """关闭悬停查看器"""
        if hasattr(self, 'hover_viewer') and self.hover_viewer:
            # 如果悬停查看器还处于打开状态，先关闭它
            if self._hover_viewer_open:
                self.hover_viewer.close_viewer()
            else:
                self.hover_viewer.close()
                self.hover_viewer.deleteLater()
                self.hover_viewer = None

    def enable_hover_viewer(self, enabled=True):
        """启用或禁用悬停查看器"""
        self._hover_enabled = enabled
        
        if not enabled and hasattr(self, 'hover_viewer') and self.hover_viewer:
            self.close_hover_viewer()

    def show_reference_details(self, event=None):
            """显示引用详情"""
            if self.parent_window and hasattr(self.parent_window, 'show_reference_details_window'):
                self.parent_window.show_reference_details_window(
                    self.author, self.package_name, self.reference_count
                )
            elif hasattr(self, 'parent') and self.parent():
                # 尝试找到主窗口
                main_window = self.find_main_window()
                if main_window and hasattr(main_window, 'show_reference_details_window'):
                    main_window.show_reference_details_window(
                        self.author, self.package_name, self.reference_count
                    )
    
    def find_main_window(self):
        """递归查找主窗口"""
        parent = self.parent()
        while parent:
            if isinstance(parent, VARManager):
                return parent
            parent = parent.parent()
        return None

    def show_reference_popup(self):
        """显示引用次数的弹出提示"""
        msg = f"被 {self.reference_count} 个其他包引用"
        if self.reference_count > 0:
            # 可以在这里调用父窗口的show_reference_details方法
            if self.parent_window and hasattr(self.parent_window, 'show_reference_details'):
                self.parent_window.show_reference_details(self.author, self.package_name)
    
    def show_dependency_details(self, event=None):
        """显示依赖详情"""
        if self.parent_window and hasattr(self.parent_window, 'show_dependency_details_window'):
            self.parent_window.show_dependency_details_window(
                self.author, self.package_name, self.dep_count
            )
        elif hasattr(self, 'parent') and self.parent():
            # 尝试找到主窗口
            main_window = self.find_main_window()
            if main_window and hasattr(main_window, 'show_dependency_details_window'):
                main_window.show_dependency_details_window(
                    self.author, self.package_name, self.dep_count
                )
    # 在ThumbnailWidget类中添加显示得分详情的方法
    def show_score_details(self):
        """显示得分详情"""
        if hasattr(self, 'score_details'):
            details_text = "\n".join([f"{k}: {v}" for k, v in self.score_details.items()])
            QMessageBox.information(self, f"{self.package_name} 得分详情", 
                                  f"包名: {self.full_identifier}\n\n"
                                  f"总得分: {self.score}\n\n"
                                  f"得分详情:\n{details_text+"\n若含场景,不依赖扣分，每个依赖+1分"}")

    def load_analysis_tags(self):
        """加载分析标签"""
        try:
            # 从父窗口获取分析数据
            if hasattr(self, 'parent_window') and self.parent_window:
                analysis_info = self.parent_window.analysis_data.get(self.full_identifier, {})
                self.analysis_tags = analysis_info.get('tags', [])
            else:
                # 如果无法从父窗口获取，尝试直接加载文件
                analysis_file = "var_analysis_results.csv"
                if os.path.exists(analysis_file):
                    import csv
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            filename = row.get('filename', '')
                            tags_str = row.get('tags', '')
                            
                            if filename and self.full_identifier in filename:
                                # 解析tags
                                tags = [tag.strip() for tag in tags_str.split('.') if tag.strip()]
                                self.analysis_tags = tags
                                break
            
            # 构建显示文本
            if self.analysis_tags:
                # 限制显示的标签数量
                if len(self.analysis_tags) <= 3:
                    self.analysis_text = " • ".join(self.analysis_tags)
                else:
                    self.analysis_text = " • ".join(self.analysis_tags[:3]) + " • ..."
            else:
                self.analysis_text = "无分析类别"
                
        except Exception as e:
            print(f"加载分析标签失败: {e}")
            self.analysis_text = "加载失败"

    def format_creation_date(self, date_str):
            """格式化创建日期显示"""
            if not date_str or date_str.strip() == "":
                return "无日期"
            
            try:
                # 解析日期字符串，支持多种格式
                
                # 尝试解析日期
                date_formats = [
                    '%Y-%m-%d %H:%M:%S',  # 2023-07-29 22:05:58
                    '%Y/%m/%d %H:%M:%S',  # 2023/07/29 22:05:58
                    '%Y-%m-%d',           # 2023-07-29
                    '%Y/%m/%d',           # 2023/07/29
                ]
                
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(date_str.strip(), fmt)
                        # 格式化显示：只显示年月日
                        return dt.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
                
                # 如果无法解析，尝试提取日期部分
                import re
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
                if date_match:
                    return date_match.group()
                    
                return "日期格式错误"
                
            except Exception as e:
                print(f"格式化日期失败: {date_str}, 错误: {e}")
                return "日期解析失败"
    
    def format_processed_time(self, time_str):
        """格式化处理时间显示"""
        if not time_str or time_str.strip() == "":
            return "未知"
        
        try:
            # 获取父窗口的parse_processed_time方法
            if hasattr(self, 'parent_window') and self.parent_window:
                dt = self.parent_window.parse_processed_time(time_str)
            else:
                # 如果没有父窗口引用，使用自己的解析逻辑
                dt = self.parse_processed_time(time_str)
            
            if dt and dt != datetime.min:
                # 如果是今天，显示"今天 HH:MM"
                today = datetime.now().date()
                if dt.date() == today:
                    return f"今天 {dt.strftime('%H:%M')}"
                # 如果是今年，显示"MM-DD HH:MM"
                elif dt.year == today.year:
                    return dt.strftime("%m-%d %H:%M")
                # 否则显示完整日期
                else:
                    return dt.strftime("%Y-%m-%d")
        except Exception as e:
            print(f"格式化处理时间失败: {e}")
        
        # 如果解析失败，显示原始字符串（截断）
        if len(time_str) > 15:
            return time_str[:12] + "..."
        return time_str

    def parse_processed_time(self, time_str):
        """解析处理时间字符串（简化版）"""
        if not time_str or time_str.strip() == "":
            return datetime.min
        
        try:
            time_str_clean = time_str.strip()
            
            # 尝试常见的时间格式
            time_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d',
            ]
            
            for fmt in time_formats:
                try:
                    return datetime.strptime(time_str_clean, fmt)
                except ValueError:
                    continue
            
            # 尝试提取日期部分
            import re
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', time_str_clean)
            if date_match:
                return datetime.strptime(date_match.group(), '%Y-%m-%d')
                
        except Exception as e:
            print(f"解析处理时间失败: {time_str}, 错误: {e}")
        
        return datetime.min

class ImageDetailViewer(QDialog):
    """大图查看器 - 修复大小和循环切换"""
    def __init__(self, images, start_index=0, parent=None):
        super().__init__(parent)
        self.config = ConfigManager("config.json")
        self.images = images
        self.current_index = start_index
        self.scale_factor = 1.0
        self.initUI()
        self.show_image()
        
    def initUI(self):
        self.setWindowTitle('图片查看器')
        self.setGeometry(0, 0, self.config.get_window_size()[0]-200, self.config.get_window_size()[1]-200)  # 增大窗口
        
        layout = QVBoxLayout()
        
        # 控制栏
        control_layout = QHBoxLayout()
        
        self.info_label = QLabel()
        self.info_label.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(self.info_label)
        
        control_layout.addStretch()
        
        # 缩放控制
        control_layout.addWidget(QLabel("缩放:"))
        
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(30, 30)
        zoom_out_btn.clicked.connect(self.zoom_out)
        control_layout.addWidget(zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(self.zoom_label)
        
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(30, 30)
        zoom_in_btn.clicked.connect(self.zoom_in)
        control_layout.addWidget(zoom_in_btn)
        
        reset_btn = QPushButton("重置")
        reset_btn.setFixedSize(60, 30)
        reset_btn.clicked.connect(self.reset_zoom)
        control_layout.addWidget(reset_btn)
        
        layout.addLayout(control_layout)
        
        # 图片显示区域 - 设置最小尺寸
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumSize(600, 600)  # 设置最小显示区域
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(500, 500)  # 图片最小500x500
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        # 导航
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton('◀ 上一张')
        self.next_btn = QPushButton('下一张 ▶')
        self.prev_btn.clicked.connect(self.prev_image)
        self.next_btn.clicked.connect(self.next_image)
        
        nav_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel()
        self.page_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        nav_layout.addWidget(self.page_label)
        
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        
        # 快捷键提示
        hint_label = QLabel("快捷键: ← 上一张 | → 下一张 | +/- 缩放 | ESC 关闭")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(hint_label)
        
        self.setLayout(layout)
        
        # 确保对话框可以接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
    def show_image(self):
        if not self.images or self.current_index >= len(self.images):
            return
            
        image_path = self.images[self.current_index]
        
        try:
            # 加载图片并确保最小尺寸
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 获取原始尺寸
            width, height = img.size
            
            # 确保图片至少500x500
            if width < 500 or height < 500:
                # 计算缩放比例，保持宽高比
                scale = max(500 / width, 500 / height)
                width = int(width * scale)
                height = int(height * scale)
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            self.original_image = img
            self.original_size = (width, height)
            
            filename = os.path.basename(image_path)
            self.info_label.setText(f"文件: {filename} | 尺寸: {width}×{height}")
            self.page_label.setText(f"{self.current_index + 1}/{len(self.images)}")
            
            self.reset_zoom()
            
        except Exception as e:
            self.image_label.setText(f"无法加载图片: {str(e)}")
            self.image_label.setMinimumSize(500, 500)
    
    def update_display(self):
        if hasattr(self, 'original_image'):
            width = int(self.original_size[0] * self.scale_factor)
            height = int(self.original_size[1] * self.scale_factor)
            
            # 确保最小尺寸
            width = max(width, 1000)
            height = max(height, 1000)
            
            resized_img = self.original_image.resize((width, height), Image.Resampling.LANCZOS)
            
            img_byte_arr = io.BytesIO()
            resized_img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            pixmap = QPixmap()
            pixmap.loadFromData(img_byte_arr)
            
            self.image_label.setPixmap(pixmap)
            self.image_label.setFixedSize(pixmap.size())
            self.zoom_label.setText(f"{int(self.scale_factor * 100)}%")
    
    def zoom_in(self):
        self.scale_factor *= 1.2
        self.update_display()
    
    def zoom_out(self):
        self.scale_factor /= 1.2
        self.update_display()
    
    def reset_zoom(self):
        self.scale_factor = 1.0
        self.update_display()
    
    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def prev_image(self):
        """上一张图片 - 支持循环"""
        if not self.images:
            return
        
        if self.current_index > 0:
            self.current_index -= 1
        else:
            # 循环到最后一页
            self.current_index = len(self.images) - 1
        
        self.show_image()
    
    def next_image(self):
        """下一张图片 - 支持循环"""
        if not self.images:
            return
        
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
        else:
            # 循环到第一页
            self.current_index = 0
        
        self.show_image()
    
    def keyPressEvent(self, event):
        """键盘快捷键"""
        if event.key() == Qt.Key_Left:
            self.prev_image()
        elif event.key() == Qt.Key_Right:
            self.next_image()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoom_in()
        elif event.key() == Qt.Key_Minus:
            self.zoom_out()
        elif event.key() == Qt.Key_0:
            self.reset_zoom()
        elif event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            # 空格键切换下一张
            self.next_image()
        else:
            super().keyPressEvent(event)


class ImageGridViewer(QDialog):
    """小图查看器 - 支持键盘切换"""
    def __init__(self, images, image_types, title="图片查看器", parent=None):
        super().__init__(parent)
        self.config = ConfigManager("config.json")
        self.images = images
        self.image_types = image_types
        # print(image_types)
        self.thumbnail_size = 400
        self.current_category = "全部"
        self.current_selected_index = 0  # 当前选中的图片索引（在过滤后的列表中）
        self.initUI(title)
        self.load_images()
        
    def initUI(self, title):
        self.setWindowTitle(title)
        self.setGeometry(0, 0, self.config.get_window_size()[0]-100, self.config.get_window_size()[1]-100)
        
        layout = QVBoxLayout()
        
        # 控制栏
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部", "场景", "衣服", "头发", "外观", "姿势", "纹理", "插件", "其他"])
        self.category_combo.currentTextChanged.connect(self.change_category)
        control_layout.addWidget(self.category_combo)
        
        control_layout.addWidget(QLabel("大小:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(100, 1300)
        self.size_slider.setValue(self.thumbnail_size)
        self.size_slider.valueChanged.connect(self.change_thumbnail_size)
        self.size_slider.setFixedWidth(150)
        control_layout.addWidget(self.size_slider)
        
        self.count_label = QLabel("共 0 张图片")
        self.count_label.setStyleSheet("font-weight: bold; color: #0078d7;")
        control_layout.addWidget(self.count_label)
        
        # 当前位置显示
        self.position_label = QLabel("位置: 0")
        self.position_label.setStyleSheet("color: #666;")
        control_layout.addWidget(self.position_label)
        
        layout.addLayout(control_layout)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.container_widget = QWidget()
        self.grid_layout = QGridLayout(self.container_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        self.scroll_area.setWidget(self.container_widget)
        layout.addWidget(self.scroll_area)
        
        # 提示
        hint_label = QLabel("提示: 点击图片查看大图，←/→切换选中图片，Enter查看大图，ESC关闭")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #888; font-size: 12px; padding: 5px;")
        layout.addWidget(hint_label)
        
        self.setLayout(layout)
        
        # 设置焦点策略以接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        self.current_selected_widget = None
        
    def load_images(self):
        # 清空现有内容
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取过滤后的图片索引
        self.filtered_indices = self.filter_images_by_category()
        
        if not self.filtered_indices:
            self.count_label.setText("共 0 张图片")
            self.position_label.setText("位置: 0")
            return
        
        # 确保当前选中索引在有效范围内
        self.current_selected_index = min(self.current_selected_index, len(self.filtered_indices) - 1)
        
        # 计算列数
        # columns = max(4, self.width() // (self.thumbnail_size + 40))
        columns = 6

        # 添加缩略图
        for idx, img_index in enumerate(self.filtered_indices):
            if img_index >= len(self.images):
                continue
                
            row = idx // columns
            col = idx % columns
            
            img_path = self.images[img_index]
            filename = os.path.basename(img_path)
            file_type = self.image_types[img_index] if img_index < len(self.image_types) else "未知"
            
            thumbnail = self.create_thumbnail(img_path, filename, file_type, idx)
            thumbnail.mousePressEvent = lambda e, idx=idx: self.select_and_show_detail(idx)
            
            # 如果是当前选中的，设置高亮样式
            if idx == self.current_selected_index:
                thumbnail.setStyleSheet("""
                    QWidget {
                        border: 3px solid #0078d7;
                        border-radius: 8px;
                        background: #f0f8ff;
                    }
                """)
                self.current_selected_widget = thumbnail
            else:
                thumbnail.setStyleSheet("""
                    QWidget {
                        border: 1px solid #e0e0e0;
                        border-radius: 8px;
                        background: white;
                    }
                    QWidget:hover {
                        border: 2px solid #0078d7;
                    }
                """)
            
            self.grid_layout.addWidget(thumbnail, row, col)
        
        self.count_label.setText(f"共 {len(self.filtered_indices)} 张图片")
        self.position_label.setText(f"位置: {self.current_selected_index + 1}/{len(self.filtered_indices)}")
        
        # 滚动到选中位置
        self.scroll_to_selected()
    
    def scroll_to_selected(self):
        """滚动到当前选中的图片"""
        if self.current_selected_widget:
            # 计算选中项的位置
            pos = self.current_selected_widget.pos()
            self.scroll_area.ensureVisible(pos.x(), pos.y())
    
    def filter_images_by_category(self):
        filtered_indices = []
        
        category_map = {
            'subscene': ['subscene'],
            'clothing_preset':['衣服预设'],
            'skin': ['皮肤预设'],
            "场景": ["scene"],
            "衣服": ["clothing", "clothes"],
            "头发": ["hair"],
            "姿势": ["pose"],
            "外观预设": ["appearance", "skin"],
            "纹理": ["texture", "tex"],
            "插件": ["plugin", "script"],
            'assets':['资产']
        }

        for i, img_path in enumerate(self.images):
            if self.current_category == "全部":
                filtered_indices.append(i)
            else:
                if self.current_category in category_map:
                    keywords = category_map[self.current_category]
                    img_lower = img_path.lower()
                    if any(keyword in img_lower for keyword in keywords):
                        filtered_indices.append(i)
                elif self.current_category == "其他":
                    all_keywords = []
                    for keywords in category_map.values():
                        all_keywords.extend(keywords)
                    
                    img_lower = img_path.lower()
                    if not any(keyword in img_lower for keyword in all_keywords):
                        filtered_indices.append(i)
        
        return filtered_indices
    
    def create_thumbnail(self, image_path, filename, file_type, index):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 图片
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setFixedSize(self.thumbnail_size - 20, self.thumbnail_size - 60)
        
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.thumbnail((self.thumbnail_size - 30, self.thumbnail_size - 70), Image.Resampling.LANCZOS)
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                pixmap = QPixmap()
                pixmap.loadFromData(img_byte_arr)
                
                if not pixmap.isNull():
                    image_label.setPixmap(pixmap)
                else:
                    image_label.setText("图")
                    image_label.setStyleSheet("background: #f0f0f0;")
            except:
                image_label.setText("加载失败")
                image_label.setStyleSheet("background: #fff0f0;")
        else:
            image_label.setText("无图")
            image_label.setStyleSheet("background: #f0f0f0;")
        
        layout.addWidget(image_label)
        
        # 信息
        name_label = QLabel(filename[:20] + ("..." if len(filename) > 20 else ""))
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        type_label = QLabel(f"类型: {file_type}")
        type_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(type_label)
        
        return widget
    
    def change_category(self, category):
        self.current_category = category
        self.current_selected_index = 0  # 重置选中位置
        self.load_images()
    
    def change_thumbnail_size(self, size):
        self.thumbnail_size = size
        self.load_images()
    
    def select_and_show_detail(self, index):
        """选择并显示大图"""
        self.current_selected_index = index
        self.show_detail_image(index)
    
    def show_detail_image(self, filtered_index):
        """显示大图"""
        if filtered_index >= len(self.filtered_indices):
            return
        
        # 获取原始图片索引
        original_index = self.filtered_indices[filtered_index]
        
        # 获取过滤后的图片列表
        filtered_images = [self.images[i] for i in self.filtered_indices]
        
        # 在过滤后的列表中查找当前位置
        current_in_filtered = filtered_index
        
        viewer = ImageDetailViewer(filtered_images, current_in_filtered, self)
        viewer.exec_()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.load_images()
    
    def keyPressEvent(self, event):
        """键盘快捷键"""
        if not self.filtered_indices:
            return
            
        if event.key() == Qt.Key_Left:
            # 向左移动选中位置（支持循环）
            if self.current_selected_index > 0:
                self.current_selected_index -= 1
            else:
                self.current_selected_index = len(self.filtered_indices) - 1
            self.load_images()
            
        elif event.key() == Qt.Key_Right:
            # 向右移动选中位置（支持循环）
            if self.current_selected_index < len(self.filtered_indices) - 1:
                self.current_selected_index += 1
            else:
                self.current_selected_index = 0
            self.load_images()
            
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 回车键查看大图
            self.show_detail_image(self.current_selected_index)
            
        elif event.key() == Qt.Key_Escape:
            self.close()
            
        elif event.key() == Qt.Key_Home:
            # Home键跳到第一张
            self.current_selected_index = 0
            self.load_images()
            
        elif event.key() == Qt.Key_End:
            # End键跳到最后一张
            self.current_selected_index = len(self.filtered_indices) - 1
            self.load_images()
            
        else:
            super().keyPressEvent(event)


"""透明悬停小图查看器 - 完全修复版"""
class HoverImageViewer(QWidget):
    """透明悬停图片查看器 - 使用QWidget而不是QDialog"""
    viewer_closed = pyqtSignal()  # 新增：查看器关闭信号
    
    def __init__(self, images, image_types, parent=None):
        super().__init__(parent)
        self.config = ConfigManager("config.json")
        self.images = images
        self.image_types = image_types
        
        # 关键设置：使用无边框窗口，但不设置透明属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        
        # 关键：不设置WA_TranslucentBackground，而是设置半透明样式
        self.setWindowOpacity(0.99)  # 设置窗口透明度
        
        # 设置窗口为全屏
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        
        # 设置背景颜色为半透明白色
        self.setStyleSheet("background-color: rgba(255, 255, 255, 220);")  # 220/255透明度
        
        # 创建滚动区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setGeometry(self.rect())  # 充满整个窗口
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建容器widget
        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        
        self.scroll_area.setWidget(self.container)
        
        # 加载图片
        self.load_images()
        
        # 确保窗口显示
        self.show()
        
        # 打印调试信息
        print(f"HoverImageViewer: 显示 {len(self.images)} 张图片")
        print(f"窗口尺寸: {self.size()}")
        print(f"滚动区域尺寸: {self.scroll_area.size()}")

    def load_images(self):
        """加载图片到网格布局"""
        if not self.images:
            print("警告: 没有图片可显示")
            return
        
        print(f"开始加载 {len(self.images)} 张图片...")
        
        # 根据图片数量动态调整列数
        window_width = self.config.get_window_size()[0]
        window_height = self.config.get_window_size()[1]
        image_size = self.config.get_current_HoverImageViewer_size()

        image_count = len(self.images)
        # 动态计算列数，确保图片铺满窗口宽度
        max_columns = max(1, window_width // image_size)
        # 设置列数，但不能超过图片总数
        columns = min(max_columns, image_count)
        
        for idx in range(image_count):
            row = idx // columns
            col = idx % columns
            
            img_path = self.images[idx]
            
            # 创建图片标签
            label = QLabel()
            label.setFixedSize(image_size, image_size)  # 使用更小的尺寸
            
            if os.path.exists(img_path):
                try:
                    pixmap = QPixmap(img_path)
                    if not pixmap.isNull():
                        # 缩放到合适大小
                        scaled = pixmap.scaled(image_size, image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        label.setPixmap(scaled)
                        label.setAlignment(Qt.AlignCenter)
                        # print(f"已加载: {os.path.basename(img_path)}")
                    else:
                        label.setText("图片无效")
                except Exception as e:
                    print(f"加载失败 {img_path}: {e}")
                    label.setText("加载失败")
            else:
                label.setText("图片不存在")
            
            self.grid_layout.addWidget(label, row, col)
        
        print("图片加载完成")
    
    def wheelEvent(self, event):
        """鼠标滚轮事件"""
        # 直接处理滚轮事件
        v_scroll_bar = self.scroll_area.verticalScrollBar()
        delta = event.angleDelta().y()
        scroll_speed = 2
        
        if delta > 0:
            v_scroll_bar.setValue(v_scroll_bar.value()*scroll_speed)
        else:
            v_scroll_bar.setValue(v_scroll_bar.value()*scroll_speed)
        
        event.accept()
    
    def mousePressEvent(self, event):
        """鼠标点击关闭窗口"""
        print("HoverImageViewer: 鼠标点击，关闭窗口")
        self.close_viewer()
    
    def close_viewer(self):
        """关闭查看器并发送信号"""
        print("HoverImageViewer: 关闭查看器")
        self.viewer_closed.emit()  # 发送关闭信号
        self.close()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        print("HoverImageViewer: 关闭事件")
        super().closeEvent(event)
    
    def paintEvent(self, event):
        """绘制事件，确保背景正确绘制"""
        super().paintEvent(event)
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        self.scroll_area.setGeometry(self.rect())
        super().resizeEvent(event)

# MultiTagFilterDialog 和 VARManager 类保持不变，但需要小调整
class MultiTagFilterDialog(QDialog):
    """标签筛选对话框"""
    def __init__(self, all_tags, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.selected_tags = set()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("多标签筛选")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.tag_layout = QGridLayout(scroll_widget)
        
        self.tag_checkboxes = []
        sorted_tags = sorted(self.all_tags)
        for i, tag in enumerate(sorted_tags):
            checkbox = QCheckBox(tag)
            self.tag_checkboxes.append(checkbox)
            self.tag_layout.addWidget(checkbox, i // 3, i % 3)
        
        scroll_widget.setLayout(self.tag_layout)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("全选")
        clear_all_btn = QPushButton("清空")
        apply_btn = QPushButton("应用")
        cancel_btn = QPushButton("取消")
        
        select_all_btn.clicked.connect(self.select_all)
        clear_all_btn.clicked.connect(self.clear_all)
        apply_btn.clicked.connect(self.apply_filter)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(clear_all_btn)
        button_layout.addStretch()
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def select_all(self):
        for checkbox in self.tag_checkboxes:
            checkbox.setChecked(True)
    
    def clear_all(self):
        for checkbox in self.tag_checkboxes:
            checkbox.setChecked(False)
    
    def apply_filter(self):
        self.selected_tags.clear()
        for checkbox in self.tag_checkboxes:
            if checkbox.isChecked():
                self.selected_tags.add(checkbox.text())
        self.accept()


# TagAdderDialog 类（已修正）- 单包添加
class TagAdderDialog(QDialog):
    """标签添加对话框 - 支持分组显示"""
    def __init__(self, var_package_name, csv_file="var_packages.csv", tag_file_path="tags.txt", 
                 full_identifier=None, batch_mode=False, selected_count=0, parent=None):
        super().__init__(parent)
        self.config = ConfigManager("config.json")
        self.var_package_name = var_package_name
        self.full_identifier = full_identifier
        self.csv_file = csv_file
        self.tag_file_path = tag_file_path
        self.batch_mode = batch_mode
        self.selected_count = selected_count
        self.existing_tags = []
        self.user_selected_tags = set()
        self.current_package_tags = set()
        
        # 新增：分组相关属性
        self.tag_groups = {}  # 分组 -> 标签列表
        self.expanded_groups = set()  # 展开的分组
        self.group_widgets = {}  # 分组名称 -> 分组控件
        
        self.initUI()
        self.load_existing_tags()
        self.expand_all_groups()
        
    def initUI(self):
        self.setWindowTitle("添加/编辑标签 - 分组显示")
        self.setGeometry(0, 0, self.config.get_window_size()[0]-10, self.config.get_window_size()[1]-100)
        
        layout = QVBoxLayout()
        
        # 标题
        """初始化UI"""
        operation_text = "添加/编辑" if not self.batch_mode else "批量添加"
        
        if self.batch_mode:
            title_text = f"为 {self.selected_count} 个选中的包{operation_text}标签"
        elif self.full_identifier:
            title_text = f"为 {self.full_identifier} {operation_text}标签："
        else:
            title_text = f"为 {self.var_package_name} {operation_text}标签："
        
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            margin-bottom: 10px; 
            color: #0078d7;
            padding: 5px;
            background: #f0f8ff;
            border-radius: 5px;
            border: 1px solid #b3d9ff;
        """)
        layout.addWidget(self.title_label)
        
        # 当前包已有标签显示
        self.current_tags_label = QLabel("当前标签: 加载中...")
        self.current_tags_label.setStyleSheet("""
            font-size: XXXXX; 
            color: #666; 
            margin-bottom: 10px; 
            background: #f8f9fa; 
            padding: 5px; 
            border-radius: 3px;
        """.replace("XXXXX",self.config.get_font_size()))
        layout.addWidget(self.current_tags_label)
        
        # 搜索和分组控制
        control_layout = QHBoxLayout()
        
        # 搜索框
        control_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索标签...")
        self.search_input.textChanged.connect(self.filter_tags)
        self.search_input.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        control_layout.addWidget(self.search_input)
        
        # 分组显示控制按钮
        self.expand_all_btn = QPushButton("展开所有分组")
        self.expand_all_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        self.collapse_all_btn = QPushButton("折叠所有分组")
        self.collapse_all_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))

        self.expand_all_btn.clicked.connect(self.expand_all_groups)
        self.collapse_all_btn.clicked.connect(self.collapse_all_groups)
        
        control_layout.addStretch()
        control_layout.addWidget(self.expand_all_btn)
        control_layout.addWidget(self.collapse_all_btn)
        
        layout.addLayout(control_layout)
        
        # 标签显示区域（分组显示）
        self.tags_scroll = QScrollArea()
        self.tags_scroll.setWidgetResizable(True)
        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setSpacing(1)
        self.tags_layout.setContentsMargins(5, 5, 5, 5)
        self.tags_scroll.setWidget(self.tags_container)
        layout.addWidget(self.tags_scroll)
        
        # 自定义标签输入
        custom_layout = QHBoxLayout()
        custom_label = QLabel("自定义标签:")
        custom_label.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("输入新标签，格式: 分组_标签名")
        add_custom_btn = QPushButton("添加")
        self.custom_input.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        add_custom_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))

        add_custom_btn.clicked.connect(self.add_custom_tags)
        
        custom_layout.addWidget(custom_label)
        custom_layout.addWidget(self.custom_input)
        custom_layout.addWidget(add_custom_btn)
        layout.addLayout(custom_layout)
        
        # 统计信息
        self.stats_label = QLabel("已选择 0 个标签")
        self.stats_label.setStyleSheet("""
            color: #0078d7; 
            font-weight: bold;
            background: #e8f4ff;
            padding: 5px;
            border-radius: 3px;
            border: 1px solid #b3d9ff;
        """)
        self.stats_label.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        layout.addWidget(self.stats_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 左侧操作按钮
        left_buttons = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        clear_all_btn = QPushButton("清空")
        select_existing_btn = QPushButton("仅选择已有标签")
        select_all_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        clear_all_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        select_existing_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))

        select_all_btn.clicked.connect(self.select_all_tags)
        clear_all_btn.clicked.connect(self.clear_all_tags)
        select_existing_btn.clicked.connect(self.select_existing_tags)
        
        left_buttons.addWidget(select_all_btn)
        left_buttons.addWidget(clear_all_btn)
        left_buttons.addWidget(select_existing_btn)
        left_buttons.addStretch()
        
        button_layout.addLayout(left_buttons)
        
        # 右侧操作按钮
        right_buttons = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        confirm_btn = QPushButton("确定保存")
        cancel_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        confirm_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))

        
        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept)
        
        right_buttons.addWidget(cancel_btn)
        right_buttons.addWidget(confirm_btn)
        
        button_layout.addLayout(right_buttons)
        
        layout.addLayout(button_layout)
        
        # 添加状态显示标签（替代statusBar）
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                background: #f8f9fa;
                padding: 3px 8px;
                border-radius: 3px;
                border-top: 1px solid #dee2e6;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)
    
    def show_status_message(self, message, timeout=3000):
        """显示状态消息"""
        self.status_label.setText(message)
        
        # 如果有超时设置，使用定时器清除消息
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.status_label.setText(""))
    
    def load_existing_tags(self):
        """加载已有标签并解析分组"""
        try:
            # 读取标签文件
            tag_file_tags = []
            if os.path.exists(self.tag_file_path):
                with open(self.tag_file_path, 'r', encoding='utf-8') as f:
                    tag_file_tags = [line.strip() for line in f.readlines() 
                                    if line.strip() and not line.strip().startswith('#')]
            
            # 解析分组
            self.parse_tag_groups(tag_file_tags)
            
            # 从CSV加载所有标签（用于补全）
            all_tags_from_csv = set()
            if os.path.exists(self.csv_file):
                with open(self.csv_file, 'r', encoding='gb18030') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        tags_str = row.get('tags', '')
                        if tags_str and tags_str != "无":
                            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                            all_tags_from_csv.update(tags)
                        
                        # 获取当前包已有标签
                        if self.full_identifier:
                            author = row.get('author', '')
                            package_name = row.get('package_name', '')
                            version = row.get('version', '')
                            current_full_id = f"{author}.{package_name}.{version}"
                            
                            if current_full_id == self.full_identifier:
                                current_tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                                self.current_package_tags = set(current_tags)
            
            # 合并标签到分组
            self.merge_csv_tags_into_groups(all_tags_from_csv)
            
            # 设置当前包已有标签
            if self.current_package_tags:
                tags_text = ",".join(sorted(self.current_package_tags))
                self.current_tags_label.setText(f"当前已有标签: {tags_text}")
                self.user_selected_tags = set(self.current_package_tags)
            else:
                self.current_tags_label.setText("当前标签: 无")
            
            # 显示分组标签
            self.display_tag_groups()
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载标签失败: {str(e)}")
            self.tag_groups = {}
            self.current_tags_label.setText("当前标签: 加载失败")
    
    def parse_tag_groups(self, tag_lines):
        """解析标签分组"""
        self.tag_groups = {}
        current_group = "未分组"
        self.tag_groups[current_group] = []
        
        for line in tag_lines:
            # 检查是否为分组标题
            if line.startswith('[') and line.endswith(']'):
                current_group = line[1:-1].strip()
                if current_group not in self.tag_groups:
                    self.tag_groups[current_group] = []
            else:
                # 检查是否有下划线分隔
                if '_' in line:
                    parts = line.split('_', 1)
                    group_name = parts[0].strip()
                    tag_name = parts[1].strip()
                    
                    if group_name not in self.tag_groups:
                        self.tag_groups[group_name] = []
                    
                    # 保存完整标签名（带分组前缀）
                    full_tag_name = f"{group_name}_{tag_name}"
                    self.tag_groups[group_name].append({
                        'display': tag_name,
                        'full': full_tag_name,
                        'group': group_name
                    })
                else:
                    # 无分组的标签
                    self.tag_groups[current_group].append({
                        'display': line,
                        'full': line,
                        'group': current_group
                    })
        
        # 清理空分组
        empty_groups = [group for group, tags in self.tag_groups.items() if not tags]
        for group in empty_groups:
            del self.tag_groups[group]
    
    def merge_csv_tags_into_groups(self, csv_tags):
        """将CSV中的标签合并到分组中"""
        for tag in csv_tags:
            found = False
            # 检查标签是否已在分组中
            for group_name, tags in self.tag_groups.items():
                for tag_info in tags:
                    if tag_info['full'] == tag:
                        found = True
                        break
                if found:
                    break
            
            # 如果不在任何分组中，尝试解析或放入未分组
            if not found:
                if '_' in tag:
                    parts = tag.split('_', 1)
                    group_name = parts[0]
                    tag_name = parts[1]
                    
                    if group_name not in self.tag_groups:
                        self.tag_groups[group_name] = []
                    
                    self.tag_groups[group_name].append({
                        'display': tag_name,
                        'full': tag,
                        'group': group_name
                    })
                else:
                    if "未分组" not in self.tag_groups:
                        self.tag_groups["未分组"] = []
                    
                    self.tag_groups["未分组"].append({
                        'display': tag,
                        'full': tag,
                        'group': "未分组"
                    })
    
    def display_tag_groups(self, filter_text=""):
        """显示分组标签"""
        # 清空现有内容
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.group_widgets.clear()
        
        if not self.tag_groups:
            no_tags_label = QLabel("没有可用的标签")
            no_tags_label.setAlignment(Qt.AlignCenter)
            self.tags_layout.addWidget(no_tags_label)
            return
        
        # 是否应用过滤
        apply_filter = bool(filter_text.strip())
        filter_lower = filter_text.lower()
        
        # 按分组显示
        for group_name in sorted(self.tag_groups.keys()):
            tags = self.tag_groups[group_name]
            
            # 过滤标签
            if apply_filter:
                filtered_tags = [
                    tag_info for tag_info in tags 
                    if filter_lower in tag_info['full'].lower() or 
                       filter_lower in tag_info['display'].lower()
                ]
            else:
                filtered_tags = tags
            
            if not filtered_tags:
                continue  # 跳过空分组
            
            # 创建分组折叠控件
            group_box = self.create_group_box(group_name, filtered_tags, len(tags))
            self.tags_layout.addWidget(group_box)
            self.group_widgets[group_name] = group_box
            
            # 默认展开前3个分组
            if group_name in list(sorted(self.tag_groups.keys()))[:3]:
                self.expand_group(group_name)
        
        # 添加弹性空间
        self.tags_layout.addStretch()
        
        # 更新统计信息
        self.update_stats()
    
    def create_group_box(self, group_name, tags, total_count):
        """创建分组折叠框"""
        group_box = QGroupBox()
        group_box.setObjectName(f"group_{group_name}")
        
        # 分组标题（带折叠按钮和选择按钮）
        header_layout = QHBoxLayout()
        
        # 折叠/展开按钮
        is_expanded = group_name in self.expanded_groups
        toggle_btn = QPushButton("▼" if is_expanded else "▶")
        toggle_btn.setFixedSize(20, 20)
        toggle_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-weight: bold;
                color: #0078d7;
            }
        """)
        toggle_btn.clicked.connect(lambda: self.toggle_group(group_name))
        
        # 分组标题
        title_label = QLabel(f"{group_name} ({len(tags)}/{total_count})")
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: XXXXX;
                color: #495057;
            }
        """.replace("XXXXX",self.config.get_font_size()))
        
        # 分组全选按钮
        select_group_btn = QPushButton("全选")
        select_group_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                background: white;
                font-size: XXXXX;
                padding: 1px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: #0078d7;
                color: white;
                border-color: #0056b3;
            }
        """.replace("XXXXX",self.config.get_font_size()))
        select_group_btn.clicked.connect(lambda: self.select_group_tags(group_name))
        
        header_layout.addWidget(toggle_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(select_group_btn)

        # 分组内的标签网格
        tags_container = QWidget()
        tags_container.setObjectName(f"tags_container_{group_name}")
        tags_grid = QGridLayout(tags_container)
        
        tags_grid.setSpacing(8)
        tags_grid.setContentsMargins(15, 5, 5, 5)
        
        # 添加标签复选框
        for i, tag_info in enumerate(tags):
            row = i // self.config.get_columns1()
            col = i % self.config.get_columns1()
            
            checkbox = self.create_tag_checkbox(tag_info)
            tags_grid.addWidget(checkbox, row, col)
        
        # 主布局
        main_layout = QVBoxLayout(group_box)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(tags_container)
        
        # 初始状态
        tags_container.setVisible(is_expanded)
        
        return group_box
    
    # 创建复选框，关键代码，颜色没必要改
    def create_tag_checkbox(self, tag_info):
        """创建标签复选框"""
        checkbox = QCheckBox(tag_info['display'])
        checkbox.setProperty('full_tag', tag_info['full'])
        checkbox.setProperty('group', tag_info['group'])

        checkbox.setStyleSheet("""
            QCheckBox {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 3px;
                background: white; 
                font-size: XXXXX;
            }
            QCheckBox:hover {
                border: 1px solid #0078d7;
                background: #f0f8ff;
            }
            QCheckBox::indicator {
                width: XXXXX;
                height: XXXXX;
            }
        """.replace("XXXXX",self.config.get_font_size()))
        
        # 如果标签已选中，设置状态
        if tag_info['full'] in self.user_selected_tags:
            checkbox.setChecked(True)
        
        # 连接信号
        checkbox.stateChanged.connect(
            lambda state, t=tag_info['full']: self.on_tag_toggled(state, t)
        )
        
        return checkbox
    
    def toggle_group(self, group_name):
        """切换分组展开/折叠状态"""
        if group_name in self.expanded_groups:
            self.collapse_group(group_name)
        else:
            self.expand_group(group_name)
    
    def expand_group(self, group_name):
        """展开分组"""
        if group_name in self.group_widgets:
            group_box = self.group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"tags_container_{group_name}")
            if tags_container:
                tags_container.setVisible(True)
            
            # 更新按钮文字
            toggle_btn = None
            for child in group_box.findChildren(QPushButton):
                if child.text() in ["▶", "▼"]:
                    toggle_btn = child
                    break
            if toggle_btn:
                toggle_btn.setText("▼")
            
            self.expanded_groups.add(group_name)
    
    def collapse_group(self, group_name):
        """折叠分组"""
        if group_name in self.group_widgets:
            group_box = self.group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"tags_container_{group_name}")
            if tags_container:
                tags_container.setVisible(False)
            
            # 更新按钮文字
            toggle_btn = None
            for child in group_box.findChildren(QPushButton):
                if child.text() in ["▶", "▼"]:
                    toggle_btn = child
                    break
            if toggle_btn:
                toggle_btn.setText("▶")
            
            self.expanded_groups.discard(group_name)
    
    def expand_all_groups(self):
        """展开所有分组"""
        for group_name in self.group_widgets.keys():
            self.expand_group(group_name)
    
    def collapse_all_groups(self):
        """折叠所有分组"""
        for group_name in self.group_widgets.keys():
            self.collapse_group(group_name)
    
    def filter_tags(self):
        """过滤标签"""
        filter_text = self.search_input.text().strip()
        self.display_tag_groups(filter_text)
        
        # 如果有过滤文本，自动展开所有分组
        if filter_text:
            self.expand_all_groups()
    
    def select_all_tags(self):
        """选择所有可见标签"""
        # 获取当前所有可见的复选框
        visible_checkboxes = []
        
        # 遍历所有分组控件
        for group_name, group_box in self.group_widgets.items():
            # 获取分组内的标签容器
            tags_container = group_box.findChild(QWidget, f"tags_container_{group_name}")
            if tags_container and tags_container.isVisible():
                # 查找容器内的所有复选框
                checkboxes = tags_container.findChildren(QCheckBox)
                visible_checkboxes.extend(checkboxes)
        
        # 选中所有可见的复选框
        for checkbox in visible_checkboxes:
            full_tag = checkbox.property('full_tag')
            if full_tag:
                checkbox.setChecked(True)
                self.user_selected_tags.add(full_tag)
        
        # 更新统计信息
        self.update_stats()
        
        # 显示提示
        selected_count = len(visible_checkboxes)
        self.show_status_message(f"已选择 {selected_count} 个标签")
    
    def select_existing_tags(self):
        """仅选择当前包已有的标签"""
        # 先清空当前选择
        self.clear_all_tags()
        
        # 选中当前包已有的标签
        for tag in self.current_package_tags:
            # 在界面中找到对应的复选框并选中
            for group_name, group_box in self.group_widgets.items():
                # 获取分组内的标签容器
                tags_container = group_box.findChild(QWidget, f"tags_container_{group_name}")
                if tags_container:
                    # 查找容器内的所有复选框
                    checkboxes = tags_container.findChildren(QCheckBox)
                    for checkbox in checkboxes:
                        full_tag = checkbox.property('full_tag')
                        if full_tag == tag:
                            checkbox.setChecked(True)
                            self.user_selected_tags.add(tag)
                            break
        
        # 更新统计信息
        self.update_stats()
        
        # 显示提示
        selected_count = len(self.current_package_tags)
        self.show_status_message(f"已选择 {selected_count} 个已有标签")
    
    def clear_all_tags(self):
        """清除所有选择"""
        # 遍历所有复选框
        for group_name, group_box in self.group_widgets.items():
            # 获取分组内的标签容器
            tags_container = group_box.findChild(QWidget, f"tags_container_{group_name}")
            if tags_container:
                # 查找容器内的所有复选框
                checkboxes = tags_container.findChildren(QCheckBox)
                for checkbox in checkboxes:
                    checkbox.setChecked(False)
        
        # 清空选择集合
        self.user_selected_tags.clear()
        
        # 更新统计信息
        self.update_stats()
        
        # 显示提示
        self.show_status_message("已清除所有选择")
    
    def on_tag_toggled(self, state, full_tag):
        """标签选择状态改变"""
        if state == Qt.Checked:
            self.user_selected_tags.add(full_tag)
        elif full_tag in self.user_selected_tags:
            self.user_selected_tags.remove(full_tag)
        
        self.update_stats()
    
    def update_stats(self):
        """更新统计信息"""
        count = len(self.user_selected_tags)
        self.stats_label.setText(f"已选择 {count} 个标签")
        
        # 显示选中的标签
        if count > 0:
            # 按分组组织选中的标签
            grouped_tags = {}
            for full_tag in sorted(self.user_selected_tags):
                # 解析分组
                if '_' in full_tag:
                    group = full_tag.split('_')[0]
                    tag_name = full_tag.split('_')[1]
                else:
                    group = "未分组"
                    tag_name = full_tag
                
                if group not in grouped_tags:
                    grouped_tags[group] = []
                grouped_tags[group].append(tag_name)
            
            # 构建工具提示文本
            tooltip_parts = []
            for group in sorted(grouped_tags.keys()):
                tags_text = "，".join(grouped_tags[group])
                tooltip_parts.append(f"{group}: {tags_text}")
            
            tooltip_text = "\n".join(tooltip_parts)
            if len(tooltip_text) > 150:
                tooltip_text = tooltip_text[:147] + "..."
            
            self.stats_label.setToolTip(f"选中的标签:\n{tooltip_text}")
        else:
            self.stats_label.setToolTip("")
    
    def add_custom_tags(self):
        """添加自定义标签"""
        custom_tags_text = self.custom_input.text().strip()
        if not custom_tags_text:
            return
        
        # 解析标签
        new_tags = []
        for tag in custom_tags_text.replace(',', ' ').split():
            tag_clean = tag.strip()
            if tag_clean:
                new_tags.append(tag_clean)
        
        if not new_tags:
            QMessageBox.information(self, "提示", "请输入有效的标签")
            return
        
        # 添加到标签文件
        try:
            # 添加新标签到文件
            with open(self.tag_file_path, 'a', encoding='utf-8') as f:
                for tag in new_tags:
                    f.write(tag + '\n')
            
            # 重新加载标签
            self.load_existing_tags()
            
            # 清除输入框
            self.custom_input.clear()
            
            # 自动选中新添加的标签
            for tag in new_tags:
                self.user_selected_tags.add(tag)
            
            # 重新显示并展开所有分组（方便查看新标签）
            self.expand_all_groups()
            
            # 显示成功消息
            self.show_status_message(f"已添加 {len(new_tags)} 个新标签")
            
            QMessageBox.information(self, "成功", 
                f"已添加 {len(new_tags)} 个新标签")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加标签失败: {str(e)}")
    
    def select_group_tags(self, group_name):
        """选择指定分组的所有标签"""
        if group_name in self.group_widgets:
            group_box = self.group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"tags_container_{group_name}")
            
            if tags_container and tags_container.isVisible():
                # 获取分组内的所有复选框
                checkboxes = tags_container.findChildren(QCheckBox)
                
                for checkbox in checkboxes:
                    full_tag = checkbox.property('full_tag')
                    if full_tag:
                        checkbox.setChecked(True)
                        self.user_selected_tags.add(full_tag)
                
                # 更新统计信息
                self.update_stats()
                
                # 显示提示
                selected_count = len(checkboxes)
                self.show_status_message(f"已选择 {group_name} 分组的 {selected_count} 个标签")
    
    def accept(self):
        """对话框接受"""
        # 确保有选中的标签
        if not self.user_selected_tags:
            reply = QMessageBox.question(
                self, 
                "确认",
                "没有选择任何标签，这将清空原有标签。是否继续？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 调用父类的 accept 方法
        super().accept()
    
    def get_selected_tags(self):
        """获取用户选择的标签"""
        return sorted(self.user_selected_tags)


# TagFilterDialog 类（修正版 - 两个区域都显示所有标签） 筛选器
class TagFilterDialog(QDialog):
    """标签筛选对话框 - 支持包含和排除标签，带分组显示"""
    def __init__(self, all_tags, include_tags, exclude_tags, csv_file="var_packages.csv", parent=None):
        super().__init__(parent)
        self.config = ConfigManager("config.json")
        self.all_tags = sorted(all_tags)
        self.include_tags = set(include_tags)
        self.exclude_tags = set(exclude_tags)
        self.csv_file = csv_file  # 新增：CSV文件路径
        
        # 新增：作者统计相关属性
        self.author_tags = []  # 存储自动生成的作者标签
        self.author_group_name = "自动临时筛选_-author"  # 作者分组的名称前缀
        
        # 新增：分组相关属性
        self.tag_groups = {}  # 分组 -> 标签列表
        self.include_expanded_groups = set()  # 包含标签展开的分组
        self.exclude_expanded_groups = set()  # 排除标签展开的分组
        self.include_group_widgets = {}  # 包含标签分组名称 -> 分组控件
        self.exclude_group_widgets = {}  # 排除标签分组名称 -> 分组控件

        # 新增：作者分类相关属性
        self.author_categories = {}  # 存储作者分类信息
        self.load_author_categories()  # 新增：加载作者分类
        self.load_author_statistics()  # 新增：加载作者统计
        self.parse_tags_into_groups()
        self.initUI()
        
        
    def initUI(self):
        self.setWindowTitle("标签筛选 - 包含/排除")
        self.setGeometry(0, 0, self.config.get_window_size()[0]-10, self.config.get_window_size()[1]-100)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("选择要包含和排除的标签")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #0078d7;")
        layout.addWidget(title_label)
        
        # 标签区域（分两栏：包含标签和排除标签）
        tags_widget = QWidget()
        tags_layout = QHBoxLayout(tags_widget)
        
        # 左侧：包含标签
        include_group = QGroupBox("包含标签（必须包含以下所有标签）")
        include_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #28a745;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #28a745;
            }
        """)
        
        self.include_layout = QVBoxLayout()
        
        # 包含标签搜索和分组控制
        include_control_layout = QHBoxLayout()
        include_control_layout.addWidget(QLabel("搜索:"))
        self.include_search_input = QLineEdit()
        self.include_search_input.setPlaceholderText("搜索包含标签...")
        self.include_search_input.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        self.include_search_input.textChanged.connect(self.filter_include_tags)
        include_control_layout.addWidget(self.include_search_input)
        
        # 包含标签的分组控制按钮
        self.include_expand_all_btn = QPushButton("展开所有分组")
        self.include_collapse_all_btn = QPushButton("折叠所有分组")
        self.include_expand_all_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        self.include_collapse_all_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        self.include_expand_all_btn.clicked.connect(self.expand_all_include_groups)
        self.include_collapse_all_btn.clicked.connect(self.collapse_all_include_groups)
        
        include_control_layout.addStretch()
        include_control_layout.addWidget(self.include_expand_all_btn)
        include_control_layout.addWidget(self.include_collapse_all_btn)
        
        self.include_layout.addLayout(include_control_layout)
        
        # 包含标签显示区域
        self.include_scroll = QScrollArea()
        self.include_scroll.setWidgetResizable(True)
        self.include_widget = QWidget()
        self.include_tags_layout = QVBoxLayout(self.include_widget)
        self.include_tags_layout.setSpacing(5)
        self.include_tags_layout.setContentsMargins(5, 5, 5, 5)
        self.include_scroll.setWidget(self.include_widget)
        self.include_layout.addWidget(self.include_scroll)
        
        # 包含标签操作按钮
        include_buttons = QHBoxLayout()
        include_select_all_btn = QPushButton("全选")
        include_clear_all_btn = QPushButton("清空")
        include_select_all_btn.setStyleSheet("* {font-size: XXXXX;}".replace("XXXXX",self.config.get_font_size()))
        include_clear_all_btn.setStyleSheet("* {font-size: XXXXX;}".replace("XXXXX",self.config.get_font_size()))

        include_select_all_btn.clicked.connect(self.select_all_include)
        include_clear_all_btn.clicked.connect(self.clear_all_include)
        include_buttons.addWidget(include_select_all_btn)
        include_buttons.addWidget(include_clear_all_btn)
        include_buttons.addStretch()
        self.include_layout.addLayout(include_buttons)
        
        include_group.setLayout(self.include_layout)
        tags_layout.addWidget(include_group)
        
        # 右侧：排除标签
        exclude_group = QGroupBox("排除标签（不能包含以下任何标签）")
        exclude_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dc3545;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #dc3545;
            }
        """)
        
        self.exclude_layout = QVBoxLayout()
        
        # 排除标签搜索和分组控制
        exclude_control_layout = QHBoxLayout()
        exclude_control_layout.addWidget(QLabel("搜索:"))
        self.exclude_search_input = QLineEdit()
        self.exclude_search_input.setPlaceholderText("搜索排除标签...")
        self.exclude_search_input.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        self.exclude_search_input.textChanged.connect(self.filter_exclude_tags)
        exclude_control_layout.addWidget(self.exclude_search_input)
        
        # 排除标签的分组控制按钮
        self.exclude_expand_all_btn = QPushButton("展开所有分组")
        self.exclude_collapse_all_btn = QPushButton("折叠所有分组")
        self.exclude_expand_all_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
        self.exclude_collapse_all_btn.setStyleSheet("font-size: XXXXX;".replace("XXXXX",self.config.get_font_size()))
 
        self.exclude_expand_all_btn.clicked.connect(self.expand_all_exclude_groups)
        self.exclude_collapse_all_btn.clicked.connect(self.collapse_all_exclude_groups)
        
        exclude_control_layout.addStretch()
        exclude_control_layout.addWidget(self.exclude_expand_all_btn)
        exclude_control_layout.addWidget(self.exclude_collapse_all_btn)
        
        self.exclude_layout.addLayout(exclude_control_layout)
        
        # 排除标签显示区域
        self.exclude_scroll = QScrollArea()
        self.exclude_scroll.setWidgetResizable(True)
        self.exclude_widget = QWidget()
        self.exclude_tags_layout = QVBoxLayout(self.exclude_widget)
        self.exclude_tags_layout.setSpacing(1)
        self.exclude_tags_layout.setContentsMargins(5, 5, 5, 5)
        self.exclude_scroll.setWidget(self.exclude_widget)
        self.exclude_layout.addWidget(self.exclude_scroll)
        
        # 排除标签操作按钮
        exclude_buttons = QHBoxLayout()
        exclude_select_all_btn = QPushButton("全选")
        exclude_clear_all_btn = QPushButton("清空")
        exclude_select_all_btn.setStyleSheet("* {font-size: XXXXX;}".replace("XXXXX",self.config.get_font_size()))
        exclude_clear_all_btn.setStyleSheet("* {font-size: XXXXX;}".replace("XXXXX",self.config.get_font_size()))

        exclude_select_all_btn.clicked.connect(self.select_all_exclude)
        exclude_clear_all_btn.clicked.connect(self.clear_all_exclude)
        exclude_buttons.addWidget(exclude_select_all_btn)
        exclude_buttons.addWidget(exclude_clear_all_btn)
        exclude_buttons.addStretch()
        self.exclude_layout.addLayout(exclude_buttons)
        
        exclude_group.setLayout(self.exclude_layout)
        tags_layout.addWidget(exclude_group)
        
        layout.addWidget(tags_widget)
        
        # 统计信息
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        
        self.include_count_label = QLabel("包含标签: 0 个")
        self.include_count_label.setStyleSheet("color: #28a745; font-weight: bold;")
        
        self.exclude_count_label = QLabel("排除标签: 0 个")
        self.exclude_count_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        
        stats_layout.addWidget(self.include_count_label)
        stats_layout.addWidget(QLabel(" | "))
        stats_layout.addWidget(self.exclude_count_label)
        stats_layout.addStretch()
        
        layout.addWidget(stats_widget)
        
        # 状态显示标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                background: #f8f9fa;
                padding: 3px 8px;
                border-radius: 3px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        quick_buttons = QHBoxLayout()
        swap_tags_btn = QPushButton("交换包含/排除")
        swap_tags_btn.clicked.connect(self.swap_tags)
        clear_all_btn = QPushButton("清除所有筛选")
        clear_all_btn.clicked.connect(self.clear_all_filters)
        quick_buttons.addWidget(swap_tags_btn)
        quick_buttons.addWidget(clear_all_btn)
        quick_buttons.addStretch()
        button_layout.addLayout(quick_buttons)
        
        cancel_btn = QPushButton("取消")
        apply_btn = QPushButton("应用筛选")

        cancel_btn.clicked.connect(self.reject)
        apply_btn.clicked.connect(self.apply_filters)
        cancel_btn.setStyleSheet("* {font-size: XXXXX;}".replace("XXXXX",self.config.get_font_size()))
        apply_btn.setStyleSheet("* {font-size: XXXXX;}".replace("XXXXX",self.config.get_font_size()))
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 初始显示标签
        self.display_all_tags()
        self.update_counts()
        self.expand_all_exclude_groups()
        self.expand_all_include_groups()



        
    def show_status_message(self, message, timeout=3000):
        """显示状态消息"""
        self.status_label.setText(message)
        
        # 如果有超时设置，使用定时器清除消息
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.status_label.setText(""))
    
    def load_author_statistics(self):
        """从CSV文件中加载作者统计信息，生成临时标签"""
        try:
            if not os.path.exists(self.csv_file):
                print(f"CSV文件不存在: {self.csv_file}")
                return
            
            # 读取CSV文件
            import pandas as pd
            df = pd.read_csv(self.csv_file, encoding='gb18030')
            
            # 统计作者包数量
            author_counts = df['author'].value_counts()
            
            # 生成临时作者标签（只包含包数量大于3的作者）
            for author, count in author_counts.items():
                if count > 2:
                    # 使用特定的分隔符来避免下划线冲突
                    # 修改：使用双下划线作为分隔符，避免与作者名中的单下划线冲突
                    full_tag = f"{self.author_group_name}__{author}"
                    
                    # 保存到作者标签列表
                    self.author_tags.append({
                        'display': f"{author} ({count}个包)",
                        'full': full_tag,
                        'group': self.author_group_name,
                        'author': author,
                        'count': count
                    })
            
            print(f"已加载 {len(self.author_tags)} 个作者临时标签")
            
            # 按包数量降序排序
            self.author_tags.sort(key=lambda x: x['count'], reverse=True)
            
        except Exception as e:
            print(f"加载作者统计信息失败: {e}")

    def parse_tags_into_groups(self):
        """解析标签分组 - 修改后包含作者临时标签"""
        self.tag_groups = {}
        
        # 1. 添加作者临时标签分组
        if self.author_tags:
            if self.author_group_name not in self.tag_groups:
                self.tag_groups[self.author_group_name] = []
            
            # 添加作者风格标签到分组
            for tag_info in self.author_tags:
                # 确保tag_info包含author信息
                author = tag_info.get('author', '')
                if author and author in self.author_categories:
                    category = self.author_categories[author]
                    # 在display中添加分类标记
                    original_display = tag_info['display']
                    tag_info['display'] = f"{original_display} [{category}]"
                    tag_info['category'] = category  # 保存分类信息
                
                self.tag_groups[self.author_group_name].append({
                    'display': tag_info['display'],
                    'full': tag_info['full'],
                    'group': self.author_group_name,
                    'author': tag_info.get('author', ''),  # 确保传递author信息
                    'category': tag_info.get('category', ''),  # 传递分类信息
                    'count': tag_info.get('count', 0)
                })
        
        
        # # 1. 添加作者临时标签分组
        # if self.author_tags:
        #     if self.author_group_name not in self.tag_groups:
        #         self.tag_groups[self.author_group_name] = []
            
        #     # 添加作者标签到分组
        #     for tag_info in self.author_tags:
        #         self.tag_groups[self.author_group_name].append({
        #             'display': tag_info['display'],
        #             'full': tag_info['full'],
        #             'group': self.author_group_name
        #         })
        
        # 2. 添加普通标签分组
        for tag in self.all_tags:
            # 首先检查是否是作者临时标签（使用双下划线分隔）
            if tag.startswith(f"{self.author_group_name}__"):
                # 这是作者临时标签，已经处理过，跳过
                continue
            
            # 检查是否有下划线分隔（普通标签的分组）
            if '_' in tag:
                parts = tag.split('_', 1)
                group_name = parts[0].strip()
                tag_name = parts[1].strip()
                
                if group_name not in self.tag_groups:
                    self.tag_groups[group_name] = []
                
                # 保存标签信息
                self.tag_groups[group_name].append({
                    'display': tag_name,
                    'full': tag,
                    'group': group_name
                })
            else:
                # 无分组的标签放入"未分组"
                if "未分组" not in self.tag_groups:
                    self.tag_groups["未分组"] = []
                
                self.tag_groups["未分组"].append({
                    'display': tag,
                    'full': tag,
                    'group': "未分组"
                })
    
    def display_all_tags(self):
        """显示所有标签"""
        # 包含标签：显示所有标签，但禁用已经在排除标签中的标签
        self.display_include_tags()
        # 排除标签：显示所有标签，但禁用已经在包含标签中的标签
        self.display_exclude_tags()
    
    def display_include_tags(self):
        """显示包含标签"""
        # 清空现有内容
        while self.include_tags_layout.count():
            item = self.include_tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.include_checkboxes = []
        self.include_group_widgets.clear()
        
        # 按分组显示
        for group_name in sorted(self.tag_groups.keys()):
            tags = self.tag_groups[group_name]
            
            # 根据搜索条件过滤
            search_text = self.include_search_input.text().strip().lower()
            if search_text:
                filtered_tags = [
                    tag_info for tag_info in tags 
                    if search_text in tag_info['full'].lower() or 
                       search_text in tag_info['display'].lower()
                ]
            else:
                filtered_tags = tags
            
            if not filtered_tags:
                continue  # 跳过空分组
            
            # 创建分组折叠控件 - 传递过滤后的标签
            group_box = self.create_group_box(group_name, filtered_tags, len(tags), "include")
            self.include_tags_layout.addWidget(group_box)
            self.include_group_widgets[group_name] = group_box
            
            # 默认展开前3个分组或已展开的分组
            if (group_name in list(sorted(self.tag_groups.keys()))[:3] or 
                group_name in self.include_expanded_groups):
                self.expand_include_group(group_name)
        
        # 添加弹性空间
        self.include_tags_layout.addStretch()

    def display_exclude_tags(self):
        """显示排除标签"""
        # 清空现有内容
        while self.exclude_tags_layout.count():
            item = self.exclude_tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.exclude_checkboxes = []
        self.exclude_group_widgets.clear()
        
        # 按分组显示
        for group_name in sorted(self.tag_groups.keys()):
            tags = self.tag_groups[group_name]
            
            # 根据搜索条件过滤
            search_text = self.exclude_search_input.text().strip().lower()
            if search_text:
                filtered_tags = [
                    tag_info for tag_info in tags 
                    if search_text in tag_info['full'].lower() or 
                       search_text in tag_info['display'].lower()
                ]
            else:
                filtered_tags = tags
            
            if not filtered_tags:
                continue  # 跳过空分组
            
            # 创建分组折叠控件 - 传递过滤后的标签
            group_box = self.create_group_box(group_name, filtered_tags, len(tags), "exclude")
            self.exclude_tags_layout.addWidget(group_box)
            self.exclude_group_widgets[group_name] = group_box
            
            # 默认展开前3个分组或已展开的分组
            if (group_name in list(sorted(self.tag_groups.keys()))[:3] or 
                group_name in self.exclude_expanded_groups):
                self.expand_exclude_group(group_name)
        
        # 添加弹性空间
        self.exclude_tags_layout.addStretch()
    
    def create_group_box(self, group_name, tags, total_count, tag_type):
        """创建分组折叠框 - 修改全选按钮逻辑"""
        group_box = QGroupBox()
        group_box.setObjectName(f"{tag_type}_group_{group_name}")
        
        # 分组标题（带折叠按钮和选择按钮）
        header_layout = QHBoxLayout()
        
        # 判断是否展开
        is_expanded = False
        if tag_type == "include":
            is_expanded = group_name in self.include_expanded_groups
        else:
            is_expanded = group_name in self.exclude_expanded_groups
        
        # 折叠/展开按钮
        toggle_btn = QPushButton("▼" if is_expanded else "▶")
        toggle_btn.setFixedSize(20, 20)
        toggle_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-weight: bold;
                color: #0078d7;
            }
        """)
        
        # 动态计算当前显示的标签数量
        visible_tags_count = len(tags)  # 这里tags已经是过滤后的
        
        # 分组标题（显示当前显示数量/总数）
        title_label = QLabel(f"{group_name} ({visible_tags_count}/{total_count})")
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: XXXXX;
                color: #495057;
            }
        """.replace("XXXXX", self.config.get_font_size()))
        
        # 分组全选按钮 - 添加lambda参数传递当前分组信息
        select_group_btn = QPushButton("全选")
        select_group_btn.setFixedSize(50, 20)
        
        # 使用闭包传递当前分组的标签信息
        if tag_type == "include":
            select_group_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #28a745;
                    background: white;
                    font-size: 10px;
                    padding: 1px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background: #28a745;
                    color: white;
                    border-color: #218838;
                }
            """)
            # 传递当前显示的标签列表
            select_group_btn.clicked.connect(
                lambda checked, gn=group_name, tl=tags: self.select_visible_include_group_tags(gn, tl)
            )
        else:
            select_group_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #dc3545;
                    background: white;
                    font-size: 10px;
                    padding: 1px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background: #dc3545;
                    color: white;
                    border-color: #c82333;
                }
            """)
            # 传递当前显示的标签列表
            select_group_btn.clicked.connect(
                lambda checked, gn=group_name, tl=tags: self.select_visible_exclude_group_tags(gn, tl)
            )
        
        header_layout.addWidget(toggle_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(select_group_btn)
        
        # ... 其余代码保持不变 ...

        header_layout.addWidget(toggle_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(select_group_btn)
        
        # 分组内的标签网格
        tags_container = QWidget()
        tags_container.setObjectName(f"{tag_type}_tags_container_{group_name}")
        tags_grid = QGridLayout(tags_container)
        tags_grid.setSpacing(8)
        tags_grid.setContentsMargins(15, 5, 5, 5)
        
        # 添加标签复选框
        for i, tag_info in enumerate(tags):
            row = i // self.config.get_columns1()
            col = i % self.config.get_columns1()
            
            checkbox = self.create_tag_checkbox(tag_info, tag_type)
            tags_grid.addWidget(checkbox, row, col)
            
            # 保存复选框引用
            if tag_type == "include":
                self.include_checkboxes.append((checkbox, tag_info['full']))
            else:
                self.exclude_checkboxes.append((checkbox, tag_info['full']))
        
        # 主布局
        main_layout = QVBoxLayout(group_box)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(tags_container)
        
        # 初始状态
        tags_container.setVisible(is_expanded)
        
        return group_box
    

    def create_tag_checkbox(self, tag_info, tag_type):
        """创建标签复选框 - 在作者标签旁添加分类标记"""
        checkbox = QCheckBox(tag_info['display'])
        checkbox.setProperty('full_tag', tag_info['full'])
        checkbox.setProperty('group', tag_info['group'])
        
        # 检查是否是作者临时标签
        is_author_tag = False
        author_name = None
        
        if 'author' in tag_info:
            is_author_tag = True
            author_name = tag_info['author']
            
            # 检查是否有对应的分类
            if author_name in self.author_categories:
                category = self.author_categories[author_name]

                # 在显示文本中添加分类标记
                current_text = checkbox.text()

                # checkbox.setText(f"{current_text} [{category}]")
                # 名称修复
                checkbox.setText(f"{current_text}")
        
        # 普通标签的处理（保持原样）
        if tag_type == "include":
            # 如果标签已经在排除标签中，禁用该复选框
            if tag_info['full'] in self.exclude_tags:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        padding: 5px;
                        border: 1px solid #ddd;
                        border-radius: 3px;
                        background: #f8f9fa;
                        color: #6c757d;
                        font-size: XXXXX;
                    }
                    QCheckBox::indicator {
                        background-color: #e9ecef;
                        border: 1px solid #dee2e6;
                    }
                """.replace("XXXXX",self.config.get_font_size()))
                checkbox.setToolTip("该标签已被选为排除标签，无法选择为包含标签")
            else:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        padding: 5px;
                        border: 1px solid #ddd;
                        border-radius: 3px;
                        background: white;
                        font-size: XXXXX;
                    }
                    QCheckBox:hover {
                        border: 1px solid #28a745;
                        background: #f0fff0;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #28a745;
                    }
                """.replace("XXXXX",self.config.get_font_size()))
                checkbox.setEnabled(True)
                checkbox.setToolTip("")
            
            # 如果标签在包含集合中，设置为选中
            if tag_info['full'] in self.include_tags:
                checkbox.setChecked(True)
            
            checkbox.stateChanged.connect(
                lambda state, t=tag_info['full']: self.on_include_tag_toggled(state, t)
            )
        else:
            # 排除标签的处理（保持原样）
            if tag_info['full'] in self.include_tags:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        padding: 5px;
                        border: 1px solid #ddd;
                        border-radius: 3px;
                        background: #f8f9fa;
                        color: #6c757d;
                        font-size: XXXXX;
                    }
                    QCheckBox::indicator {
                        background-color: #e9ecef;
                        border: 1px solid #dee2e6;
                    }
                """.replace("XXXXX",self.config.get_font_size()))
                checkbox.setToolTip("该标签已被选为包含标签，无法选择为排除标签")
            else:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        padding: 5px;
                        border: 1px solid #ddd;
                        border-radius: 3px;
                        background: white;
                        font-size: XXXXX;
                    }
                    QCheckBox:hover {
                        border: 1px solid #dc3545;
                        background: #fff0f0;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #dc3545;
                    }
                """.replace("XXXXX",self.config.get_font_size()))
                checkbox.setEnabled(True)
                checkbox.setToolTip("")
            
            # 如果标签在排除集合中，设置为选中
            if tag_info['full'] in self.exclude_tags:
                checkbox.setChecked(True)
            
            checkbox.stateChanged.connect(
                lambda state, t=tag_info['full']: self.on_exclude_tag_toggled(state, t)
            )
        
        return checkbox

    def toggle_include_group(self, group_name):
        """切换包含标签分组展开/折叠状态"""
        if group_name in self.include_expanded_groups:
            self.collapse_include_group(group_name)
        else:
            self.expand_include_group(group_name)
    
    def toggle_exclude_group(self, group_name):
        """切换排除标签分组展开/折叠状态"""
        if group_name in self.exclude_expanded_groups:
            self.collapse_exclude_group(group_name)
        else:
            self.expand_exclude_group(group_name)
    
    def expand_include_group(self, group_name):
        """展开包含标签分组"""
        if group_name in self.include_group_widgets:
            group_box = self.include_group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"include_tags_container_{group_name}")
            if tags_container:
                tags_container.setVisible(True)
            
            # 更新按钮文字
            for child in group_box.findChildren(QPushButton):
                if child.text() in ["▶", "▼"]:
                    child.setText("▼")
            
            self.include_expanded_groups.add(group_name)
    
    def collapse_include_group(self, group_name):
        """折叠包含标签分组"""
        if group_name in self.include_group_widgets:
            group_box = self.include_group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"include_tags_container_{group_name}")
            if tags_container:
                tags_container.setVisible(False)
            
            # 更新按钮文字
            for child in group_box.findChildren(QPushButton):
                if child.text() in ["▶", "▼"]:
                    child.setText("▶")
            
            self.include_expanded_groups.discard(group_name)
    
    def expand_exclude_group(self, group_name):
        """展开排除标签分组"""
        if group_name in self.exclude_group_widgets:
            group_box = self.exclude_group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"exclude_tags_container_{group_name}")
            if tags_container:
                tags_container.setVisible(True)
            
            # 更新按钮文字
            for child in group_box.findChildren(QPushButton):
                if child.text() in ["▶", "▼"]:
                    child.setText("▼")
            
            self.exclude_expanded_groups.add(group_name)
    
    def collapse_exclude_group(self, group_name):
        """折叠排除标签分组"""
        if group_name in self.exclude_group_widgets:
            group_box = self.exclude_group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"exclude_tags_container_{group_name}")
            if tags_container:
                tags_container.setVisible(False)
            
            # 更新按钮文字
            for child in group_box.findChildren(QPushButton):
                if child.text() in ["▶", "▼"]:
                    child.setText("▶")
            
            self.exclude_expanded_groups.discard(group_name)
    
    def expand_all_include_groups(self):
        """展开所有包含标签分组"""
        for group_name in self.include_group_widgets.keys():
            self.expand_include_group(group_name)
    
    def collapse_all_include_groups(self):
        """折叠所有包含标签分组"""
        for group_name in self.include_group_widgets.keys():
            self.collapse_include_group(group_name)
    
    def expand_all_exclude_groups(self):
        """展开所有排除标签分组"""
        for group_name in self.exclude_group_widgets.keys():
            self.expand_exclude_group(group_name)
    
    def collapse_all_exclude_groups(self):
        """折叠所有排除标签分组"""
        for group_name in self.exclude_group_widgets.keys():
            self.collapse_exclude_group(group_name)
    
    def filter_include_tags(self):
        """过滤包含标签"""
        self.display_include_tags()
        
        # 如果有搜索文本，自动展开所有分组
        if self.include_search_input.text().strip():
            self.expand_all_include_groups()
    
    def filter_exclude_tags(self):
        """过滤排除标签"""
        self.display_exclude_tags()
        
        # 如果有搜索文本，自动展开所有分组
        if self.exclude_search_input.text().strip():
            self.expand_all_exclude_groups()
        
    def on_include_tag_toggled(self, state, tag):
        """包含标签选择状态改变"""
        if state == Qt.Checked:
            self.include_tags.add(tag)
            # 如果同时也在排除标签中，移除排除
            if tag in self.exclude_tags:
                self.exclude_tags.remove(tag)
                # 更新排除标签的复选框状态
                self.update_exclude_checkbox_state(tag, False)
        elif tag in self.include_tags:
            self.include_tags.remove(tag)
        
        # 更新包含标签的复选框状态（主要是选中状态）
        self.update_include_checkbox_state(tag, state == Qt.Checked)
        
        # 更新统计
        self.update_counts()

    
    def on_exclude_tag_toggled(self, state, tag):
        """排除标签选择状态改变"""
        if state == Qt.Checked:
            self.exclude_tags.add(tag)
            # 如果同时也在包含标签中，移除包含
            if tag in self.include_tags:
                self.include_tags.remove(tag)
                # 更新包含标签的复选框状态
                self.update_include_checkbox_state(tag, False)
        elif tag in self.exclude_tags:
            self.exclude_tags.remove(tag)
        
        # 更新排除标签的复选框状态（主要是选中状态）
        self.update_exclude_checkbox_state(tag, state == Qt.Checked)
        
        # 更新统计
        self.update_counts()

    def update_include_checkbox_state(self, tag, checked):
        """更新包含标签复选框状态"""
        for checkbox, checkbox_tag in self.include_checkboxes:
            if checkbox_tag == tag:
                # 设置选中状态
                checkbox.setChecked(checked)
                
                # 设置启用/禁用状态
                # 如果标签在排除标签中，禁用复选框
                if tag in self.exclude_tags:
                    # checkbox.setEnabled(False)
                    checkbox.setStyleSheet("""
                        QCheckBox {
                            padding: 5px;
                            border: 1px solid #ddd;
                            border-radius: 3px;
                            background: #f8f9fa;
                            color: #6c757d;
                        }
                        QCheckBox::indicator {
                            background-color: #e9ecef;
                            border: 1px solid #dee2e6;
                        }
                    """)
                    checkbox.setToolTip("该标签已被选为排除标签，无法选择为包含标签")
                else:
                    checkbox.setEnabled(True)
                    if checked:
                        checkbox.setStyleSheet("""
                            QCheckBox {
                                padding: 5px;
                                border: 1px solid #28a745;
                                border-radius: 3px;
                                background: #f0fff0;
                            }
                            QCheckBox::indicator:checked {
                                background-color: #28a745;
                            }
                        """)
                    else:
                        checkbox.setStyleSheet("""
                            QCheckBox {
                                padding: 5px;
                                border: 1px solid #ddd;
                                border-radius: 3px;
                                background: white;
                            }
                            QCheckBox:hover {
                                border: 1px solid #28a745;
                                background: #f0fff0;
                            }
                            QCheckBox::indicator:checked {
                                background-color: #28a745;
                            }
                        """)
                    checkbox.setToolTip("")
                break  
    
    def update_exclude_checkbox_state(self, tag, checked):
        """更新排除标签复选框状态"""
        for checkbox, checkbox_tag in self.exclude_checkboxes:
            if checkbox_tag == tag:
                # 设置选中状态
                checkbox.setChecked(checked)
                
                # 设置启用/禁用状态
                # 如果标签在包含标签中，禁用复选框
                if tag in self.include_tags:
                    # checkbox.setEnabled(False)
                    checkbox.setStyleSheet("""
                        QCheckBox {
                            padding: 5px;
                            border: 1px solid #ddd;
                            border-radius: 3px;
                            background: #f8f9fa;
                            color: #6c757d;
                        }
                        QCheckBox::indicator {
                            background-color: #e9ecef;
                            border: 1px solid #dee2e6;
                        }
                    """)
                    checkbox.setToolTip("该标签已被选为包含标签，无法选择为排除标签")
                else:
                    checkbox.setEnabled(True)
                    if checked:
                        checkbox.setStyleSheet("""
                            QCheckBox {
                                padding: 5px;
                                border: 1px solid #dc3545;
                                border-radius: 3px;
                                background: #fff0f0;
                            }
                            QCheckBox::indicator:checked {
                                background-color: #dc3545;
                            }
                        """)
                    else:
                        checkbox.setStyleSheet("""
                            QCheckBox {
                                padding: 5px;
                                border: 1px solid #ddd;
                                border-radius: 3px;
                                background: white;
                            }
                            QCheckBox:hover {
                                border: 1px solid #dc3545;
                                background: #fff0f0;
                            }
                            QCheckBox::indicator:checked {
                                background-color: #dc3545;
                            }
                        """)
                    checkbox.setToolTip("")
                break

    def select_all_include(self):
        """全选包含标签"""
        # 清空当前包含标签
        self.include_tags.clear()
        
        # 添加所有标签到包含标签，但排除已经在排除标签中的标签
        for group_name, tags in self.tag_groups.items():
            for tag_info in tags:
                # 只有当标签不在排除标签中时，才添加到包含标签
                if tag_info['full'] not in self.exclude_tags:
                    self.include_tags.add(tag_info['full'])
        
        # 重新显示标签（以更新选中状态）
        self.display_include_tags()
        self.display_exclude_tags()
        
        # 更新统计
        self.update_counts()
        
        # 显示提示
        selected_count = len(self.include_tags)
        self.show_status_message(f"已全选 {selected_count} 个包含标签")
    
    def clear_all_include(self):
        """清空包含标签"""
        # 清空包含标签集合
        self.include_tags.clear()
        
        # 重新显示标签（以更新选中状态）
        self.display_include_tags()
        self.display_exclude_tags()
        
        # 更新统计
        self.update_counts()
        
        # 显示提示
        self.show_status_message("已清空所有包含标签")
    
    def select_all_exclude(self):
        """全选排除标签"""
        # 清空当前排除标签
        self.exclude_tags.clear()
        
        # 添加所有标签到排除标签，但排除已经在包含标签中的标签
        for group_name, tags in self.tag_groups.items():
            for tag_info in tags:
                # 只有当标签不在包含标签中时，才添加到排除标签
                if tag_info['full'] not in self.include_tags:
                    self.exclude_tags.add(tag_info['full'])
        
        # 重新显示标签（以更新选中状态）
        self.display_include_tags()
        self.display_exclude_tags()
        
        # 更新统计
        self.update_counts()
        
        # 显示提示
        selected_count = len(self.exclude_tags)
        self.show_status_message(f"已全选 {selected_count} 个排除标签")
    
    def clear_all_exclude(self):
        """清空排除标签"""
        # 清空排除标签集合
        self.exclude_tags.clear()
        
        # 重新显示标签（以更新选中状态）
        self.display_include_tags()
        self.display_exclude_tags()
        
        # 更新统计
        self.update_counts()
        
        # 显示提示
        self.show_status_message("已清空所有排除标签")
    
    def select_include_group_tags(self, group_name):
        """选择指定分组的所有包含标签（只选择当前显示的）"""
        if group_name in self.include_group_widgets:
            group_box = self.include_group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"include_tags_container_{group_name}")
            
            if tags_container and tags_container.isVisible():
                # 获取分组内的所有复选框（只包括当前显示的）
                checkboxes = tags_container.findChildren(QCheckBox)
                
                # 只选择可见的复选框
                selected_count = 0
                for checkbox in checkboxes:
                    if checkbox.isVisible():
                        full_tag = checkbox.property('full_tag')
                        if full_tag:
                            # 只有当标签不在排除标签中时，才添加到包含标签
                            if full_tag not in self.exclude_tags:
                                self.include_tags.add(full_tag)
                                checkbox.setChecked(True)
                                selected_count += 1
                
                # 更新统计
                self.update_counts()
                
                # 显示提示
                self.show_status_message(f"已选择 {group_name} 分组的 {selected_count} 个包含标签（当前显示）")
    
    def select_exclude_group_tags(self, group_name):
        """选择指定分组的所有排除标签（只选择当前显示的）"""
        if group_name in self.exclude_group_widgets:
            group_box = self.exclude_group_widgets[group_name]
            tags_container = group_box.findChild(QWidget, f"exclude_tags_container_{group_name}")
            
            if tags_container and tags_container.isVisible():
                # 获取分组内的所有复选框（只包括当前显示的）
                checkboxes = tags_container.findChildren(QCheckBox)
                
                # 只选择可见的复选框
                selected_count = 0
                for checkbox in checkboxes:
                    if checkbox.isVisible():
                        full_tag = checkbox.property('full_tag')
                        if full_tag:
                            # 只有当标签不在包含标签中时，才添加到排除标签
                            if full_tag not in self.include_tags:
                                self.exclude_tags.add(full_tag)
                                checkbox.setChecked(True)
                                selected_count += 1
                
                # 更新统计
                self.update_counts()
                
                # 显示提示
                self.show_status_message(f"已选择 {group_name} 分组的 {selected_count} 个排除标签（当前显示）")
    
    def swap_tags(self):
        """交换包含和排除标签"""
        # 保存原始值
        temp_include = self.include_tags.copy()
        temp_exclude = self.exclude_tags.copy()
        
        # 交换
        self.include_tags = temp_exclude
        self.exclude_tags = temp_include
        
        # 重新显示
        self.display_all_tags()
        self.update_counts()
        
        # 显示提示
        self.show_status_message("已交换包含和排除标签")
    
    def clear_all_filters(self):
        """清除所有筛选"""
        self.include_tags.clear()
        self.exclude_tags.clear()
        
        # 清空搜索框
        self.include_search_input.clear()
        self.exclude_search_input.clear()
        
        # 重新显示
        self.display_all_tags()
        self.update_counts()
        
        # 显示提示
        self.show_status_message("已清除所有筛选")
    
    def update_counts(self):
        """更新统计信息"""
        include_count = len(self.include_tags)
        exclude_count = len(self.exclude_tags)
        
        self.include_count_label.setText(f"包含标签: {include_count} 个")
        self.exclude_count_label.setText(f"排除标签: {exclude_count} 个")
        
        # 设置工具提示显示具体标签
        if include_count > 0:
            include_text = ",".join(sorted(self.include_tags))
            if len(include_text) > 100:
                include_text = include_text[:97] + "..."
            self.include_count_label.setToolTip(f"包含的标签: {include_text}")
        else:
            self.include_count_label.setToolTip("")
        
        if exclude_count > 0:
            exclude_text = ",".join(sorted(self.exclude_tags))
            if len(exclude_text) > 100:
                exclude_text = exclude_text[:97] + "..."
            self.exclude_count_label.setToolTip(f"排除的标签: {exclude_text}")
        else:
            self.exclude_count_label.setToolTip("")
    
    def apply_filters(self):
        """应用筛选"""
        # 显示应用提示
        include_count = len(self.include_tags)
        exclude_count = len(self.exclude_tags)
        self.show_status_message(f"已应用筛选: 包含 {include_count} 个, 排除 {exclude_count} 个")
        
        # 延迟接受对话框
        QTimer.singleShot(500, self.accept)
    
    def get_include_tags(self):
        """获取包含标签"""
        return self.include_tags
    
    def get_exclude_tags(self):
        """获取排除标签"""
        return self.exclude_tags
    
    def load_author_categories(self):
        # 定位2 
        """从authors_categories.csv文件中加载作者分类信息"""
        try:
            category_file = "authors_categories.csv"
            print(f"尝试加载作者分类文件: {category_file}")
            if os.path.exists(category_file):
                print("文件存在，开始读取...")
                with open(category_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    row_count = 0
                    for row in reader:
                        row_count += 1
                        author = row.get('author', '').strip()
                        category = row.get('category', '').strip()
                        
                        # print(f"第{row_count}行: author='{author}', category='{category}'")
                        
                        if author and category:
                            # 保存作者分类信息
                            self.author_categories[author] = category
                            # print(f"添加作者分类: {author} -> {category}")
                
                print(f"已加载 {len(self.author_categories)} 个作者分类")
                # print(f"作者分类字典: {self.author_categories}")
            else:
                print(f"作者分类文件不存在: {category_file}")
        except Exception as e:
            print(f"加载作者分类失败: {e}")
            import traceback
            traceback.print_exc()

    def select_visible_include_group_tags(self, group_name, visible_tags):
        """选择指定分组当前显示的所有包含标签"""
        if not visible_tags:
            self.show_status_message(f"{group_name} 分组当前没有显示任何标签")
            return
        
        selected_count = 0
        for tag_info in visible_tags:
            full_tag = tag_info['full']
            # 只有当标签不在排除标签中时，才添加到包含标签
            if full_tag not in self.exclude_tags:
                self.include_tags.add(full_tag)
                selected_count += 1
        
        # 更新包含标签复选框状态
        self.update_include_checkboxes_for_tags([tag_info['full'] for tag_info in visible_tags], True)
        
        # 更新排除标签复选框状态（因为包含和排除互斥）
        self.update_exclude_checkboxes_for_tags([tag_info['full'] for tag_info in visible_tags], False)
        
        # 更新统计
        self.update_counts()
        
        # 显示提示
        self.show_status_message(f"已选择 {group_name} 分组的 {selected_count} 个包含标签（当前显示）")

    def select_visible_exclude_group_tags(self, group_name, visible_tags):
        """选择指定分组当前显示的所有排除标签"""
        if not visible_tags:
            self.show_status_message(f"{group_name} 分组当前没有显示任何标签")
            return
        
        selected_count = 0
        for tag_info in visible_tags:
            full_tag = tag_info['full']
            # 只有当标签不在包含标签中时，才添加到排除标签
            if full_tag not in self.include_tags:
                self.exclude_tags.add(full_tag)
                selected_count += 1
        
        # 更新排除标签复选框状态
        self.update_exclude_checkboxes_for_tags([tag_info['full'] for tag_info in visible_tags], True)
        
        # 更新包含标签复选框状态（因为包含和排除互斥）
        self.update_include_checkboxes_for_tags([tag_info['full'] for tag_info in visible_tags], False)
        
        # 更新统计
        self.update_counts()
        
        # 显示提示
        self.show_status_message(f"已选择 {group_name} 分组的 {selected_count} 个排除标签（当前显示）")

    def update_include_checkboxes_for_tags(self, tags, checked):
        """批量更新包含标签复选框状态"""
        for tag in tags:
            self.update_include_checkbox_state(tag, checked)

    def update_exclude_checkboxes_for_tags(self, tags, checked):
        """批量更新排除标签复选框状态"""
        for tag in tags:
            self.update_exclude_checkbox_state(tag, checked)

class BatchTagDialog(QDialog):
    """批量标签操作对话框"""
    
    def __init__(self, all_tags, selected_packages_count, operation_type="add", parent=None, common_tags=None):
        super().__init__(parent)
        self.config = ConfigManager("config.json")
        self.all_tags = sorted(all_tags)
        self.selected_packages_count = selected_packages_count
        self.operation_type = operation_type  # "add" 或 "remove"
        self.selected_tags = set()
        self.common_tags = common_tags or set()  # 新增：公共标签
        self.initUI()
        
    def initUI(self):
        """初始化UI"""
        operation_text = "添加" if self.operation_type == "add" else "删除"
        window_title = f"批量{operation_text}标签"
        
        # 如果有公共标签，在标题中显示
        if self.common_tags and self.operation_type == "remove":
            window_title += f" (共 {len(self.common_tags)} 个公共标签)"
        
        self.setWindowTitle(window_title)
        self.setGeometry(0, 0, self.config.get_window_size()[0]-10, self.config.get_window_size()[1]-100)
        layout = QVBoxLayout()
        
        # 标题
        title_text = f"为 {self.selected_packages_count} 个选中的包批量{operation_text}标签"
        
        # 如果是删除操作且有公共标签，显示公共标签信息
        if self.common_tags and self.operation_type == "remove":
            common_tags_text = ", ".join(sorted(self.common_tags)[:5])  # 只显示前5个
            if len(self.common_tags) > 5:
                common_tags_text += f" ...等 {len(self.common_tags)} 个"
            
            title_text += f"\n共有 {len(self.common_tags)} 个公共标签: {common_tags_text}"
        
        title_label = QLabel(title_text)
        title_label.setStyleSheet("""
            font-size: XXXXX; 
            font-weight: bold; 
            margin-bottom: 10px; 
            color: #0078d7;
            padding: 10px;
            background: #f0f8ff;
            border-radius: 5px;
            border: 1px solid #b3d9ff;
        """.replace("XXXXX",self.config.get_font_size()))
        title_label.setWordWrap(True)  # 支持换行
        layout.addWidget(title_label)
        
        # 如果是删除操作且有公共标签，添加说明标签
        if self.common_tags and self.operation_type == "remove":
            info_label = QLabel("💡 提示: 绿色背景的标签是选中的包共有的标签")
            info_label.setStyleSheet("""
                font-size: XXXXX; 
                color: #155724; 
                margin-bottom: 10px; 
                background: #d4edda; 
                padding: 8px; 
                border-radius: 3px;
                border: 1px solid #c3e6cb;
                font-weight: bold;
            """.replace("XXXXX",self.config.get_font_size()))
            layout.addWidget(info_label)
        
        # 创建两列布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # 左侧：标签显示区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索标签:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索标签...")
        self.search_input.textChanged.connect(self.filter_tags)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)
        
        # 标签显示区域（网格布局）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.tags_container = QWidget()
        self.tags_layout = QGridLayout(self.tags_container)
        self.tags_layout.setSpacing(8)
        self.tags_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.tags_container)
        left_layout.addWidget(scroll_area)
        
        # 添加到主布局
        main_layout.addWidget(left_widget, 2)  # 左侧占2/3
        
        # 右侧：信息面板（只在有公共标签时显示）
        if self.common_tags and self.operation_type == "remove":
            right_widget = QWidget()
            right_widget.setMaximumWidth(300)  # 限制宽度
            right_layout = QVBoxLayout(right_widget)
            
            # 公共标签面板
            common_panel = QGroupBox("公共标签详情")
            common_panel.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: XXXXX;
                    color: #155724;
                    border: 2px solid #28a745;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
            """.replace("XXXXX",self.config.get_font_size()))
            
            common_inner_layout = QVBoxLayout()
            
            # 公共标签列表
            common_label = QLabel(f"共有 {len(self.common_tags)} 个公共标签:")
            common_label.setStyleSheet("font-weight: bold; color: #155724;")
            common_inner_layout.addWidget(common_label)
            
            # 滚动区域显示公共标签
            common_scroll = QScrollArea()
            common_scroll.setWidgetResizable(True)
            common_scroll.setMinimumHeight(200)
            
            common_list_widget = QWidget()
            common_list_layout = QVBoxLayout(common_list_widget)
            
            for tag in sorted(self.common_tags):
                tag_label = QLabel(f"• {tag}")
                tag_label.setStyleSheet("""
                    QLabel {
                        padding: 4px 8px;
                        margin: 2px;
                        background-color: #d4edda;
                        border: 1px solid #c3e6cb;
                        border-radius: 3px;
                        font-size: XXXXX;
                        color: #155724;
                    }
                """)
                common_list_layout.addWidget(tag_label)
            
            common_list_layout.addStretch()
            common_scroll.setWidget(common_list_widget)
            common_inner_layout.addWidget(common_scroll)
            
            # 操作按钮
            common_btn_layout = QHBoxLayout()
            select_common_btn = QPushButton("全选公共标签")
            select_common_btn.clicked.connect(self.select_common_tags)
            select_common_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 4px;
                    border: none;
                    font-size: XXXXX;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """.replace("XXXXX",self.config.get_font_size()))
            
            common_btn_layout.addWidget(select_common_btn)
            common_inner_layout.addLayout(common_btn_layout)
            
            common_panel.setLayout(common_inner_layout)
            right_layout.addWidget(common_panel)
            
            # 统计信息面板
            stats_panel = QGroupBox("统计信息")
            stats_panel.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: XXXXX;
                    color: #0078d7;
                    border: 2px solid #0078d7;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 15px;
                }
            """.replace("XXXXX",self.config.get_font_size()))
            
            stats_inner_layout = QVBoxLayout()
            
            stats_data = QLabel(
                f"选中的包数: {self.selected_packages_count}\n"
                f"公共标签数: {len(self.common_tags)}\n"
                f"所有标签数: {len(self.all_tags)}\n"
                f"已选择标签: 0 个"
            )
            stats_data.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    line-height: 1.5;
                    color: #495057;
                }
            """)
            self.stats_data_label = stats_data  # 保存引用以便更新
            
            stats_inner_layout.addWidget(stats_data)
            stats_panel.setLayout(stats_inner_layout)
            right_layout.addWidget(stats_panel)
            
            right_layout.addStretch()
            main_layout.addWidget(right_widget, 1)  # 右侧占1/3
        
        # 将主部件添加到布局
        layout.addWidget(main_widget)
        
        # 自定义标签输入（仅添加操作可用）
        if self.operation_type == "add":
            custom_layout = QHBoxLayout()
            custom_label = QLabel("自定义新标签:")
            self.custom_input = QLineEdit()
            self.custom_input.setPlaceholderText("输入新标签，用逗号分隔")
            add_custom_btn = QPushButton("添加")
            add_custom_btn.clicked.connect(self.add_custom_tags)
            
            custom_layout.addWidget(custom_label)
            custom_layout.addWidget(self.custom_input)
            custom_layout.addWidget(add_custom_btn)
            layout.addLayout(custom_layout)
        
        # 统计信息
        self.stats_label = QLabel(f"已选择 0 个标签")
        self.stats_label.setStyleSheet("""
            color: #0078d7; 
            font-weight: bold;
            background: #e8f4ff;
            padding: 10px;
            border-radius: 3px;
            border: 1px solid #b3d9ff;
        """)
        layout.addWidget(self.stats_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 左侧操作按钮
        left_buttons = QHBoxLayout()
        select_all_btn = QPushButton("全选所有标签")
        clear_all_btn = QPushButton("清空选择")
        
        select_all_btn.clicked.connect(self.select_all_tags)
        clear_all_btn.clicked.connect(self.clear_all_tags)
        
        left_buttons.addWidget(select_all_btn)
        left_buttons.addWidget(clear_all_btn)
        
        # 如果是删除操作且有公共标签，添加"仅选择公共标签"按钮
        if self.common_tags and self.operation_type == "remove":
            select_only_common_btn = QPushButton("仅选择公共标签")
            select_only_common_btn.clicked.connect(self.select_only_common_tags)
            select_only_common_btn.setStyleSheet("""
                QPushButton {
                    background-color: #20c997;
                    color: white;
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 4px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #1ba87e;
                }
            """)
            left_buttons.addWidget(select_only_common_btn)
        
        left_buttons.addStretch()
        button_layout.addLayout(left_buttons)
        
        # 右侧操作按钮
        right_buttons = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        confirm_btn = QPushButton(f"确定{operation_text}")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept)
        
        right_buttons.addWidget(cancel_btn)
        right_buttons.addWidget(confirm_btn)
        button_layout.addLayout(right_buttons)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 显示所有标签
        self.display_all_tags()
    
    def display_all_tags(self):
        """显示所有标签，高亮公共标签"""
        # 清空现有内容
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.tag_checkboxes = []
        self.tag_labels = []
        
        # 按字母顺序排序
        sorted_tags = sorted(self.all_tags)
        
        # 网格布局，每行3列（增加每行列数以显示更多标签）
        columns = self.config.get_columns1()
        
        for i, tag in enumerate(sorted_tags):
            row = i // columns
            col = i % columns
            
            # 创建复选框
            checkbox = QCheckBox(tag)
            
            # 如果是公共标签，高亮显示
            if tag in self.common_tags and self.operation_type == "remove":
                checkbox.setStyleSheet("""
                    QCheckBox {
                        padding: 8px;
                        border: 1px solid #c3e6cb;
                        border-radius: 4px;
                        background-color: #d4edda;
                        font-weight: bold;
                        color: #155724;
                        font-size: XXXXX;
                    }
                    QCheckBox:hover {
                        border: 2px solid #28a745;
                        background-color: #c3e6cb;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #28a745;
                        border: 1px solid #218838;
                    }
                """.replace("XXXXX",self.config.get_font_size()))
            else:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        padding: 8px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        background-color: white;
                        font-size: XXXXX;
                    }
                    QCheckBox:hover {
                        border: 1px solid #0078d7;
                        background-color: #f0f8ff;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #0078d7;
                    }
                """.replace("XXXXX",self.config.get_font_size()))
            
            # 添加工具提示
            if tag in self.common_tags and self.operation_type == "remove":
                checkbox.setToolTip(f"✔ 这是选中的 {self.selected_packages_count} 个包共有的标签")
            
            checkbox.stateChanged.connect(
                lambda state, t=tag: self.on_tag_toggled(state, t)
            )
            
            self.tag_checkboxes.append(checkbox)
            self.tags_layout.addWidget(checkbox, row, col)
        
        # 更新统计
        self.update_stats()

    def select_common_tags(self):
        """选择所有公共标签"""
        for checkbox in self.tag_checkboxes:
            tag = checkbox.text()
            if tag in self.common_tags:
                checkbox.setChecked(True)
                self.selected_tags.add(tag)
        
        self.update_stats()
        QMessageBox.information(self, "操作成功", f"已选择 {len(self.common_tags)} 个公共标签")

    def select_only_common_tags(self):
        """仅选择公共标签（清空其他选择）"""
        # 清空所有选择
        for checkbox in self.tag_checkboxes:
            checkbox.setChecked(False)
        
        self.selected_tags.clear()
        
        # 只选择公共标签
        for checkbox in self.tag_checkboxes:
            tag = checkbox.text()
            if tag in self.common_tags:
                checkbox.setChecked(True)
                self.selected_tags.add(tag)
        
        self.update_stats()
        QMessageBox.information(self, "操作成功", f"已选择 {len(self.common_tags)} 个公共标签")

    
    def filter_tags(self):
        """过滤标签"""
        search_text = self.search_input.text().strip().lower()
        
        # 隐藏所有标签
        for i, checkbox in enumerate(self.tag_checkboxes):
            checkbox.setVisible(False)
        
        # 显示匹配的标签
        for i, checkbox in enumerate(self.tag_checkboxes):
            tag_text = checkbox.text().lower()
            if not search_text or search_text in tag_text:
                checkbox.setVisible(True)
        
        # 重新布局
        visible_checkboxes = [cb for cb in self.tag_checkboxes if cb.isVisible()]
        for i, checkbox in enumerate(visible_checkboxes):
            row = i // 4
            col = i % 4
            self.tags_layout.addWidget(checkbox, row, col)
    
    def on_tag_toggled(self, state, tag):
        """标签选择状态改变"""
        if state == Qt.Checked:
            self.selected_tags.add(tag)
        elif tag in self.selected_tags:
            self.selected_tags.remove(tag)
        
        self.update_stats()
    
    def select_all_tags(self):
        """全选所有标签"""
        for checkbox in self.tag_checkboxes:
            if checkbox.isVisible():
                checkbox.setChecked(True)
                tag = checkbox.text()
                self.selected_tags.add(tag)
        
        self.update_stats()
    
    def clear_all_tags(self):
        """清空所有选择"""
        for checkbox in self.tag_checkboxes:
            checkbox.setChecked(False)
        
        self.selected_tags.clear()
        self.update_stats()
    
    def add_custom_tags(self):
        """添加自定义标签"""
        custom_tags_text = self.custom_input.text().strip()
        if not custom_tags_text:
            QMessageBox.information(self, "提示", "请输入标签")
            return
        
        # 解析标签（支持逗号、空格分隔）
        new_tags = []
        for tag in custom_tags_text.replace(',', ' ').split():
            tag_clean = tag.strip()
            if tag_clean and tag_clean not in self.all_tags:
                new_tags.append(tag_clean)
        
        if not new_tags:
            QMessageBox.information(self, "提示", "没有有效的标签或标签已存在")
            return
        
        # 添加到标签列表
        for tag in new_tags:
            self.all_tags.append(tag)
        
        # 重新显示标签
        self.display_all_tags()
        
        # 自动选中新添加的标签
        for tag in new_tags:
            self.selected_tags.add(tag)
            # 找到对应的复选框并选中
            for checkbox in self.tag_checkboxes:
                if checkbox.text() == tag:
                    checkbox.setChecked(True)
                    break
        
        # 清空输入框
        self.custom_input.clear()
        
        # 更新统计
        self.update_stats()
        
        QMessageBox.information(self, "成功", f"已添加 {len(new_tags)} 个新标签")
    
    def update_stats(self):
        """更新统计信息"""
        count = len(self.selected_tags)
        self.stats_label.setText(f"已选择 {count} 个标签")
        
        # 计算选择的公共标签数量
        common_selected = len(self.selected_tags.intersection(self.common_tags))
        
        # 设置工具提示
        if count > 0:
            tags_text = ", ".join(sorted(self.selected_tags))
            if len(tags_text) > 150:
                tags_text = tags_text[:147] + "..."
            
            stats_text = f"选中的标签: {tags_text}"
            if self.common_tags:
                stats_text += f"\n其中公共标签: {common_selected} 个"
            
            self.stats_label.setToolTip(stats_text)
        else:
            self.stats_label.setToolTip("")
        
        # 更新右侧统计信息（如果存在）
        if hasattr(self, 'stats_data_label'):
            self.stats_data_label.setText(
                f"选中的包数: {self.selected_packages_count}\n"
                f"公共标签数: {len(self.common_tags)}\n"
                f"所有标签数: {len(self.all_tags)}\n"
                f"已选择标签: {count} 个\n"
                f"其中公共标签: {common_selected} 个"
            )
    
    def get_selected_tags(self):
        """获取用户选择的标签"""
        return sorted(self.selected_tags)

# 7 advanced_package_grabber.py
class AnalysisTagFilterDialog(QDialog):
    """分析标签筛选对话框"""
    def __init__(self, all_tags, selected_tags, exclude_tags, parent=None):
        super().__init__(parent)
        self.config = ConfigManager("config.json")
        self.all_tags = sorted(all_tags)
        self.selected_tags = set(selected_tags)
        self.exclude_tags = set(exclude_tags)
        
        # 新增：存储标签对应的包数量
        self.tag_counts = {}  # 格式: {tag: count}
        self.calculate_tag_counts()  # 计算标签包数量

        self.initUI()
        self.display_tags()
        
    def initUI(self):
        self.setWindowTitle("自动包分类筛选")
        self.setGeometry(0, 0, self.config.get_window_size()[0]-100, self.config.get_window_size()[1]-200)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("选择要包含和排除的分析标签")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #0078d7;")
        layout.addWidget(title_label)
        
        # 标签区域（分两栏）
        tags_widget = QWidget()
        tags_layout = QHBoxLayout(tags_widget)
        
        # 左侧：包含标签
        include_group = QGroupBox("包含标签（必须包含以下所有分析标签）")
        include_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #28a745;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #28a745;
            }
        """)
        
        include_layout = QVBoxLayout()
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_include = QLineEdit()
        self.search_include.setPlaceholderText("搜索包含标签...")
        self.search_include.textChanged.connect(self.filter_include_tags)
        search_layout.addWidget(self.search_include)
        include_layout.addLayout(search_layout)
        
        # 标签显示区域
        self.include_scroll = QScrollArea()
        self.include_scroll.setWidgetResizable(True)
        self.include_widget = QWidget()
        self.include_grid = QGridLayout(self.include_widget)
        self.include_grid.setSpacing(5)
        self.include_grid.setContentsMargins(5, 5, 5, 5)
        self.include_scroll.setWidget(self.include_widget)
        include_layout.addWidget(self.include_scroll)
        
        # 操作按钮
        include_buttons = QHBoxLayout()
        include_select_all = QPushButton("全选")
        include_clear_all = QPushButton("清空")
        include_select_all.clicked.connect(self.select_all_include)
        include_clear_all.clicked.connect(self.clear_all_include)
        include_buttons.addWidget(include_select_all)
        include_buttons.addWidget(include_clear_all)
        include_buttons.addStretch()
        include_layout.addLayout(include_buttons)
        
        include_group.setLayout(include_layout)
        tags_layout.addWidget(include_group)
        
        # 右侧：排除标签
        exclude_group = QGroupBox("排除标签（不能包含以下任何分析标签）")
        exclude_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dc3545;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #dc3545;
            }
        """)
        
        exclude_layout = QVBoxLayout()
        
        # 搜索框
        search_layout2 = QHBoxLayout()
        search_layout2.addWidget(QLabel("搜索:"))
        self.search_exclude = QLineEdit()
        self.search_exclude.setPlaceholderText("搜索排除标签...")
        self.search_exclude.textChanged.connect(self.filter_exclude_tags)
        search_layout2.addWidget(self.search_exclude)
        exclude_layout.addLayout(search_layout2)
        
        # 标签显示区域
        self.exclude_scroll = QScrollArea()
        self.exclude_scroll.setWidgetResizable(True)
        self.exclude_widget = QWidget()
        self.exclude_grid = QGridLayout(self.exclude_widget)
        self.exclude_grid.setSpacing(5)
        self.exclude_grid.setContentsMargins(5, 5, 5, 5)
        self.exclude_scroll.setWidget(self.exclude_widget)
        exclude_layout.addWidget(self.exclude_scroll)
        
        # 操作按钮
        exclude_buttons = QHBoxLayout()
        exclude_select_all = QPushButton("全选")
        exclude_clear_all = QPushButton("清空")
        exclude_select_all.clicked.connect(self.select_all_exclude)
        exclude_clear_all.clicked.connect(self.clear_all_exclude)
        exclude_buttons.addWidget(exclude_select_all)
        exclude_buttons.addWidget(exclude_clear_all)
        exclude_buttons.addStretch()
        exclude_layout.addLayout(exclude_buttons)
        
        exclude_group.setLayout(exclude_layout)
        tags_layout.addWidget(exclude_group)
        
        layout.addWidget(tags_widget)
        
        # 统计信息
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        
        self.include_count_label = QLabel("包含标签: 0 个")
        self.include_count_label.setStyleSheet("color: #28a745; font-weight: bold;")
        
        self.exclude_count_label = QLabel("排除标签: 0 个")
        self.exclude_count_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        
        stats_layout.addWidget(self.include_count_label)
        stats_layout.addWidget(QLabel(" | "))
        stats_layout.addWidget(self.exclude_count_label)
        stats_layout.addStretch()
        
        layout.addWidget(stats_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 快捷按钮
        quick_buttons = QHBoxLayout()
        swap_btn = QPushButton("交换包含/排除")
        swap_btn.clicked.connect(self.swap_tags)
        clear_all_btn = QPushButton("清除所有筛选")
        clear_all_btn.clicked.connect(self.clear_all_filters)
        quick_buttons.addWidget(swap_btn)
        quick_buttons.addWidget(clear_all_btn)
        quick_buttons.addStretch()
        button_layout.addLayout(quick_buttons)
        
        # 确定/取消按钮
        cancel_btn = QPushButton("取消")
        apply_btn = QPushButton("应用筛选")
        cancel_btn.clicked.connect(self.reject)
        apply_btn.clicked.connect(self.apply_filters)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.update_counts()
        
    def display_tags(self):
        """显示所有分析标签"""
        self.display_include_tags()
        self.display_exclude_tags()
        
    def display_include_tags(self):
        """显示包含标签"""
        # 清空现有内容
        while self.include_grid.count():
            item = self.include_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取搜索文本
        search_text = self.search_include.text().lower().strip()
        
        # 筛选标签
        filtered_tags = []
        for tag in self.all_tags:
            if not search_text or search_text in tag.lower():
                filtered_tags.append(tag)
        
        # 显示标签
        columns = 3
        for i, tag in enumerate(filtered_tags):
            row = i // columns
            col = i % columns
            
            # 获取标签对应的包数量
            tag_count = self.tag_counts.get(tag, 0)
            
            # 创建复选框，显示标签和数量
            checkbox_text = f"{tag} ({tag_count})"
            checkbox = QCheckBox(checkbox_text)
            
            # 如果包数量大于0，高亮显示
            if tag_count > 0:
                # 设置不同数量的颜色梯度
                if tag_count > 100:
                    bg_color = "#dc3545"  # 红色，非常多
                    text_color = "#ffffff"
                elif tag_count > 50:
                    bg_color = "#ffc107"  # 黄色，很多
                    text_color = "#212529"
                elif tag_count > 20:
                    bg_color = "#28a745"  # 绿色，较多
                    text_color = "#ffffff"
                elif tag_count > 10:
                    bg_color = "#20c997"  # 青色
                    text_color = "#ffffff"
                elif tag_count > 5:
                    bg_color = "#17a2b8"  # 蓝色
                    text_color = "#ffffff"
                else:
                    bg_color = "#6c757d"  # 灰色，少量
                    text_color = "#ffffff"
                
                checkbox.setStyleSheet(f"""
                    QCheckBox {{
                        padding: 8px;
                        border: 2px solid {bg_color};
                        border-radius: 5px;
                        background-color: {bg_color};
                        color: {text_color};
                        font-weight: bold;
                    }}
                    QCheckBox:hover {{
                        border: 2px solid #007bff;
                        background-color: #0056b3;
                    }}
                """)
            else:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        padding: 8px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        background-color: #f8f9fa;
                        color: #6c757d;
                    }
                    QCheckBox:hover {
                        border: 1px solid #28a745;
                        background: #f0fff0;
                    }
                """)
            
            # 添加工具提示，显示详细信息
            tooltip_text = f"标签: {tag}\n"
            tooltip_text += f"包数量: {tag_count}"
            if tag_count > 0:
                tooltip_text += "\n\n包含此标签的包:"
                # 列出前5个包
                displayed_count = 0
                for package in self.parent().var_data:
                    author = package.get('author', '')
                    package_name = package.get('package_name', '')
                    version = package.get('version', '')
                    pkg_identifier = f"{author}.{package_name}.{version}"
                    
                    if pkg_identifier in self.parent().analysis_data:
                        analysis_tags = self.parent().analysis_data[pkg_identifier].get('tags', [])
                        if tag in analysis_tags:
                            tooltip_text += f"\n• {author}.{package_name}.{version}"
                            displayed_count += 1
                            if displayed_count >= 5:  # 最多显示5个
                                tooltip_text += f"\n...等{tag_count}个包"
                                break
            
            checkbox.setToolTip(tooltip_text)
            
            # 如果标签已经在排除标签中，禁用
            if tag in self.exclude_tags:
                checkbox.setEnabled(False)
                checkbox.setStyleSheet(f"""
                    QCheckBox {{
                        padding: 8px;
                        border: 1px solid #dc3545;
                        border-radius: 5px;
                        background-color: #f8d7da;
                        color: #721c24;
                    }}
                    QCheckBox:disabled {{
                        color: #999;
                    }}
                """)
            else:
                # 如果已选中，设置选中状态
                if tag in self.selected_tags:
                    checkbox.setChecked(True)
                
                # 如果数量为0，稍微降低不透明度
                if tag_count == 0:
                    checkbox.setStyleSheet("""
                        QCheckBox {
                            padding: 8px;
                            border: 1px solid #e0e0e0;
                            border-radius: 5px;
                            background-color: #f9f9f9;
                            color: #aaa;
                        }
                        QCheckBox:hover {
                            border: 1px solid #ccc;
                        }
                    """)
            
            checkbox.stateChanged.connect(
                lambda state, t=tag: self.on_include_tag_toggled(state, t)
            )
            
            self.include_grid.addWidget(checkbox, row, col)
        
        self.update_counts()
        
    def display_exclude_tags(self):
        """显示排除标签"""
        # 清空现有内容
        while self.exclude_grid.count():
            item = self.exclude_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取搜索文本
        search_text = self.search_exclude.text().lower().strip()
        
        # 筛选标签
        filtered_tags = []
        for tag in self.all_tags:
            if not search_text or search_text in tag.lower():
                filtered_tags.append(tag)
        
        # 显示标签
        columns = 3
        for i, tag in enumerate(filtered_tags):
            row = i // columns
            col = i % columns
            
            # 获取标签对应的包数量
            tag_count = self.tag_counts.get(tag, 0)
            
            # 创建复选框，显示标签和数量
            checkbox_text = f"{tag} ({tag_count})"
            checkbox = QCheckBox(checkbox_text)
            
            # 如果包数量大于0，高亮显示（与include类似但颜色不同）
            if tag_count > 0:
                if tag_count > 100:
                    bg_color = "#dc3545"
                    text_color = "#ffffff"
                elif tag_count > 50:
                    bg_color = "#e4606d"
                    text_color = "#ffffff"
                elif tag_count > 20:
                    bg_color = "#e83e8c"
                    text_color = "#ffffff"
                elif tag_count > 10:
                    bg_color = "#d63384"
                    text_color = "#ffffff"
                elif tag_count > 5:
                    bg_color = "#fd7e14"
                    text_color = "#ffffff"
                else:
                    bg_color = "#ff8c00"
                    text_color = "#ffffff"
                
                checkbox.setStyleSheet(f"""
                    QCheckBox {{
                        padding: 8px;
                        border: 2px solid {bg_color};
                        border-radius: 5px;
                        background-color: {bg_color};
                        color: {text_color};
                        font-weight: bold;
                    }}
                    QCheckBox:hover {{
                        border: 2px solid #dc3545;
                        background-color: #c82333;
                    }}
                """)
            
            # 添加工具提示
            tooltip_text = f"标签: {tag}\n包数量: {tag_count}"
            checkbox.setToolTip(tooltip_text)
            
            # 如果标签已经在包含标签中，禁用
            if tag in self.selected_tags:
                checkbox.setEnabled(False)
                checkbox.setStyleSheet(f"""
                    QCheckBox {{
                        padding: 8px;
                        border: 1px solid #28a745;
                        border-radius: 5px;
                        background-color: #d4edda;
                        color: #155724;
                    }}
                    QCheckBox:disabled {{
                        color: #999;
                    }}
                """)
            else:
                # 如果已选中，设置选中状态
                if tag in self.exclude_tags:
                    checkbox.setChecked(True)
                
                # 如果数量为0，灰色显示
                if tag_count == 0:
                    checkbox.setStyleSheet("""
                        QCheckBox {
                            padding: 8px;
                            border: 1px solid #e0e0e0;
                            border-radius: 5px;
                            background-color: #f9f9f9;
                            color: #aaa;
                        }
                        QCheckBox:hover {
                            border: 1px solid #dc3545;
                            background: #fff0f0;
                        }
                    """)
            
            checkbox.stateChanged.connect(
                lambda state, t=tag: self.on_exclude_tag_toggled(state, t)
            )
            
            self.exclude_grid.addWidget(checkbox, row, col)
        
        self.update_counts()
        
    def on_include_tag_toggled(self, state, tag):
        """包含标签选择状态改变"""
        if state == Qt.Checked:
            self.selected_tags.add(tag)
            if tag in self.exclude_tags:
                self.exclude_tags.remove(tag)
        elif tag in self.selected_tags:
            self.selected_tags.remove(tag)
        
        self.display_tags()  # 重新显示以更新状态
        self.update_counts()
        
    def on_exclude_tag_toggled(self, state, tag):
        """排除标签选择状态改变"""
        if state == Qt.Checked:
            self.exclude_tags.add(tag)
            if tag in self.selected_tags:
                self.selected_tags.remove(tag)
        elif tag in self.exclude_tags:
            self.exclude_tags.remove(tag)
        
        self.display_tags()  # 重新显示以更新状态
        self.update_counts()
        
    def filter_include_tags(self):
        """过滤包含标签"""
        self.display_include_tags()
        
    def filter_exclude_tags(self):
        """过滤排除标签"""
        self.display_exclude_tags()
        
    def select_all_include(self):
        """全选包含标签"""
        # 清除当前包含标签
        self.selected_tags.clear()
        
        # 添加所有不在排除标签中的标签
        for tag in self.all_tags:
            if tag not in self.exclude_tags:
                self.selected_tags.add(tag)
        
        self.display_tags()
        self.update_counts()
        
    def clear_all_include(self):
        """清空包含标签"""
        self.selected_tags.clear()
        self.display_tags()
        self.update_counts()
        
    def select_all_exclude(self):
        """全选排除标签"""
        # 清除当前排除标签
        self.exclude_tags.clear()
        
        # 添加所有不在包含标签中的标签
        for tag in self.all_tags:
            if tag not in self.selected_tags:
                self.exclude_tags.add(tag)
        
        self.display_tags()
        self.update_counts()
        
    def clear_all_exclude(self):
        """清空排除标签"""
        self.exclude_tags.clear()
        self.display_tags()
        self.update_counts()
        
    def swap_tags(self):
        """交换包含和排除标签"""
        temp_selected = self.selected_tags.copy()
        temp_exclude = self.exclude_tags.copy()
        
        self.selected_tags = temp_exclude
        self.exclude_tags = temp_selected
        
        self.display_tags()
        self.update_counts()
        
    def clear_all_filters(self):
        """清除所有筛选"""
        self.selected_tags.clear()
        self.exclude_tags.clear()
        self.search_include.clear()
        self.search_exclude.clear()
        
        self.display_tags()
        self.update_counts()
        
    def update_counts(self):
        """更新统计信息"""
        self.include_count_label.setText(f"包含标签: {len(self.selected_tags)} 个")
        self.exclude_count_label.setText(f"排除标签: {len(self.exclude_tags)} 个")
        
    def apply_filters(self):
        """应用筛选"""
        self.accept()
        
    def get_selected_tags(self):
        """获取包含标签"""
        return self.selected_tags
        
    def get_exclude_tags(self):
        """获取排除标签"""
        return self.exclude_tags
    def calculate_tag_counts(self):
        """计算每个标签对应的包数量"""
        if not hasattr(self.parent(), 'var_data'):
            return
            
        var_data = self.parent().filtered_packages  # 从父窗口获取包数据
        self.tag_counts = {}
        
        for tag in self.all_tags:
            count = 0
            for package in var_data:
                # 获取包标识符
                author = package.get('author', '')
                package_name = package.get('package_name', '')
                version = package.get('version', '')
                pkg_identifier = f"{author}.{package_name}.{version}"
                
                # 从分析数据中检查是否包含此标签
                if pkg_identifier in self.parent().analysis_data:
                    analysis_tags = self.parent().analysis_data[pkg_identifier].get('tags', [])
                    if tag in analysis_tags:
                        count += 1
            
            self.tag_counts[tag] = count


class VARManager(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        
        # 初始化配置管理器
        self.config = ConfigManager("config.json")
        # # 方式2：通过get_path方法访问
        self.unzip_base_dir = self.config.get_path("unzip_base_dir")
        self.output_base_dir = self.config.get_path("output_base_dir")
        self.var_scan_dir = self.config.get_path("var_scan_dir")
        self.back_ground_color = self.config.get_back_ground_color()
        self.font_color = self.config.get_font_color()
        self.font_size = self.config.get_font_size()
        self.mySstyleSheet = '* {background-color: AAA;} QLineEdit {color: XXXX;font-size: JJJJJ;background-color: GGGG;} QComboBox {color: XXXX;font-size: JJJJJ;background-color: GGGG;}\
        QPushButton {color: XXXX;font-size: JJJJJ;background-color: GGGG;} QLabel {color: XXXX;font-size: JJJJJ;background-color: GGGG;}\
        QSpinBox {color: XXXX;font-size: JJJJJ;background-color: GGGG;}'\
        .replace("AAA",self.back_ground_color).replace("GGGG",self.back_ground_color).replace("XXXX",self.font_color).replace("JJJJJ",self.font_size)\

        self.csv_file = "var_packages.csv"
        self.data_dir = "data"
        self.tag_file = os.path.join(os.getcwd(),"Files","标签.txt")  # 标签文件路径
        self.var_data = []
        self.all_tags = set()
        self.current_thumbnail_size = self.config.get_current_thumbnail_size()
        self.filter_tags = set()
        self.filtered_packages = []
        self.current_page = 1
        self.packages_per_page = int(self.config.get_packages_per_page())
        self.selected_packages = set()  # 新增：存储选中的 作者名.包名.版本
        # 新增：排序相关变量
        self.sort_by = "author"  # 默认按作者名排序
        self.sort_order = Qt.AscendingOrder  # 默认升序
        # 新增：排除标签相关变量
        self.exclude_tags = set()  # 必须排除的标签
        self.random_seed = None  # 随机种子
        self.is_random_sort = False  # 是否随机排序
        self.include_json_deps = True  # 新增：默认包含JSON依赖
        # File_info.txt的信息
        with open("File_info.txt","r", encoding='gb18030') as f:
            self.File_info_data = f.readlines()

         # 新增：依赖统计相关
        self.dependency_counter = Counter()  # 存储依赖统计
        self.dep_stats_file = self.config.get_dep_stats_path()
        self.load_dependency_stats()  # 加载依赖统计

        # 新增：得分相关属性
        self.score_weights = self.config.get_score_weights()
        self.tag_weights = self.score_weights.get("tag_weights", {})

        
        #初始化语言相关
        # 初始化语言管理器
        self.language_manager = LanguageManager(self.config.language_file)
        self.tr = self.language_manager.get_text  # 快捷方法
        self.initLanguageMenu()

        # 新增：磁盘检测标志
        self.paths_on_different_drives = self.config.are_paths_on_different_drives()
        print("self.paths_on_different_drives = ",self.paths_on_different_drives)

        # 新增：自动包分类相关属性
        self.analysis_csv_file = "var_analysis_results.csv"
        self.analysis_data = {}  # 存储分析结果：filename -> tags
        self.analysis_tags = set()  # 所有分析标签
        self.selected_analysis_tags = set()  # 选择的分析标签
        self.exclude_analysis_tags = set()  # 排除的分析标签
        # 加载分析结果
        self.load_analysis_data()

        self.initUI()
        self.load_data()
        self.last_escape_time = None
        
    def initUI(self):
        # 移除或注释掉这些设置
        # self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框
        # self.showFullScreen()  # 全屏显示
        # self.setWindowState(Qt.WindowFullScreen)  # 全屏状态
        self.setWindowTitle('Virt-A-Mate Supernova')
        self.setGeometry(0, 0, self.config.get_window_size()[0], self.config.get_window_size()[1]-150)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # ====== 创建工具栏容器 ======
        toolbar_container = QVBoxLayout()
        
        # ====== 第一行工具栏：搜索、筛选、排序 ======
        # 改为使用QWidget容器实现居中布局
        toolbar_row1_widget = QWidget()
        toolbar_row1_layout = QHBoxLayout(toolbar_row1_widget)
        toolbar_row1_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_row1_layout.setSpacing(10)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索包名、作者或标签...')
        self.search_input.textChanged.connect(self.filter_and_display)
        self.search_input.setMaximumWidth(200)
        toolbar_row1_layout.addWidget(self.search_input)
        
        # 分隔符
        toolbar_row1_layout.addWidget(self.create_vertical_line())
        
        # 排序控件组
        toolbar_row1_layout.addWidget(QLabel("排序:"))
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["作者", "包名" , "图片数量", "依赖数量", "版本号","被引用次数", "随机排序", "得分","创建日期", "处理时间"])
        self.sort_combo.setCurrentText("作者")
        self.sort_combo.currentTextChanged.connect(self.change_sort_criteria)
        self.sort_combo.setMaximumWidth(100)
        toolbar_row1_layout.addWidget(self.sort_combo)
        
        self.sort_order_btn = QToolButton()
        self.sort_order_btn.setText("升序")
        self.sort_order_btn.setCheckable(False)
        self.sort_order_btn.clicked.connect(self.toggle_sort_order)
        self.sort_order_btn.setMaximumWidth(60)
        toolbar_row1_layout.addWidget(self.sort_order_btn)
        
        # 随机种子控件
        toolbar_row1_layout.addWidget(self.create_vertical_line())
        toolbar_row1_layout.addWidget(QLabel("随机种子:"))
        
        self.random_seed_input = QSpinBox()
        self.random_seed_input.setRange(0, 999999999)
        self.random_seed_input.setValue(0)
        self.random_seed_input.setEnabled(False)
        self.random_seed_input.valueChanged.connect(self.change_random_seed)
        self.random_seed_input.setMaximumWidth(100)
        toolbar_row1_layout.addWidget(self.random_seed_input)
        
        self.refresh_random_btn = QToolButton()
        self.refresh_random_btn.setText("刷新随机")
        self.refresh_random_btn.setEnabled(False)
        self.refresh_random_btn.clicked.connect(self.refresh_random_sort)
        self.refresh_random_btn.setMaximumWidth(100)
        toolbar_row1_layout.addWidget(self.refresh_random_btn)
        
        # 标签筛选控件
        toolbar_row1_layout.addWidget(self.create_vertical_line())
        # 右侧弹性空间
        toolbar_row1_layout.addStretch()





        
        # 在标签筛选按钮附近添加
        self.analysis_filter_btn = QToolButton()
        self.analysis_filter_btn.setText("自动包分类")
        self.analysis_filter_btn.clicked.connect(self.open_analysis_filter)
        self.analysis_filter_btn.setStyleSheet("""
            QToolButton {
                background-color: #6610f2;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #590bd1;
            }
        """)
        toolbar_row1_layout.addWidget(self.analysis_filter_btn)
        self.analysis_display_label = QLabel("自动分类: 无")
        self.analysis_display_label.setStyleSheet("color: #6610f2; font-weight: bold; padding: 0 5px;")
        toolbar_row1_layout.addWidget(self.analysis_display_label)

        

        self.tag_filter_btn = QToolButton()
        self.tag_filter_btn.setText("标签筛选")
        self.tag_filter_btn.clicked.connect(self.open_tag_filter)
        self.tag_filter_btn.setStyleSheet("""
            QToolButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #218838;
            }
        """)
        toolbar_row1_layout.addWidget(self.tag_filter_btn)
        
        self.tag_display_label = QLabel("筛选: 无")
        self.tag_display_label.setStyleSheet("color: #0078d7; font-weight: bold; padding: 0 5px;")
        toolbar_row1_layout.addWidget(self.tag_display_label)
        
        clear_filter_btn = QToolButton()
        clear_filter_btn.setText("清除筛选")
        clear_filter_btn.clicked.connect(self.clear_filters)
        # 清除筛选按钮也添加对7 advanced_package_grabber.py 的支持
        clear_filter_btn.clicked.connect(lambda: (self.clear_filters(), self.clear_analysis_filters()))

        toolbar_row1_layout.addWidget(clear_filter_btn)
        
        self.export_btn = QToolButton()
        self.export_btn.setText("导出筛选CSV")
        self.export_btn.setToolTip("导出标签筛选的CSV")
        self.export_btn.clicked.connect(self.export_filtered_csv)
        toolbar_row1_layout.addWidget(self.export_btn)
        toolbar_row1_layout.addWidget(self.create_vertical_line())

        select_all_btn = QToolButton()
        select_all_btn.setText("全选当前页")
        select_all_btn.clicked.connect(self.select_all_current_page)
        toolbar_row1_layout.addWidget(select_all_btn)
        
        clear_selection_btn = QToolButton()
        clear_selection_btn.setText("清除选择")
        clear_selection_btn.clicked.connect(self.clear_selection)
        toolbar_row1_layout.addWidget(clear_selection_btn)

















        # 添加标签按钮组（居中区域）
        tag_buttons_container = QWidget()
        tag_buttons_layout = QHBoxLayout(tag_buttons_container)
        tag_buttons_layout.setSpacing(5)
        tag_buttons_layout.setContentsMargins(0, 0, 0, 0)

        # 添加弹性空间使内容居中
        toolbar_row1_layout.addStretch()

        self.add_tag_btn = QToolButton()
        self.add_tag_btn.setText("单包添加标签")
        self.add_tag_btn.setStyleSheet("""
            QToolButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #218838;
            }
        """)
        self.add_tag_btn.clicked.connect(self.open_add_tag_dialog)
        tag_buttons_layout.addWidget(self.add_tag_btn)

        self.batch_add_tag_btn = QToolButton()
        self.batch_add_tag_btn.setText("批量添加标签")
        self.batch_add_tag_btn.setStyleSheet("""
            QToolButton {
                background-color: #20c997;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #1ba87e;
            }
        """)
        self.batch_add_tag_btn.clicked.connect(self.batch_add_tags)
        self.batch_add_tag_btn.setEnabled(False)
        tag_buttons_layout.addWidget(self.batch_add_tag_btn)
        
        self.batch_remove_tag_btn = QToolButton()
        self.batch_remove_tag_btn.setText("批量删除标签")
        self.batch_remove_tag_btn.setStyleSheet("""
            QToolButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #c82333;
            }
        """)
        self.batch_remove_tag_btn.clicked.connect(self.batch_remove_tags)
        self.batch_remove_tag_btn.setEnabled(False)
        tag_buttons_layout.addWidget(self.batch_remove_tag_btn)
        
        toolbar_row1_layout.addWidget(tag_buttons_container)
        
        # 右侧弹性空间
        toolbar_row1_layout.addStretch()
        
        # ====== 第二行工具栏：分页、操作、显示控制 ======
        toolbar_row2_widget = QWidget()
        toolbar_row2_layout = QHBoxLayout(toolbar_row2_widget)
        toolbar_row2_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_row2_layout.setSpacing(10)
        
        # 分页控件组（左对齐）
        page_container = QWidget()
        page_layout = QHBoxLayout(page_container)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(5)
        
        self.prev_page_btn = QToolButton()
        self.prev_page_btn.setText("◀ 上一页")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.prev_page_btn.setEnabled(False)
        page_layout.addWidget(self.prev_page_btn)
        
        self.page_label = QLabel("第 1 页")
        self.page_label.setStyleSheet("font-weight: bold; padding: 0 10px;")
        page_layout.addWidget(self.page_label)
        
        self.next_page_btn = QToolButton()
        self.next_page_btn.setText("下一页 ▶")
        self.next_page_btn.clicked.connect(self.next_page)
        self.next_page_btn.setEnabled(False)
        page_layout.addWidget(self.next_page_btn)
        
        toolbar_row2_layout.addWidget(page_container)
        toolbar_row2_layout.addWidget(self.create_vertical_line())
        toolbar_row2_layout.addWidget(QLabel("跳到:"))
        
        self.page_input = QSpinBox()
        self.page_input.setMinimum(1)
        self.page_input.setMaximum(9999)
        self.page_input.setValue(1)
        self.page_input.setMaximumWidth(70)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.setStyleSheet("""
            QSpinBox {
                padding: 4px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
        toolbar_row2_layout.addWidget(self.page_input)
        
        self.jump_btn = QToolButton()
        self.jump_btn.setText("跳转")
        self.jump_btn.clicked.connect(self.jump_to_page)
        self.jump_btn.setStyleSheet("""
            QToolButton {
                background-color: #0078d7;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #0056b3;
            }
        """)
        toolbar_row2_layout.addWidget(self.jump_btn)

        # 操作按钮组（居中）
        toolbar_row2_layout.addStretch()
        
        operation_container = QWidget()
        operation_layout = QHBoxLayout(operation_container)
        operation_layout.setContentsMargins(0, 0, 0, 0)
        operation_layout.setSpacing(5)
        
        # 添加JSON依赖复选框
        # self.json_deps_checkbox = QCheckBox("导出选中CSV时,从所有包的JSON寻找依赖。")
        self.json_deps_checkbox = QCheckBox("从JSON寻找依赖")
        self.json_deps_checkbox.setChecked(self.include_json_deps)
        self.json_deps_checkbox.setToolTip("导出选中CSV时,讲从所有包的JSON寻找依赖。")
        operation_layout.addWidget(self.json_deps_checkbox)

        self.export_select_btn = QToolButton()
        self.export_select_btn.setText("导出选中CSV")
        self.export_select_btn.setToolTip("导出选中的CSV并添加符号链接库")
        self.export_select_btn.setStyleSheet("""
            QToolButton {
                background-color: #ffc107;
                color: #212529;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e0a800;
            }
        """)
        self.export_select_btn.clicked.connect(self.export_select_csv)
        operation_layout.addWidget(self.export_select_btn)
        
        self.locate_btn = QToolButton()
        self.locate_btn.setText("定位包目录")
        self.locate_btn.setToolTip("一键定位选中的包目录")
        self.locate_btn.setStyleSheet("""
            QToolButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #138496;
            }
        """)
        self.locate_btn.clicked.connect(self.locate_selected_package)
        operation_layout.addWidget(self.locate_btn)
        
        self.view_selected_btn = QToolButton()
        self.view_selected_btn.setText("查看选中包")
        self.view_selected_btn.setStyleSheet("""
            QToolButton {
                background-color: #6610f2;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #590bd1;
            }
        """)
        self.view_selected_btn.clicked.connect(self.view_selected_packages)
        operation_layout.addWidget(self.view_selected_btn)
        
        self.view_all_btn = QToolButton()
        self.view_all_btn.setText("查看全部包")
        self.view_all_btn.setStyleSheet("""
            QToolButton {
                background-color: #6c757d;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #5a6268;
            }
        """)
        self.view_all_btn.clicked.connect(self.view_all_packages)
        operation_layout.addWidget(self.view_all_btn)
        
        self.extract_btn = QToolButton()
        self.extract_btn.setText("提取包信息")
        self.extract_btn.setToolTip("提取选中VAR包信息")
        self.extract_btn.setStyleSheet("""
            QToolButton {
                background-color: #fd7e14;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e66a1c;
            }
        """)
        self.extract_btn.clicked.connect(self.extract_selected_var_info)
        operation_layout.addWidget(self.extract_btn)
        
        toolbar_row2_layout.addWidget(operation_container)
        
        # 大小控制（右对齐）
        toolbar_row2_layout.addStretch()
        
        size_container = QWidget()
        size_layout = QHBoxLayout(size_container)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(5)
        
        size_layout.addWidget(QLabel("大小:"))
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(100, 3000)
        self.size_slider.setValue(self.current_thumbnail_size)
        self.size_slider.valueChanged.connect(self.change_thumbnail_size)
        self.size_slider.setMaximumWidth(150)
        size_layout.addWidget(self.size_slider)
        
        self.size_label = QLabel(f"{self.current_thumbnail_size}px")
        self.size_label.setMinimumWidth(50)
        size_layout.addWidget(self.size_label)
        
        toolbar_row2_layout.addWidget(size_container)
        toolbar_row2_layout.addWidget(self.create_vertical_line())
        
        # 选择操作按钮（最右侧）
        selection_container = QWidget()
        selection_layout = QHBoxLayout(selection_container)
        selection_layout.setContentsMargins(0, 0, 0, 0)
        selection_layout.setSpacing(5)
        
        
    
        








        # 测试按钮 - 修改为三个特定路径按钮        
        toolbar_row3_widget = QWidget()
        toolbar_row3_layout = QHBoxLayout(toolbar_row3_widget)
        toolbar_row3_layout.setContentsMargins(1, 1, 1, 1)
        toolbar_row3_layout.setSpacing(1)

        # 按钮1: 打开VAR扫描目录
        self.open_scan_btn = QToolButton()
        self.open_scan_btn.setText("打开VAR目录")
        self.open_scan_btn.setStyleSheet("""
            QToolButton {
                background-color: #0078d7;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #0056b3;
            }
        """)
        self.open_scan_btn.clicked.connect(lambda: self.open_specific_path(self.var_scan_dir))
        self.open_scan_btn.setToolTip(f"打开: {self.var_scan_dir}")
        toolbar_row3_layout.addWidget(self.open_scan_btn)
        
        # 按钮2: 打开解压目录
        self.open_unzip_btn = QToolButton()
        self.open_unzip_btn.setText("打开解压目录")
        self.open_unzip_btn.setStyleSheet("""
            QToolButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #218838;
            }
        """)
        self.open_unzip_btn.clicked.connect(lambda: self.open_specific_path(self.unzip_base_dir))
        self.open_unzip_btn.setToolTip(f"打开: {self.unzip_base_dir}")
        toolbar_row3_layout.addWidget(self.open_unzip_btn)
        
        # 按钮3: 打开输=exe目录
        self.open_output_btn = QToolButton()
        self.open_output_btn.setText("打开exe目录")
        self.open_output_btn.setStyleSheet("""
            QToolButton {
                background-color: #fd7e14;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e66a1c;
            }
        """)
        self.open_output_btn.clicked.connect(lambda: self.open_specific_path(self.output_base_dir))
        self.open_output_btn.setToolTip(f"打开: {self.output_base_dir}")
        toolbar_row3_layout.addWidget(self.open_output_btn)
        
        # 按钮4: 打开person目录
        self.open_person_btn = QToolButton()
        self.open_person_btn.setText("打开person目录")
        self.open_person_btn.setStyleSheet("""
            QToolButton {
                background-color: #fd7e14;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e66a1c;
            }
        """)
        self.open_person_btn.clicked.connect(lambda: self.open_specific_path( os.path.join(self.output_base_dir,"Custom","Atom","Person") ))
        toolbar_row3_layout.addWidget(self.open_person_btn)

        # 按钮5: 打开 scene 目录
        self.open_scene_btn = QToolButton()
        self.open_scene_btn.setText("打开scene目录")
        self.open_scene_btn.setStyleSheet("""
            QToolButton {
                background-color: #fd7e14;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e66a1c;
            }
        """)
        self.open_scene_btn.clicked.connect(lambda: self.open_specific_path( os.path.join(self.output_base_dir,"Saves","scene") ))
        toolbar_row3_layout.addWidget(self.open_scene_btn)

        # 按钮6: 打开 pkg_tmp 目录
        self.open_pkg_tmp_btn = QToolButton()
        self.open_pkg_tmp_btn.setText("打开 pkg_tmp 目录")
        self.open_pkg_tmp_btn.clicked.connect(lambda: self.open_specific_path( os.path.join(self.output_base_dir,"pkg_tmp") ))
        toolbar_row3_layout.addWidget(self.open_pkg_tmp_btn)

        # +++ 新增：JSON宝贝提取按钮 +++
        self.extract_json_btn = QToolButton()
        self.extract_json_btn.setText("提取JSON中的人物")
        self.extract_json_btn.setToolTip("提取选中包中的JSON宝贝")
        self.extract_json_btn.setStyleSheet("""
            QToolButton {
                background-color: #e83e8c;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #d63384;
            }
        """)
        self.extract_json_btn.clicked.connect(self.extract_json_baby)
        toolbar_row3_layout.addWidget(self.extract_json_btn)
        
        # +++ 新增：依赖补全 +++
        self.json_extractor_btn = QToolButton()
        self.json_extractor_btn.setText("从json查看某个包的依赖,并从hub补全")
        self.json_extractor_btn.setStyleSheet("""
            QToolButton {
                background-color: #e83e8c;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #d63384;
            }
        """)
        self.json_extractor_btn.clicked.connect(self.extract_json)
        toolbar_row3_layout.addWidget(self.json_extractor_btn)





        # ====== 添加工具栏到容器 ======
        toolbar_row4_widget = QWidget()
        toolbar_row4_layout = QHBoxLayout(toolbar_row4_widget)
        toolbar_row4_layout.setContentsMargins(1, 1, 1, 1)
        toolbar_row4_layout.setSpacing(1)

        toolbar_container.addWidget(toolbar_row1_widget)
        toolbar_container.addWidget(toolbar_row2_widget)
        toolbar_container.addWidget(toolbar_row3_widget)
        toolbar_container.addWidget(toolbar_row4_widget)
        main_layout.addLayout(toolbar_container)
        
        # ====== 滚动区域（保持原有） ======
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.container_widget = QWidget()
        self.container_widget.setStyleSheet(f"* {{ background-color: {self.config.get_back_ground_color()}; }}")
        self.grid_layout = QGridLayout(self.container_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        
        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area)

        

        # +++ 新增：AI分析按钮 +++

        self.ai_analyze_btn = QToolButton()
        self.ai_analyze_btn.setText("AI包分析")
        self.ai_analyze_btn.setToolTip("使用AI分析选中的包")
        self.ai_analyze_btn.setStyleSheet("""
            QToolButton {
                background-color: #6f42c1;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #5a32a3;
            }
        """)
        self.ai_analyze_btn.clicked.connect(self.open_ai_analyzer)
        toolbar_row4_layout.addWidget(self.ai_analyze_btn)


        # +++ 新增：AI特征搜索框 +++
        self.ai_search_input = QLineEdit()
        self.ai_search_input.setPlaceholderText('搜索AI特征描述...')
        self.ai_search_input.textChanged.connect(self.filter_and_display)
        self.ai_search_input.setMaximumWidth(200)
        self.ai_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #f8f0ff;
                border: 2px solid #e0d0ff;
            }
            QLineEdit:focus {
                border: 2px solid #8a2be2;
            }
        """)
        toolbar_row4_layout.addWidget(self.ai_search_input)

        # +++ 新增：AI特征排除框 +++
        self.ai_exclude_input = QLineEdit()
        self.ai_exclude_input.setPlaceholderText('排除ai特征...')
        self.ai_exclude_input.textChanged.connect(self.filter_and_display)
        self.ai_exclude_input.setMaximumWidth(200)
        self.ai_exclude_input.setStyleSheet("""
            QLineEdit {
                background-color: #f8f0ff;
                border: 2px solid #e0d0ff;
            }
            QLineEdit:focus {
                border: 2px solid #8a2be2;
            }
        """)
        toolbar_row4_layout.addWidget(self.ai_exclude_input)

        self.File_info_input = QLineEdit()
        self.File_info_input.setPlaceholderText('File_info搜索')
        self.File_info_input.textChanged.connect(self.filter_and_display)
        self.File_info_input.setMaximumWidth(200)
        toolbar_row4_layout.addWidget(self.File_info_input)

        # 添加每页显示数量控件
        toolbar_row4_layout.addWidget(QLabel("每页显示:"))
        self.page_size_input = QSpinBox()
        self.page_size_input.setRange(1, 1000)  # 设置范围
        self.page_size_input.setValue(self.packages_per_page)
        self.page_size_input.setMaximumWidth(60)
        self.page_size_input.setAlignment(Qt.AlignCenter)
        self.page_size_input.valueChanged.connect(
            lambda value: (setattr(self, 'packages_per_page', value), self.filter_and_display())
        )
        toolbar_row4_layout.addWidget(self.page_size_input)

        print_selected_btn = QToolButton()
        print_selected_btn.setText("打印选中")
        print_selected_btn.clicked.connect(self.print_selected_packages)
        toolbar_row4_layout.addWidget(print_selected_btn)

        # +++ 新增：extract_Animation_from_scenes +++
        self.test_print_btn = QToolButton()
        self.test_print_btn.setText("extr_Ani")
        self.test_print_btn.setToolTip("点击打印 'a'")
        self.test_print_btn.setStyleSheet("""
            QToolButton {
                background-color: #ff69b4;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #ff1493;
            }
        """)
        self.test_print_btn.clicked.connect(self.extract_Animation_from_scenes)
        toolbar_row4_layout.addWidget(self.test_print_btn)
        
        # +++ 新增：extract_Animation_from_scenes_Tset +++
        self.test_print_btn = QToolButton()
        self.test_print_btn.setText("extr_Ani_Tset")
        self.test_print_btn.setToolTip("点击打印 'a'")
        self.test_print_btn.setStyleSheet("""
            QToolButton {
                background-color: #ff69b4;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #ff1493;
            }
        """)
        self.test_print_btn.clicked.connect(self.extract_Animation_from_scenes_Tset)
        toolbar_row4_layout.addWidget(self.test_print_btn)

        # ====== 状态栏 ======
        self.statusBar().showMessage('就绪')
        self.selected_count_label = QLabel("选中: 0 个包")
        self.selected_count_label.setStyleSheet("""
            QLabel {
                background-color: #e8f4ff;
                color: #0078d7;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #0078d7;
            }
        """)
        self.statusBar().addPermanentWidget(self.selected_count_label)
        
        # 用于后台加载的线程
        self.loading_thread = None
        self.stop_loading = False
        self.view_mode = "all"


    def create_vertical_line(self):
        """创建垂直分隔线"""
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #ccc;")
        line.setMaximumHeight(20)
        return line
        
    def display_packages(self, packages):
        """显示大缩略图，支持分页"""

        # 清空现有内容
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not packages:
            no_data_label = QLabel("没有找到匹配的包")
            no_data_label.setAlignment(Qt.AlignCenter)
            no_data_label.setStyleSheet("font-size: 24px; color: #888;")
            self.grid_layout.addWidget(no_data_label, 0, 0)
            self.update_page_controls()
            return
        
        # 计算总页数
        total_packages = len(packages)
        total_pages = max(1, (total_packages + self.packages_per_page - 1) // self.packages_per_page)
        
        # 确保当前页在有效范围内
        if self.current_page > total_pages:
            self.current_page = max(1, total_pages)
        
        # 获取当前页的数据
        start_idx = (self.current_page - 1) * self.packages_per_page
        end_idx = min(start_idx + self.packages_per_page, total_packages)
        current_page_packages = packages[start_idx:end_idx]
        
        # 固定2列布局
        columns = self.config.get_columns()
        
        for i, package in enumerate(current_page_packages):
            row = i // columns
            col = i % columns
            
            package_name = package.get('package_name', '')
            author = package.get('author', '')
            tags = package.get('tags', '')
            image_count = package.get('images_copied', '0')
            dependencies = package.get('dependencies', '')
            version = package.get('version', '')
            processed_time = package.get('processed_time', '')  # 新增：获取处理时间

            dep_count = self.get_dependency_count(dependencies)
            # 修改这里：传递 author 和 package_name
            preview_image = self.find_preview_image(author, package_name)
            
            # 新增：获取引用次数
            reference_count = self.get_dependency_reference_count(author, package_name)

            # +++ 新增：计算包的得分 +++
            package_score, score_details = self.calculate_package_score(package)
            package['score'] = package_score
            package['score_details'] = score_details


            # 新增：获取分析标签和创建日期
            analysis_tags = []
            creation_date = ""
            if hasattr(self, 'analysis_data'):
                package_identifier = f"{author}.{package_name}.{version}"
                analysis_info = self.analysis_data.get(package_identifier, {})
                analysis_tags = analysis_info.get('tags', [])
                creation_date = analysis_info.get('creation_date', '')



            # 创建缩略图控件
            thumbnail = ThumbnailWidget(preview_image, package_name, author, tags, image_count, dep_count, version,reference_count,package_score,processed_time,self )
            # 保存得分详情到缩略图对象
            thumbnail.score_details = score_details


            # 新增：传递分析标签和创建日期
            if analysis_tags:
                thumbnail.analysis_tags = analysis_tags
                thumbnail.analysis_text = self.format_analysis_text(analysis_tags)
                # 更新分析标签显示
                if hasattr(thumbnail, 'analysis_label'):
                    thumbnail.analysis_label.setText(thumbnail.analysis_text)
                    if analysis_tags:
                        full_analysis = "分析类别:\n" + "\n".join([f"• {tag}" for tag in analysis_tags])
                        thumbnail.analysis_label.setToolTip(full_analysis)
            
            # 新增：传递创建日期
            if creation_date:
                thumbnail.creation_date = creation_date
                formatted_date = thumbnail.format_creation_date(creation_date)
                if hasattr(thumbnail, 'date_label'):
                    thumbnail.date_label.setText(f"打包日期: 📅 {formatted_date}")
                    thumbnail.date_label.setToolTip(f"创建时间: {creation_date}")

            # 设置初始大小
            thumbnail.set_target_size(self.current_thumbnail_size)
            
            # 关键修改：根据 selected_packages 设置复选框状态
            full_identifier = f"{author}.{package_name}.{version}"
            is_selected = full_identifier in self.selected_packages
            
            # 使用 blockSignals 防止触发信号
            thumbnail.select_btn.blockSignals(True)
            thumbnail.select_btn.setChecked(is_selected)
            thumbnail.is_selected = is_selected
            thumbnail.update_selection_style()
            thumbnail.select_btn.blockSignals(False)
            
            # 连接选择信号 - 需要捕获所有相关变量
            thumbnail.select_btn.stateChanged.connect(
                lambda state, au=author, pn=package_name, ver=version: self.on_package_selected(state, au, pn, ver)
            )
                    # 检查样式
            # print(f"Thumbnail {i} 样式表: {thumbnail.styleSheet()}")
            # print(f"Thumbnail {i} objectName: {thumbnail.objectName()}")
            thumbnail.setStyleSheet(self.mySstyleSheet)
            thumbnail.clicked.connect(lambda _, au=author, pn=package_name: self.show_package_images({'author': au, 'package_name': pn}))
                    
            self.grid_layout.addWidget(thumbnail, row, col)
        
        # 更新页面控制
        self.update_page_controls(total_packages, total_pages)
        
        self.statusBar().showMessage(f'显示第 {self.current_page} 页，共 {len(current_page_packages)} 个包 (总计: {total_packages} 个包)')

    
    def update_page_controls(self, total_packages=0, total_pages=1):
        """更新分页控制按钮状态"""
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {total_pages} 页 (总计: {total_packages} 个包)")
        
        # 更新页码输入框的范围和值
        self.page_input.blockSignals(True)  # 防止触发信号
        self.page_input.setMaximum(total_pages)
        self.page_input.setValue(self.current_page)
        self.page_input.blockSignals(False)
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.filter_and_display()
            # 滚动到顶部
            self.scroll_area.verticalScrollBar().setValue(0)
    
    def next_page(self):
        """下一页"""
        self.current_page += 1
        self.filter_and_display()
        # 滚动到顶部
        self.scroll_area.verticalScrollBar().setValue(0)
    
    def preload_next_page(self, packages):
        """后台预加载下一页的图片"""
        if self.loading_thread and self.loading_thread.is_alive():
            self.stop_loading = True
            self.loading_thread.join(timeout=1)
        
        self.stop_loading = False
        next_page = self.current_page + 1
        start_idx = (next_page - 1) * self.packages_per_page
        end_idx = min(start_idx + self.packages_per_page, len(packages))
        next_page_packages = packages[start_idx:end_idx]
        
        def preload_images():
            for package in next_page_packages:
                if self.stop_loading:
                    break
                package_name = package.get('package_name', '')
                self.find_preview_image(package_name)  # 预加载图片
        
        self.loading_thread = threading.Thread(target=preload_images, daemon=True)
        self.loading_thread.start()
    
    def change_thumbnail_size(self, size):
        """修改缩略图大小"""
        self.current_thumbnail_size = size
        self.size_label.setText(f"{size}px")
        
        # 更新所有当前显示的缩略图
        self.update_all_thumbnail_sizes()
        
        # 显示提示
        self.statusBar().showMessage(f"缩略图大小已调整为: {size}px", 2000)
    def update_all_thumbnail_sizes(self):
        """更新所有当前显示的缩略图大小"""
        # 获取当前页面的所有ThumbnailWidget
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ThumbnailWidget):
                    widget.set_target_size(self.current_thumbnail_size)

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.loading_thread and self.loading_thread.is_alive():
            self.stop_loading = True
            self.loading_thread.join(timeout=1)
        super().closeEvent(event)

    def open_tag_filter(self):
        if not self.all_tags:
            QMessageBox.information(self, "提示", "没有可筛选的标签")
            return
        
        # 使用新的标签筛选对话框，传递CSV文件路径
        dialog = TagFilterDialog(self.all_tags, self.filter_tags, self.exclude_tags, self.csv_file, self)
        if dialog.exec_() == QDialog.Accepted:
            self.filter_tags = dialog.get_include_tags()
            self.exclude_tags = dialog.get_exclude_tags()
            self.update_tag_display()
            self.filter_and_display()

    def clear_filters(self):
        self.search_input.clear()
        self.filter_tags.clear()
        self.exclude_tags.clear()
        self.update_tag_display()
        self.filter_and_display()

    def export_filtered_csv(self):
        if not self.filtered_packages:
            QMessageBox.warning(self, "警告", "没有可导出的数据")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出CSV文件", "var_packages_filtered.csv", "CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='gb18030') as f:
                    fieldnames = ['filename', 'author', 'package_name', 'version', 
                                 'dependencies', 'tags', 'images_copied', 'processed_time']
                    #  extrasaction='ignore' 会忽略不在fieldnames中的字段
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    
                    writer.writeheader()
                    writer.writerows(self.filtered_packages)
                
                QMessageBox.information(self, "导出成功", f"成功导出 {len(self.filtered_packages)} 条记录")
                
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出CSV失败: {str(e)}")

    def load_data(self):
        if not os.path.exists(self.csv_file):
            QMessageBox.warning(self, '错误', f'找不到CSV文件: {self.csv_file}')
            return
            
        try:
            self.var_data = []
            self.all_tags.clear()
            
            with open(self.csv_file, 'r', encoding='gb18030') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.var_data.append(row)
                    
                    tags = row.get('tags', '').split(',')
                    for tag in tags:
                        tag_clean = tag.strip()
                        if tag_clean:
                            self.all_tags.add(tag_clean)
            
            self.filter_and_display()
            
        except Exception as e:
            # raise
            QMessageBox.critical(self, '错误', f'加载CSV失败: {str(e)}')
    
    def filter_packages(self):
        """筛选包 - 根据视图模式进行筛选"""
        search_text = self.search_input.text().lower().strip()
        ai_search_text = self.ai_search_input.text().lower().strip()
        ai_exclude_text = self.ai_exclude_input.text().lower().strip()
        File_info_text = self.File_info_input.text().lower().strip()

        filtered_data = []
        # 新增：获取分析标签筛选状态(7 advanced_package_grabber.py)
        apply_analysis_filter = len(self.selected_analysis_tags) > 0
        apply_analysis_exclude = len(self.exclude_analysis_tags) > 0


        # 获取作者临时标签筛选
        author_filter_tags = [tag for tag in self.filter_tags if tag.startswith("自动临时筛选_-author_")]
        # 提取作者名（注意分类标签格式）
        selected_authors = []
        for tag in author_filter_tags:
            # 格式可能是："自动临时筛选_-author__作者名" 或 "自动临时筛选_-author__作者名 [分类]"
            if tag.startswith("自动临时筛选_-author__"):
                # 移除前缀和可能的分类标记
                author_part = tag.split("__", 1)[1]
                # 移除分类标记（如果有）
                if " [" in author_part:
                    author_name = author_part.split(" [", 1)[0]
                else:
                    author_name = author_part
                selected_authors.append(author_name)
        
        # 获取作者排除标签
        author_exclude_tags = [tag for tag in self.exclude_tags if tag.startswith("自动临时筛选_-author_")]
        # 提取排除的作者名
        excluded_authors = []
        for tag in author_exclude_tags:
            if tag.startswith("自动临时筛选_-author__"):
                author_part = tag.split("__", 1)[1]
                if " [" in author_part:
                    author_name = author_part.split(" [", 1)[0]
                else:
                    author_name = author_part
                excluded_authors.append(author_name)
        
        # AI特征搜索
        if ai_search_text or ai_exclude_text:
            ai_packages = self.get_package_ai_description(ai_search_text, ai_exclude_text)
            cleaned_packages = [".".join(pkg.split(".")[:-1]) for pkg in ai_packages]
        
        # File_info搜索
        if File_info_text:
            File_info_packages = self.get_package_packages(File_info_text)

        for package in self.var_data:
            # 首先根据视图模式筛选
            if self.view_mode == "selected":
                package_identifier = f"{package.get('author', '')}.{package.get('package_name', '')}.{package.get('version', '')}"
                if package_identifier not in self.selected_packages:
                    continue
            
            # 作者包含筛选（如果有的话）
            if selected_authors:
                author = package.get('author', '')
                if author not in selected_authors:
                    continue
            
            # 作者排除筛选（关键修复点）
            if excluded_authors:
                author = package.get('author', '')
                if author in excluded_authors:
                    continue  # 排除这个作者的包
            
            # 获取包的标签集合
            package_tags = set(tag.strip() for tag in package.get('tags', '').split(',') if tag.strip())
            
            # 标签包含筛选：必须包含所有指定的标签（排除作者临时标签）
            regular_filter_tags = [tag for tag in self.filter_tags if not tag.startswith("自动临时筛选_-author_")]
            if regular_filter_tags:
                if not set(regular_filter_tags).issubset(package_tags):
                    continue
            
            # 标签排除筛选：不能包含任何排除的标签（排除作者临时标签）
            regular_exclude_tags = [tag for tag in self.exclude_tags if not tag.startswith("自动临时筛选_-author_")]
            if regular_exclude_tags:
                if regular_exclude_tags and set(regular_exclude_tags).intersection(package_tags):
                    continue
            
            # 搜索筛选
            if search_text:
                package_name = package.get('package_name', '').lower()
                author = package.get('author', '').lower()
                tags = package.get('tags', '').lower()
                
                if not (search_text in package_name or 
                       search_text in author or 
                       search_text in tags or ((author+"."+package_name) in search_text) ):
                    continue
            
            # AI特征搜索筛选
            if ai_search_text or ai_exclude_text:
                pkgs = package.get('author', '')+"."+package.get('package_name', '')
                if pkgs not in cleaned_packages:
                    continue
            
            # File_info_data搜索
            if File_info_text:
                pkgs = package.get('author', '')+"."+package.get('package_name', '')
                if pkgs not in File_info_packages:
                    continue


            # 新增：分析标签包含筛选
            if apply_analysis_filter:
                # 获取包的分析标签
                pkg_identifier = f"{package.get('author', '')}.{package.get('package_name', '')}.{package.get('version', '')}"
                analysis_tags = self.analysis_data.get(pkg_identifier, {}).get('tags', [])
                
                # 必须包含所有选中的分析标签
                if not set(self.selected_analysis_tags).issubset(set(analysis_tags)):
                    continue
            # 新增：分析标签排除筛选
            if apply_analysis_exclude:
                pkg_identifier = f"{package.get('author', '')}.{package.get('package_name', '')}.{package.get('version', '')}"
                analysis_tags = self.analysis_data.get(pkg_identifier, {}).get('tags', [])
                # 不能包含任何排除的分析标签
                if set(self.exclude_analysis_tags).intersection(set(analysis_tags)):
                    continue

            filtered_data.append(package)

        # 排序处理
        if filtered_data:
            filtered_data = self.sort_packages(filtered_data)
        
        return filtered_data

    def get_dependency_count(self, dep_str):
        if not dep_str:
            return "0"
        
        if dep_str in ["无依赖", "无meta.json", "meta.json解析错误"]:
            return "0"
        
        deps = [d.strip() for d in dep_str.split(',') if d.strip()]
        return str(len(deps))
    
    def find_preview_image(self, author, package_name):
        """根据作者和包名查找预览图片"""
        if not package_name or not os.path.exists(self.data_dir):
        # if not package_name or not author or not os.path.exists(self.data_dir):
            return None
        
        # 修改这里：使用 author_package_name 格式
        package_dir = os.path.join(self.data_dir, f"{author}_{package_name}_")
        if not os.path.exists(package_dir):
            return None
        
        # 优先查找常用目录（目录的优先级排序）
        preview_folders = ['scene', "Appearance","Clothing_Preset","Hair_Preset","Skin","Pose","SubScene","Clothing","Hair","Assets"]

        for folder in preview_folders:
            folder_path = os.path.join(package_dir, folder)
            if os.path.exists(folder_path):
                for file in os.listdir(folder_path):
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        return os.path.join(folder_path, file)
        
        # 搜索所有子目录
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    return os.path.join(root, file)
        
        return None
    
    def show_package_images(self, package_info):
        """显示包的图片 - 现在需要传入包含作者和包名的字典或元组"""
        # 如果传入的是包名字符串，尝试解析
        if isinstance(package_info, str):
            # 需要从当前数据中查找作者信息
            for package in self.filtered_packages:
                if package.get('package_name') == package_info:
                    author = package.get('author', '')
                    break
        else:
            author = package_info.get('author', '')
            package_name = package_info.get('package_name', '')
        
        images, image_types = self.get_package_images(author, package_name)
        
        if images:
            viewer = ImageGridViewer(images, image_types, f"{author}_{package_name} - 所有图片", self)
            viewer.exec_()
        else:
            QMessageBox.information(self, "提示", f"包 '{author}_{package_name}' 没有找到图片")


    def get_package_images(self, author, package_name):

        images = []
        image_types = []
        
        # if not package_name or not author or not os.path.exists(self.data_dir):
        if not package_name or not os.path.exists(self.data_dir):
            return images, image_types
            
        # 修改这里：使用 author_package_name 格式
        package_dir = os.path.join(self.data_dir, f"{author}_{package_name}_")
        if not os.path.exists(package_dir):
            return images, image_types
        
        type_mapping = {
            'subscene': 'subscene',
            'clothing_preset':'衣服预设',# 有优先级的
            r'hair\preset':'头发预设',
            'skin': '皮肤预设',
            'scene': '场景',
            'clothing': '衣服',
            'hair': '头发',
            'pose': '姿势',
            'appearance': '外观预设',
            'texture': '纹理',
            'plugin': '插件',
            'assets':'资产'
        }
        
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(root, file)
                    images.append(image_path)
                    
                    img_lower = image_path.lower()
                    # print(img_lower)
                    img_type = "其他"
                    for keyword, type_name in type_mapping.items():
                        if keyword in img_lower:
                            img_type = type_name
                            break
                    
                    image_types.append(img_type)
        
        return images, image_types

    def update_tag_display(self):
        """更新标签筛选显示"""
        display_texts = []
        
        # 显示包含标签
        if self.filter_tags:
            include_text = ",".join(sorted(self.filter_tags))
            if len(include_text) > 30:
                include_text = include_text[:27] + "..."
            display_texts.append(f"包含: {include_text}")
        
        # 显示排除标签
        if self.exclude_tags:
            exclude_text = ",".join(sorted(self.exclude_tags))
            if len(exclude_text) > 30:
                exclude_text = exclude_text[:27] + "..."
            display_texts.append(f"排除: {exclude_text}")
        
        if display_texts:
            display_text = " | ".join(display_texts)
            self.tag_display_label.setText(f"筛选: {display_text}")
            
            # 设置详细工具提示
            tooltip_parts = []
            if self.filter_tags:
                tooltip_parts.append(f"包含标签: {','.join(sorted(self.filter_tags))}")
            if self.exclude_tags:
                tooltip_parts.append(f"排除标签: {','.join(sorted(self.exclude_tags))}")
            
            self.tag_display_label.setToolTip("\n".join(tooltip_parts))
        else:
            self.tag_display_label.setText("筛选: 无")
            self.tag_display_label.setToolTip("")

    
    def open_add_tag_dialog(self):
        """打开添加标签对话框 - 支持单包和批量模式"""
        if len(self.selected_packages) == 0:
            QMessageBox.warning(self, "提示", "请先选择至少一个包")
            return
        
        if len(self.selected_packages) == 1:
            # 单包模式
            package_identifier = list(self.selected_packages)[0]
            
            try:
                parts = package_identifier.split('.')
                if len(parts) >= 3:
                    author, package_name, version = parts[0], parts[1], parts[2]
                    full_identifier = f"{author}.{package_name}.{version}"
                    
                    tag_dialog = TagAdderDialog(
                        var_package_name=package_name,
                        full_identifier=full_identifier,
                        csv_file=self.csv_file,
                        tag_file_path=self.tag_file,
                        parent=self
                    )
                    
                    if tag_dialog.exec_() == QDialog.Accepted:
                        selected_tags = tag_dialog.get_selected_tags()
                        if selected_tags is not None:
                            success = self.update_package_tags(package_identifier, selected_tags)
                            
                            if success:
                                self.save_updated_csv()
                                self.update_thumbnail_tags(author, package_name, version, selected_tags)
                                # QMessageBox.information(self, "成功", f"已为 {full_identifier} 更新标签")
                else:
                    QMessageBox.warning(self, "错误", f"包标识符格式错误: {package_identifier}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"处理包标识符时出错: {str(e)}")
        else:
            # 批量模式 - 调用批量添加标签方法
            self.batch_add_tags()
        self.selected_packages.clear()
        self.update_ui_for_selection()  # 更新UI状态
        self.filter_and_display()


    def update_thumbnail_tags(self, author, package_name, version, new_tags):
        """更新缩略图的标签显示"""
        # 构建完整标识符
        full_identifier = f"{author}.{package_name}.{version}"
        
        # 格式化标签文本
        if not new_tags:
            tags_text = "无"
        else:
            # 限制显示的标签数量
            if len(new_tags) > 4:
                tags_text = ",".join(new_tags[:4]) + "..."
            else:
                tags_text = ",".join(new_tags)
        
        # 遍历所有缩略图控件，更新对应的包
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ThumbnailWidget):
                    # 检查是否是目标包
                    if widget.full_identifier == full_identifier:
                        # 更新标签文本
                        widget.tags = ','.join(new_tags) if new_tags else "无"
                        widget.tags_label.setText(f"标签: {tags_text}")
                        
                        # 更新标签显示格式
                        formatted_tags = widget.format_tags(widget.tags)
                        widget.tags_label.setText(f"标签: {formatted_tags}")
                        
                        # 强制重绘
                        widget.tags_label.update()
                        break
        
        # 更新所有标签集合
        for tag in new_tags:
            self.all_tags.add(tag)
        
        # 更新状态栏
        self.statusBar().showMessage(f"已更新 {package_name} 的标签", 3000)
    def get_selected_packages(self):
        """获取当前显示的包列表（可根据需要扩展为实际选中的包）"""
        # 目前返回过滤后的包，可以扩展为实际选中的包
        return self.filtered_packages
    
    def update_package_tags(self, package_identifier, new_tags):
        """更新包的标签 - 支持完整标识符"""
        # 确保 new_tags 是列表
        if isinstance(new_tags, str):
            new_tags = [tag.strip() for tag in new_tags.split(',') if tag.strip()]
        
        # 解析标识符
        if '.' in package_identifier:
            parts = package_identifier.split('.')
            if len(parts) >= 3:
                author, package_name, version = parts[0], parts[1], parts[2]
                
                # 查找并更新数据
                for package in self.var_data:
                    if (package.get('author') == author and 
                        package.get('package_name') == package_name and 
                        package.get('version') == version):
                        
                        # 更新标签字段
                        tags_str = ','.join(new_tags) if new_tags else ''
                        package['tags'] = tags_str
                        
                        # 更新所有标签集合
                        for tag in new_tags:
                            self.all_tags.add(tag)
                        
                        return True
        else:
            # 旧的匹配方式
            for package in self.var_data:
                if package.get('package_name') == package_identifier:
                    tags_str = ','.join(new_tags) if new_tags else ''
                    package['tags'] = tags_str
                    
                    for tag in new_tags:
                        self.all_tags.add(tag)
                    
                    return True
        
        return False
    
    def save_updated_csv(self):
        """保存更新后的CSV文件"""
        try:
            # 备份原文件
            if os.path.exists(self.csv_file):
                backup_file = self.csv_file + '.bak'
                import shutil
                shutil.copy2(self.csv_file, backup_file)
            
            # 写入新文件
            with open(self.csv_file, 'w', newline='', encoding='gb18030') as f:
                if self.var_data:
                    fieldnames = self.var_data[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.var_data)
            
            self.statusBar().showMessage('标签更新已保存')
            
            # 刷新显示 - 立即更新当前页面
            self.filter_and_display()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存CSV文件失败: {str(e)}")



    def get_current_page_packages(self):
        """获取当前页面显示的包列表"""
        if not self.filtered_packages:
            return []
        
        # 计算当前页的数据范围
        start_idx = (self.current_page - 1) * self.packages_per_page
        end_idx = min(start_idx + self.packages_per_page, len(self.filtered_packages))
        # 返回当前页的包
        return self.filtered_packages[start_idx:end_idx]

    def on_package_selected(self, state, au, pn, ver):
        """处理包选择状态改变"""
        package_identifier = f"{au}.{pn}.{ver}"
        
        if state == Qt.Checked:
            self.selected_packages.add(package_identifier)
            # print(self.selected_packages)
        else:
            self.selected_packages.discard(package_identifier)
        
        # 更新当前页所有缩略图的显示状态
        self.update_thumbnail_selection_states()
        
        self.update_ui_for_selection()  # 更新UI状态
        # self.print_selected_packages()
    
    def update_thumbnail_selection_states(self):
        """更新当前页面所有缩略图的选择状态"""
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ThumbnailWidget):
                    full_identifier = widget.full_identifier
                    is_selected = full_identifier in self.selected_packages
                    
                    # 更新复选框状态，但不触发信号
                    widget.select_btn.blockSignals(True)
                    widget.select_btn.setChecked(is_selected)
                    widget.is_selected = is_selected
                    widget.update_selection_style()
                    widget.select_btn.blockSignals(False)
    
    def update_selected_count(self):
        """更新选中包数量的显示"""
        count = len(self.selected_packages)
        self.selected_count_label.setText(f"选中: {count} 个包")
        
        # 根据数量改变颜色
        if count > 0:
            self.selected_count_label.setStyleSheet("""
                QLabel {
                    background-color: #e8f4ff;
                    color: #0078d7;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                    border: 2px solid #0078d7;
                }
            """)
        else:
            self.selected_count_label.setStyleSheet("""
                QLabel {
                    background-color: #f5f5f5;
                    color: #666;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                    border: 1px solid #ddd;
                }
            """)

    def select_all_current_page(self):
        """全选当前页面的所有包"""
        current_packages = self.get_current_page_packages()
        
        # 遍历当前页面的所有ThumbnailWidget
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 检查是否是ThumbnailWidget
                if isinstance(widget, ThumbnailWidget):
                    # 获取包标识符
                    package_identifier = widget.full_identifier
                    
                    # 添加到选中的包集合
                    self.selected_packages.add(package_identifier)
                    
                    # 关键：手动设置复选框状态，但不触发信号
                    widget.select_btn.blockSignals(True)
                    widget.select_btn.setChecked(True)
                    widget.is_selected = True
                    widget.update_selection_style()
                    widget.select_btn.blockSignals(False)
        
        self.update_ui_for_selection()  # 更新UI状态
        print(f"已全选当前页，新增 {len(current_packages)} 个包")
        # self.print_selected_packages()

    def clear_selection(self):
        """清除所有选择"""
        count_before = len(self.selected_packages)
        self.selected_packages.clear()
        self.update_ui_for_selection()  # 更新UI状态
        print(f"已清除所有选择，移除了 {count_before} 个包")
        # self.print_selected_packages()
        self.filter_and_display()

    def filter_and_display(self):
        """筛选并显示包"""
        self.filtered_packages = self.filter_packages()
        self.display_packages(self.filtered_packages)
        # 打印当前选中状态
        # self.print_selected_packages()
    
    #导出
    def export_select_csv(self):
        empty_dep = []

        def create_link(source_path):
            """创建符号链接"""
            if not os.path.exists(source_path):
                print(f'{source_path}不存在,请检查磁盘是否在线！')
                return False
            
            link_name = os.path.basename(source_path)
            if link_name in created:
                return True
            
            try:
                if self.paths_on_different_drives:
                    os.makedirs(os.path.join(self.output_base_dir,r"pkg_tmp"), exist_ok=True)
                    source_path1 = os.path.join(self.output_base_dir,r"pkg_tmp", link_name)
                    if not os.path.exists(source_path1):
                        shutil.copy2(source_path, source_path1)
                    os.symlink(source_path1, os.path.join(target, link_name))
                else:
                    os.symlink(source_path, os.path.join(target, link_name))
                
                created.add(link_name)
                # print(f"✓ {link_name}")
                return True
            except Exception as e:
                print(str(e))
                print(f"✗ {link_name} export falied!")
                return False

        def find_file(author, package_name, version):
            """在var_packages中查找文件"""
            # 查找匹配的记录
            mask = (var_packages['author'] == author) & (var_packages['package_name'] == package_name)
            matches = var_packages[mask]
            if package_name =="Timeline":
                print(matches,version)
                print( matches['version'] == version )
            if matches.empty:
                return None
            
            if version.lower() == 'latest':
                # 查找最新版本
                try:
                    matches_sorted = matches.sort_values('version', ascending=False)
                    return matches_sorted.iloc[0]['filename']
                except:
                    return matches.iloc[0]['filename']
            else:
                # 查找指定版本
                exact_match = matches[matches['version'] == version]
                return exact_match.iloc[0]['filename'] if not exact_match.empty else None

        def find_json_files_in_saves(saves_directory):
            """
            在Saves目录中递归查找所有JSON文件
            """
            json_files = []
            try:
                for root, dirs, files in os.walk(saves_directory):
                    for file in files:
                        if file.lower().endswith('.json'):
                            full_path = os.path.join(root, file)
                            json_files.append(full_path)
            except Exception as e:
                print(f"搜索JSON文件时出错: {e}")
            
            return json_files

        def process_json_file_fav(json_file_path, var_file_path):
            """
            处理单个JSON文件，提取包名信息
            """
            try:
                # 从VAR文件路径提取包名
                var_filename = os.path.basename(var_file_path)
                package_name = os.path.splitext(var_filename)[0]  # 移除.var扩展名
                
                # 从JSON文件路径提取相对路径（相对于Saves目录）
                saves_index = json_file_path.find('Saves')
                if saves_index != -1:
                    relative_json_path = json_file_path[saves_index:]
                else:
                    relative_json_path = json_file_path
                
                # 打印结果
                print(f"  JSON路径: {relative_json_path}")
                print(f"  包名: {package_name}")
                print(f"  完整信息: {package_name}\\{relative_json_path}")
                print("  " + "-" * 50)
                
                # 处理路径
                d = relative_json_path.split("\\", -1)
                res = ""
                for i in d[0:-1]:
                    res += i + "\\"
                
                # 创建目录和.fav文件
                target_dir = os.path.join(self.output_base_dir, 'AddonPackagesFilePrefs', package_name, res)
                os.makedirs(target_dir, exist_ok=True)
                
                file_path = os.path.join(target_dir, relative_json_path.split("\\", -1)[-1] + ".fav")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
            except Exception as e:
                print(f"处理JSON文件 {json_file_path} 时出错: {e}")
                raise

        def parse_dependencies(dep_str):
            """解析依赖字符串"""
            if pd.isna(dep_str) or not dep_str:
                return []
            
            dependencies = []
            deps = re.split(r'[,;]+', str(dep_str))
            
            for dep in deps:
                dep = dep.strip()
                if dep:
                    parts = dep.split('.')
                    if len(parts) >= 3:
                        dependencies.append({
                            'author': parts[0],
                            'package_name': parts[1],
                            'version': parts[2]
                        })
            
            return dependencies

        def process_dependencies_recursively(dependencies, processed_deps=None):
            """递归处理依赖项"""
            if processed_deps is None:
                processed_deps = set()
            
            for dep in dependencies:
                if dep['version'].lower() == 'latest':
                    # 查询最新版本
                    latest_mask = (var_packages['author'] == dep['author']) & \
                                 (var_packages['package_name'] == dep['package_name'])
                    latest_versions = var_packages[latest_mask]
                    
                    if not latest_versions.empty:
                        # 假设版本号是数字或可以排序的字符串
                        # 这里需要根据实际的版本号格式进行调整
                        latest_row = latest_versions.iloc[0]  # 可能需要更复杂的版本比较逻辑
                        actual_version = latest_row['version']
                        filename = latest_row['filename']  # 直接从行中获取filename
                        
                        # 创建依赖的唯一标识（使用实际版本号）
                        dep_id = f"{dep['author']}.{dep['package_name']}.{actual_version}"
                        
                        # 如果已经处理过，跳过
                        if dep_id in processed_deps:
                            continue
                        
                        # 使用查询到的filename
                        if filename:
                            # 创建符号链接
                            dep_file = os.path.join(self.var_scan_dir, filename)
                            if create_link(dep_file):
                                processed_deps.add(dep_id)
                                
                                # 获取依赖的依赖
                                dep_dependencies = parse_dependencies(latest_row.get('dependencies'))
                                if dep_dependencies:
                                    print(f"  处理 {dep_id} 的依赖项:")
                                    process_dependencies_recursively(dep_dependencies, processed_deps)

                        else:
                            print(f"⚠ 无法找到依赖-1: {dep_id}")
                    else:
                        empty_dep.append(f"{dep['author']}.{dep['package_name']}.latest")
                        print(f"⚠ 无法找到最新版本的依赖-2: {dep['author']}.{dep['package_name']}.latest")
                        continue
                else:
                    # 创建依赖的唯一标识
                    dep_id = f"{dep['author']}.{dep['package_name']}.{dep['version']}"
                    
                    # 如果已经处理过，跳过
                    if dep_id in processed_deps:
                        continue
                    
                    # 查找依赖文件
                    filename = find_file(dep['author'], dep['package_name'], dep['version'])
                    if filename:
                        # 创建符号链接
                        dep_file = os.path.join(self.var_scan_dir, filename)
                        if create_link(dep_file):
                            processed_deps.add(dep_id)
                            
                            # 获取依赖的依赖
                            dep_mask = (var_packages['author'] == dep['author']) & \
                                      (var_packages['package_name'] == dep['package_name']) & \
                                      (var_packages['version'] == dep['version'])
                            
                            dep_row = var_packages[dep_mask]
                            if not dep_row.empty:
                                dep_dependencies = parse_dependencies(dep_row.iloc[0].get('dependencies'))
                                if dep_dependencies:
                                    print(f"  处理 {dep_id} 的依赖项:")
                                    process_dependencies_recursively(dep_dependencies, processed_deps)
                    else:
                        empty_dep.append(dep_id)
                        print(f"⚠ 无法找到依赖-3: {dep_id}")

        def get_all_dependencies_on_json(saves_directory):
            res = []
            pattern = r':.*"(.*):'
            for root, dirs, files in os.walk(saves_directory):
                for file in files:
                    # 检查文件是否是JSON文件
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            # 读取JSON文件
                            with open(file_path, 'r', encoding='utf-8') as f:
                                match = re.compile(pattern).findall(f.read())
                                for j in match:
                                    if "." in j:
                                        parts = j.split('.')
                                        if len(parts) >= 3:    
                                            tmp_data = {
                                            'author': parts[0],
                                            'package_name': parts[1],
                                            'version': parts[2]
                                            }
                                            res.append(tmp_data)
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON解析错误: {file_path} - {e}")
            return res
                # 查找所有目录下的json 获取额外的依赖,但是不更新csv。

        # 扫描预设和场景目录,获取预设依赖
        def get_preset_deps():
            # 预设目录列表
            self.preset_dirs = [
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Clothing"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Hair"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Plugins"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Appearance"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Skin"),
                os.path.join(os.getcwd(), self.output_base_dir, "Saves", "scene")
            ]
            # 排除选项
            exclude_dirs_preset = ["原始合并", "原始单件", "vap预设","预设直提","json提取"]
            # 搜寻vap文件
            vap_path_lst = []
            for preset_dir in self.preset_dirs:
                # 检查目录是否存在
                if not os.path.exists(preset_dir):
                    print(f"目录不存在: {preset_dir}")
                    continue
                # print(f"正在搜索目录: {preset_dir}")
                
                # 遍历目录树
                for root, dirs, files in os.walk(preset_dir):
                    # 过滤掉需要排除的目录
                    dirs[:] = [d for d in dirs if d not in exclude_dirs_preset]
                    
                    # 筛选VAP文件
                    for file in files:
                        if file.lower().endswith('.vap') or file.lower().endswith('.json'):
                            file_path = os.path.join(root, file)
                            vap_path_lst.append(file_path)
            # print(vap_path_lst)

            # 读取vap文件找依赖
            dep_lst = []
            pattern = r'"([^"]*)"'  # 匹配双引号内的任意非双引号字符
            for i in vap_path_lst:
                # print(i)
                try:
                    with open(i, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    with open(i, 'r', encoding='gb18030') as f:
                        content = f.read()
                matches = re.findall(pattern, content)
                # 筛选包含 / 的匹配项
                filtered_matches = [match for match in matches if ':/' in match]
                if filtered_matches:
                    # print(f"\n文件: {file_path}")
                    # print(f"找到 {len(filtered_matches)} 个匹配:")
                    for match in filtered_matches:
                        # 按 :/ 分割，取 [0] 部分
                        parts = match.split(':/')
                        if parts:
                            # print(f"  '{match}' -> 分割后第一个部分: '{parts[0]}'")
                            dep_lst.append(parts[0])
            
            dep_lst = list(set(dep_lst))
            print( dep_lst )

            # 清洗依赖格式
            dep_clean = []
            for k in dep_lst:
                parts = k.split('.')
                if len(parts) >= 3:    
                    tmp_data = {
                    'author': parts[0],
                    'package_name': parts[1],
                    'version': parts[2]
                    }
                    dep_clean.append(tmp_data)

            # print(dep_clean)
            return dep_clean


        # 主逻辑
        if not self.selected_packages:
            QMessageBox.warning(self, "警告", "没有可导出的数据")
            return
        
        # 1 导出"var_packages_selected.csv"
        file_path = "var_packages_selected.csv"
        try:
            with open(file_path, 'w', newline='', encoding='gb18030') as f:
                fieldnames = ['filename', 'author', 'package_name', 'version', 
                             'dependencies', 'tags', 'images_copied', 'processed_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames,extrasaction='ignore') #  # extrasaction='ignore' 会忽略不在fieldnames中的字段
                
                # 筛选选中的包
                res = []
                for i in self.filtered_packages:
                    gg = f"{i['author']}.{i['package_name']}.{i['version']}"
                    if gg in self.selected_packages:
                        res.append(i)
                
                writer.writeheader()
                writer.writerows(res)
            
            # QMessageBox.information(self, "导出成功", f"成功导出 {len(res)} 条记录")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出CSV失败: {str(e)}")
            return



        # 2 读取"var_packages_selected.csv"，并创建符号链接
        var_packages_selected = pd.read_csv("var_packages_selected.csv", encoding="gb18030")
        var_packages = pd.read_csv(self.csv_file, encoding="gb18030")
        target = os.path.join(self.output_base_dir, "AddonPackages", "link-packages")


        # 清空链接目录
        if os.path.exists(target):
            shutil.rmtree(target)
        os.makedirs(target)

        created = set()
        processed_deps = set()  # 记录已处理的依赖

        # 清空喜爱目录
        target_dir_1 = os.path.join(self.output_base_dir, 'AddonPackagesFilePrefs')
        # 尝试删除目录
        try:
            shutil.rmtree(target_dir_1)
        except FileNotFoundError:
            # 创建目录
            os.makedirs(target_dir_1, exist_ok=True)
        
        # 遍历var_packages_selected.csv
        for _, row in var_packages_selected.iterrows():
            print(f"\n处理主包: {row['author']}.{row['package_name']}.{row['version']}")
            
            # 包文件目录
            main_file = os.path.join(self.var_scan_dir, row['filename'])

            if create_link(main_file):
                # 处理主包的依赖（递归）
                dependencies = parse_dependencies(row.get('dependencies'))
                # 增加搜索准确度，大大增加时间
                if self.include_json_deps:
                    extra_dependencies = get_all_dependencies_on_json(os.path.join(self.unzip_base_dir, row['filename'])[:-4])
                    print(f"基本包数量:{len(dependencies)},从json扫出的包数量:{len(extra_dependencies)}")
                    dependencies.extend(extra_dependencies)
                # print(dependencies)
                # 去重
                unique_deps = [dict(t) for t in {tuple(sorted(d.items())) for d in dependencies}]
                print(f"合并后的包数量:{len(unique_deps)}")
                # 添加可操作事件
                if dependencies:
                    print("  处理依赖项:")
                    process_dependencies_recursively(dependencies, processed_deps)
            
            # 处理JSON文件
            try:
                main_file = os.path.join(self.unzip_base_dir, row['filename'])
                saves_path = os.path.join(main_file.replace(".var", ""), 'Saves')
                json_files = find_json_files_in_saves(saves_path)
                # 处理找到的JSON文件
                for json_file in json_files:
                    process_json_file_fav(json_file, main_file)
            except Exception as e:
                print(f"处理JSON文件时出错: {e}")
        
        print(f"\n创建了 {len(created)} 个符号链接")
        print("已经将所有包及其依赖添加进喜爱目录")

        # 将预设的依赖也添加进来
        process_dependencies_recursively(get_preset_deps(), processed_deps)


        print("\n\n\n\n")
        empty_dep = set(empty_dep)
        for i in empty_dep:
            print("无法找到的依赖： " ,i)
        QMessageBox.information(self, "全部处理完成！", f"全部处理完成！")

        """清除所有选择"""
        self.selected_packages.clear()
        self.update_ui_for_selection()  # 更新UI状态
        self.filter_and_display()

    def jump_to_page(self):
        """跳转到指定页面"""
        target_page = self.page_input.value()
        
        if not self.filtered_packages:
            return
        
        # 计算总页数
        total_packages = len(self.filtered_packages)
        total_pages = max(1, (total_packages + self.packages_per_page - 1) // self.packages_per_page)
        
        # 验证页码是否有效
        if target_page < 1:
            target_page = 1
        elif target_page > total_pages:
            target_page = total_pages
        
        if target_page == self.current_page:
            return  # 已经是当前页，不需要跳转
        
        # 更新当前页
        self.current_page = target_page
        self.filter_and_display()
        
        # 滚动到顶部
        self.scroll_area.verticalScrollBar().setValue(0)
        
        # 添加一个简单的动画效果
        self.animate_jump()

    def animate_jump(self):
        """跳转动画效果"""
        # 创建一个简单的闪烁效果
        original_style = self.page_input.styleSheet()
        self.page_input.setStyleSheet("""
            QSpinBox {
                padding: 4px;
                border: 2px solid #28a745;
                border-radius: 3px;
                background-color: #f0fff0;
            }
        """)
        
        # 使用QTimer恢复原始样式
        QTimer.singleShot(300, lambda: self.page_input.setStyleSheet(original_style))
        
        # 状态栏提示
        total_packages = len(self.filtered_packages)
        total_pages = max(1, (total_packages + self.packages_per_page - 1) // self.packages_per_page)
        self.statusBar().showMessage(f'已跳转到第 {self.current_page} 页 (共 {total_pages} 页)', 2000)
    







    def toggle_sort_order(self):
        """切换排序顺序"""
        if self.sort_order == Qt.AscendingOrder:
            self.sort_order = Qt.DescendingOrder
            self.sort_order_btn.setText("降序")
            self.sort_order_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
        else:
            self.sort_order = Qt.AscendingOrder
            self.sort_order_btn.setText("升序")
            self.sort_order_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
            """)
        
        self.filter_and_display()

    def sort_packages(self, packages):
        """对包进行排序"""
        if not packages:
            return packages
        
        # 随机排序
        if self.is_random_sort:
            return self.random_sort_packages(packages)
        
        # 根据排序条件选择排序键
        if self.sort_by == "package_name":
            key_func = lambda x: x.get('package_name', '').lower()
        elif self.sort_by == "author":
            key_func = lambda x: x.get('author', '').lower()
        elif self.sort_by == "version":
            key_func = lambda x: self.parse_version(x.get('version', '0'))
        elif self.sort_by == "images_copied":
            key_func = lambda x: self.parse_number(x.get('images_copied', '0'))
        elif self.sort_by == "dependencies":
            key_func = lambda x: self.get_dependency_count_int(x.get('dependencies', ''))
        # 新增：被引用次数排序
        elif self.sort_by == "reference_count":
            print(1)
            key_func = lambda x: self.get_dependency_reference_count(
                x.get('author', ''), 
                x.get('package_name', '')
            )
        elif self.sort_by == "score":  # 新增：按得分排序
            # 确保每个包都有得分
            for package in packages:
                if 'score' not in package:
                    self.calculate_package_score(package)
            key_func = lambda x: x.get('score', 0)
        elif self.sort_by == "creation_date":
            key_func = lambda x: self.parse_creation_date(self.get_package_creation_date(x))
        elif self.sort_by == "processed_time":  # 新增：处理时间排序
            key_func = lambda x: self.parse_processed_time(x.get('processed_time', ''))
        else:
            key_func = lambda x: x.get('package_name', '').lower()
        
        # 进行排序
        try:
            sorted_packages = sorted(packages, key=key_func, 
                                    reverse=(self.sort_order == Qt.DescendingOrder))
            return sorted_packages
        except Exception as e:
            print(f"排序失败: {e}")
            return packages
    
    def random_sort_packages(self, packages):
        """随机排序包"""
        if not packages:
            return packages
        
        import random
        
        # 使用设定的随机种子
        if self.random_seed is not None:
            random.seed(self.random_seed)
        
        # 创建可变的副本
        packages_copy = packages.copy()
        
        # 随机打乱顺序
        random.shuffle(packages_copy)
        
        return packages_copy

    def parse_version(self, version_str):
        """解析版本号，支持如 1.2.3 这样的格式"""
        try:
            # 移除可能的非数字字符，只保留数字和点
            version_clean = ''.join(c for c in version_str if c.isdigit() or c == '.')
            if not version_clean:
                return (0, 0, 0)
            
            # 分割版本号
            parts = version_clean.split('.')
            # 确保至少有3部分，不足的补0
            while len(parts) < 3:
                parts.append('0')
            
            # 转换为整数元组
            return tuple(int(part) for part in parts[:3])
        except:
            return (0, 0, 0)

    def parse_number(self, num_str):
        """解析数字字符串"""
        try:
            # 移除非数字字符
            num_clean = ''.join(c for c in str(num_str) if c.isdigit())
            return int(num_clean) if num_clean else 0
        except:
            return 0

    def get_dependency_count_int(self, dep_str):
        """获取依赖数量（整数形式）"""
        if not dep_str:
            return 0
        
        if dep_str in ["无依赖", "无meta.json", "meta.json解析错误"]:
            return 0
        
        deps = [d.strip() for d in dep_str.split(',') if d.strip()]
        return len(deps)

    

    def locate_selected_package(self):
        """一键定位选中的包目录"""
        if not self.selected_packages:
            QMessageBox.warning(self, "警告", "没有选中的包")
            return
        
        # 检查是否只选中了一个包
        if len(self.selected_packages) > 1:
            QMessageBox.warning(self, "警告", "只能选择一个包进行定位")
            return
        
        # 获取选中的包标识符
        package_identifier = next(iter(self.selected_packages))  # 获取第一个（也是唯一一个）选中的包
        print(f"定位包: {package_identifier}")
        
        # 构建目标目录路径（注意：self.selected_packages 是字符串，不是列表）
        # 格式如: author.package_name.version
        target_dir = os.path.join(self.unzip_base_dir, package_identifier)
        
        # 检查目录是否存在
        if not os.path.exists(target_dir):
            QMessageBox.warning(self, "目录不存在", 
                               f"目标目录不存在:\n{target_dir}\n\n"
                               f"请检查:\n"
                               f"1. 目录路径是否正确\n"
                               f"2. VAR文件是否已解压到该目录")
            return
        
        # 使用系统的文件资源管理器打开目录
        try:
            # Windows系统
            if sys.platform == 'win32':
                # 使用explorer打开目录
                os.startfile(target_dir)
                
                # 或者使用subprocess（更可靠的方式）
                # import subprocess
                # subprocess.run(['explorer', target_dir])
            
            # macOS系统
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(['open', target_dir])
            
            # Linux系统
            else:
                import subprocess
                subprocess.run(['xdg-open', target_dir])
            
            print(f"已打开目录: {target_dir}")
            
            # 在状态栏显示信息
            self.statusBar().showMessage(f"已定位到: {os.path.basename(target_dir)}", 5000)
            
        except Exception as e:
            QMessageBox.critical(self, "打开失败", 
                               f"无法打开目录:\n{target_dir}\n\n错误: {str(e)}")
    
    def update_ui_for_selection(self):
        """根据选择状态更新UI"""
        count = len(self.selected_packages)
        
        # 更新选中数量显示
        self.update_selected_count()
        
        # 更新定位按钮状态（只能选中一个包时才可用）
        if hasattr(self, 'locate_btn'):
            self.locate_btn.setEnabled(count == 1)
        
        # 更新查看选中包按钮状态
        self.view_selected_btn.setEnabled(count > 0)
        
        # 更新批量操作按钮状态
        self.batch_add_tag_btn.setEnabled(count > 0)
        self.batch_remove_tag_btn.setEnabled(count > 0)
        
        # 添加工具提示
        if count == 1:
            if hasattr(self, 'locate_btn'):
                self.locate_btn.setToolTip("定位到选中的包目录")
            self.view_selected_btn.setToolTip("查看选中的1个包")
            self.batch_add_tag_btn.setToolTip("为选中的1个包批量添加标签")
            self.batch_remove_tag_btn.setToolTip("从选中的1个包批量删除标签")
        elif count > 1:
            if hasattr(self, 'locate_btn'):
                self.locate_btn.setToolTip("只能选择一个包进行定位")
            self.view_selected_btn.setToolTip(f"查看选中的{count}个包")
            self.batch_add_tag_btn.setToolTip(f"为选中的{count}个包批量添加标签")
            self.batch_remove_tag_btn.setToolTip(f"从选中的{count}个包批量删除标签")
        else:
            if hasattr(self, 'locate_btn'):
                self.locate_btn.setToolTip("请先选择一个包")
            self.view_selected_btn.setToolTip("没有选中的包")
            self.batch_add_tag_btn.setToolTip("请先选择要操作的包")
            self.batch_remove_tag_btn.setToolTip("请先选择要操作的包")
        
        # 如果当前在选中包模式，但选中包数量为0，自动切换回全部模式
        if self.view_mode == "selected" and count == 0:
            self.view_all_packages()

    def view_selected_packages(self):
        """查看选中包模式 - 只显示选中的包"""
        if not self.selected_packages:
            QMessageBox.information(self, "提示", "没有选中的包")
            return
        
        self.view_mode = "selected"
        self.update_view_buttons()
        self.filter_and_display()
        
        # 更新状态栏
        self.statusBar().showMessage(f"显示选中包模式: {len(self.selected_packages)} 个包", 3000)

    def view_all_packages(self):
        """查看全部包模式"""
        self.view_mode = "all"
        self.update_view_buttons()
        self.filter_and_display()
        
        # 更新状态栏
        self.statusBar().showMessage("显示全部包", 3000)

    def update_view_buttons(self):
        """更新视图按钮状态"""
        if self.view_mode == "selected":
            self.view_selected_btn.setStyleSheet("""
                QPushButton {
                    background-color: #20c997;
                    color: white;
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 4px;
                    border: 2px solid #198754;
                }
                QPushButton:hover {
                    background-color: #1ba87e;
                }
            """)
            self.view_all_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
        else:  # all模式
            self.view_all_btn.setStyleSheet("""
                QPushButton {
                    background-color: #20c997;
                    color: white;
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 4px;
                    border: 2px solid #198754;
                }
                QPushButton:hover {
                    background-color: #1ba87e;
                }
            """)
            self.view_selected_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6610f2;
                    color: white;
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #590bd1;
                }
            """)
    def extract_selected_var_info(self):
        """提取选中VAR包的信息"""
        if not self.selected_packages:
            QMessageBox.warning(self, "警告", "没有选中的包")
            return
        print(f"开始提取 {len(self.selected_packages)} 个选中的VAR包信息...")
        # 临时：打印选中的包信息
        def gen_base_clothing_presets_single(package_identifier):
            # 1 基本服装预设自动生成 (多合一)
            iui = 0
            pkg_name = package_identifier
            path = os.path.join(self.unzip_base_dir,pkg_name,"Custom","Clothing")

            # 寻找vaj
            vaj_files = []
            for root, dirs, files in os.walk(path):
                vaj_files.extend(os.path.join(root, f) for f in files if f.endswith('.vam'))
            # 生成vaj预设
            init_hair = { 
               "setUnlistedParamsToDefault" : "true", 
               "storables" : [ 
                  { 
                     "id" : "geometry", 
                     "clothing" : [ 
                     ]
                  }
               ]
            }
            # print(vaj_files) # if vaj_files = []
            for j in vaj_files: 
                vaj_base_name = "Custom"+j.split("Custom")[1]
                # print(vaj_base_name)
                strs_ = { 
                   "id" : f"{pkg_name}:\\{vaj_base_name}".replace("\\","/"), 
                   "internalId" : f"{pkg_name} {j.split("\\")[-1].replace(".vam","")}", 
                   "enabled" : "true"
                }
                init_hair["storables"][0]["clothing"].append(strs_)
                with open(j.replace('.vam',".vaj"), 'r', encoding='utf-8') as garment_file:
                    storable_data = json.load(garment_file)["storables"]
                # print(storable_data)
                try:
                    for storable_item in storable_data:
                        # 贴图属性列表
                        texture_properties = [
                            "customTexture_MainTex", "customTexture_SpecTex", 
                            "customTexture_GlossTex", "customTexture_AlphaTex", 
                            "customTexture_BumpMap", "customTexture_DecalTex", 
                            "simTexture"
                        ]
                        for texture_prop in texture_properties:
                            if (texture_prop in storable_item) and (storable_item[texture_prop] != ""):
                                # storable_item中的贴图路径[texture_properties] 全部换完
                                original_texture = storable_item[texture_prop]
                                new_base_path = pkg_name + ":\\" + vaj_base_name
                                path_parts = new_base_path.split("\\", -1)[0:-1]
                                new_texture_path = '\\'.join( part for part in path_parts) + "\\" + original_texture
                                new_texture_path = new_texture_path.replace("./","").replace(" ./","").replace("/","\\").replace("\\","/")
                                print(new_texture_path)                                                    
                                storable_item[texture_prop] = new_texture_path # 轮奸替换
                                # 添加到结果列表
                    init_hair["storables"].append(storable_item)
                    # print(storable_item)
                except Exception as e: 
                    print(str(e)) # 可能是缺少依赖    
            if init_hair!= "" and init_hair!={ # 过滤掉空文件
               "setUnlistedParamsToDefault" : "true", 
               "storables" : [ 
                  { 
                     "id" : "geometry", 
                     "clothing" : [ 
                     ]
                  }
               ]
            }:
                target_dir = os.path.join(self.output_base_dir,"Custom","Atom","Person","Clothing","原始合并",pkg_name)
                os.makedirs(target_dir, exist_ok=True)
                # 构建文件路径
                file_path = os.path.join(target_dir, f"Preset_{pkg_name}_NO_{str(iui)}.vap")
                with open(file_path, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                    r = json.dumps(init_hair, indent=2, separators=(',', ':'), ensure_ascii=False) 
                    f.write(str(r)) 
                iui += 1

        def gen_base_clothing_presets_multi(package_identifier):
            # 1 基本服装预设自动生成 (不合并)
            iui = 0
            pkg_name = package_identifier
            path = os.path.join(self.unzip_base_dir,pkg_name,"Custom","Clothing")

            # 寻找vaj
            vaj_files = []
            for root, dirs, files in os.walk(path):
                vaj_files.extend(os.path.join(root, f) for f in files if f.endswith('.vam'))

            for j in vaj_files:
                # 生成vaj预设
                init_hair = { 
                   "setUnlistedParamsToDefault" : "true", 
                   "storables" : [ 
                      { 
                         "id" : "geometry", 
                         "clothing" : [ 
                         ]
                      }
                   ]
                }
                vaj_base_name = "Custom"+j.split("Custom")[1]
                strs_ = { 
                   "id" : f"{pkg_name}:\\{vaj_base_name}".replace("\\","/"), 
                   "internalId" : f"{pkg_name} {j.split("\\")[-1].replace(".vam","")}", 
                   "enabled" : "true"
                }
                init_hair["storables"][0]["clothing"].append(strs_)
                with open(j.replace('.vam',".vaj"), 'r', encoding='utf-8') as garment_file:
                    storable_data = json.load(garment_file)["storables"]
                # print(storable_data)
                try:
                    for storable_item in storable_data:
                        # 贴图属性列表
                        texture_properties = [
                            "customTexture_MainTex", "customTexture_SpecTex", 
                            "customTexture_GlossTex", "customTexture_AlphaTex", 
                            "customTexture_BumpMap", "customTexture_DecalTex", 
                            "simTexture"
                        ]
                        for texture_prop in texture_properties:
                            if (texture_prop in storable_item) and (storable_item[texture_prop] != ""):
                                # storable_item中的贴图路径[texture_properties] 全部换完
                                original_texture = storable_item[texture_prop]
                                new_base_path = pkg_name + ":\\" + vaj_base_name
                                path_parts = new_base_path.split("\\", -1)[0:-1]
                                new_texture_path = '\\'.join( part for part in path_parts) + "\\" + original_texture
                                new_texture_path = new_texture_path.replace("./","").replace(" ./","").replace("/","\\").replace("\\","/")
                                print(new_texture_path)                                                    
                                storable_item[texture_prop] = new_texture_path # 轮奸替换
                                # 添加到结果列表
                    init_hair["storables"].append(storable_item)
                    # print(storable_item)
                except Exception as e: 
                    print(str(e)) # 可能是缺少依赖    
                # pprint(init_hair) 
                if init_hair!= "" and init_hair!={ # 过滤掉空文件
                   "setUnlistedParamsToDefault" : "true", 
                   "storables" : [ 
                      { 
                         "id" : "geometry", 
                         "clothing" : [ 
                         ]
                      }
                   ]
                }:
                    target_dir = os.path.join(self.output_base_dir,"Custom","Atom","Person","Clothing","原始单件",pkg_name)
                    os.makedirs(target_dir, exist_ok=True)
                    # 构建文件路径
                    file_path = os.path.join(target_dir, f"Preset_{pkg_name}_NO_{str(iui)}.vap")
                    with open(file_path, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                        r = json.dumps(init_hair, indent=2, separators=(',', ':'), ensure_ascii=False) 
                        f.write(str(r)) 
                    iui += 1

        def gen_clothing_vaps_single(package_identifier):
            # 下面的代码是照抄的,每个目录只有一个vaj文件和若干个vap,一个每个vap文件就是vaj文件改了改参数。搬运vap时,直接掏空vaj即可。
            iui = 0
            pkg_name = package_identifier
            path = os.path.join(self.unzip_base_dir,pkg_name,"Custom","Clothing")

            # 寻找vaj
            vaj_files = []
            for root, dirs, files in os.walk(path):
                vaj_files.extend(os.path.join(root, f) for f in files if f.endswith('.vam'))
            
            # # if '衣服' in tags才会触发这个函数
            # if vaj_files == []: # 此时为空，只有一种可能：该包只有vap的服装,无vaj的服装。其实vap和vaj文件json格式完全等价。严格意义上，vap是某个vaj的皮肤，比如vaj换10多个颜色，每个颜色一个vap。
            #     for root, dirs, files in os.walk(path):
            #         vaj_files.extend(os.path.join(root, f.replace(".vap",".vam")) for f in files if f.endswith('.vap')) # replace是为了不改后面的代码
            if vaj_files == []: 
                print('该 服装/发型 包没有任何的vam和vaj文件。最大的可能性是该包只有vap文件。由于包没有任何的vaj文件，所以服装管理器中找不到该包，最大的可能性是：该包是某个外部服装包的vap皮肤扩展，该扩展可能有几百个vap。参考an3k.Wardrobe_Clothing_Addon_1.1')

            for j in vaj_files:                
                # 开始一一生成预设
                parts = j.split("\\")[:-1]  # 去掉最后1级,寻找vam的本级目录,定位该目录下的vap
                vap_basepath = "\\".join(parts)
                vap_files = [f for f in os.listdir(vap_basepath) if f.endswith('.vap')]
                for vapfile in vap_files:
                    init_hair = { 
                       "setUnlistedParamsToDefault" : "true", 
                       "storables" : [ 
                          { 
                             "id" : "geometry", 
                             "clothing" : [ 
                             ]
                          }
                       ]
                    }
                    vaj_base_name = "Custom"+j.split("Custom")[1]
                    strs_ = { 
                       "id" : f"{pkg_name}:\\{vaj_base_name}".replace("\\","/"), 
                       "internalId" : f"{pkg_name} {j.split("\\")[-1].replace(".vam","")}", 
                       "enabled" : "true"
                    }
                    init_hair["storables"][0]["clothing"].append(strs_)

                    with open(os.path.join(vap_basepath,vapfile) , 'r', encoding='utf-8') as garment_file:
                        storable_data = json.load(garment_file)["storables"]
                    try:
                        for storable_item in storable_data:
                            # 贴图属性列表
                            texture_properties = [
                                "customTexture_MainTex", "customTexture_SpecTex", 
                                "customTexture_GlossTex", "customTexture_AlphaTex", 
                                "customTexture_BumpMap", "customTexture_DecalTex", 
                                "simTexture"
                            ]
                            for texture_prop in texture_properties:
                                if (texture_prop in storable_item) and (storable_item[texture_prop] != ""):
                                    # storable_item中的贴图路径[texture_properties] 全部换完
                                    original_texture = storable_item[texture_prop]
                                    new_base_path = pkg_name + ":\\" + vaj_base_name
                                    path_parts = new_base_path.split("\\", -1)[0:-1]
                                    new_texture_path = '\\'.join( part for part in path_parts) + "\\" + original_texture
                                    new_texture_path = new_texture_path.replace("./","").replace(" ./","").replace("/","\\").replace("\\","/")
                                    # print(new_texture_path)                                                    
                                    storable_item[texture_prop] = new_texture_path # 轮奸替换
                                    # 添加到结果列表
                            init_hair["storables"].append(storable_item)
                    except Exception as e: 
                        print(str(e)) # 可能是缺少依赖 

                    if init_hair!= "" and init_hair!={ # 过滤掉空文件
                       "setUnlistedParamsToDefault" : "true", 
                       "storables" : [ 
                          { 
                             "id" : "geometry", 
                             "clothing" : [ 
                             ]
                          }
                       ]
                    }:
                        target_dir = os.path.join(self.output_base_dir,"Custom","Atom","Person","Clothing","vap预设",pkg_name)
                        os.makedirs(target_dir, exist_ok=True)
                        # 构建文件路径
                        file_path = os.path.join(target_dir, f"Preset_{pkg_name}_NO_{str(iui)}.vap")
                        with open(file_path, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                            r = json.dumps(init_hair, indent=2, separators=(',', ':'), ensure_ascii=False) 
                            f.write(str(r)) 
                        iui += 1
        
        
        def gen_base_hair_presets_single(package_identifier):
            # 1 基本头发预设自动生成 (多合一)
            iui = 0
            pkg_name = package_identifier
            path = os.path.join(self.unzip_base_dir,pkg_name,"Custom","Hair")

            # 寻找vaj
            vaj_files = []
            for root, dirs, files in os.walk(path):
                vaj_files.extend(os.path.join(root, f) for f in files if f.endswith('.vam'))
            # 生成vaj预设
            init_hair = { 
               "setUnlistedParamsToDefault" : "true", 
               "storables" : [ 
                  { 
                     "id" : "geometry", 
                     "hair" : [ 
                     ]
                  }
               ]
            }
            for j in vaj_files:
                vaj_base_name = "Custom"+j.split("Custom")[1]
                strs_ = { 
                   "id" : f"{pkg_name}:\\{vaj_base_name}".replace("\\","/"), 
                   "internalId" : f"{pkg_name} {j.split("\\")[-1].replace(".vam","")}", 
                   "enabled" : "true"
                }
                init_hair["storables"][0]["hair"].append(strs_)
                with open(j.replace('.vam',".vaj"), 'r', encoding='utf-8') as garment_file:
                    storable_data = json.load(garment_file)["storables"]
                # print(storable_data)
                try:
                    for storable_item in storable_data:
                        # 贴图属性列表
                        texture_properties = [
                            "customTexture_MainTex", "customTexture_SpecTex", 
                            "customTexture_GlossTex", "customTexture_AlphaTex", 
                            "customTexture_BumpMap", "customTexture_DecalTex", 
                            "simTexture"
                        ]
                        for texture_prop in texture_properties:
                            if (texture_prop in storable_item) and (storable_item[texture_prop] != ""):
                                # storable_item中的贴图路径[texture_properties] 全部换完
                                original_texture = storable_item[texture_prop]
                                new_base_path = pkg_name + ":\\" + vaj_base_name
                                path_parts = new_base_path.split("\\", -1)[0:-1]
                                new_texture_path = '\\'.join( part for part in path_parts) + "\\" + original_texture
                                new_texture_path = new_texture_path.replace("./","").replace(" ./","").replace("/","\\").replace("\\","/")
                                print(new_texture_path)                                                    
                                storable_item[texture_prop] = new_texture_path # 轮奸替换
                                # 添加到结果列表
                    init_hair["storables"].append(storable_item)
                    # print(storable_item)
                except Exception as e: 
                    print(str(e)) # 可能是缺少依赖    
            # pprint(init_hair) 
            if init_hair!= "" and init_hair!={ # 过滤掉空文件
               "setUnlistedParamsToDefault" : "true", 
               "storables" : [ 
                  { 
                     "id" : "geometry", 
                     "hair" : [ 
                     ]
                  }
               ]
            }:
                target_dir = os.path.join(self.output_base_dir,"Custom","Atom","Person","Hair","原始合并",pkg_name)
                os.makedirs(target_dir, exist_ok=True)
                # 构建文件路径
                file_path = os.path.join(target_dir, f"Preset_{pkg_name}_NO_{str(iui)}.vap")
                with open(file_path, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                    r = json.dumps(init_hair, indent=2, separators=(',', ':'), ensure_ascii=False) 
                    f.write(str(r)) 
                iui += 1
        
        def gen_base_hair_presets_multi(package_identifier):
            # 1 基本头发预设自动生成 (不合并)
            iui = 0
            pkg_name = package_identifier
            path = os.path.join(self.unzip_base_dir,pkg_name,"Custom","Hair")

            # 寻找vaj
            vaj_files = []
            for root, dirs, files in os.walk(path):
                vaj_files.extend(os.path.join(root, f) for f in files if f.endswith('.vam'))

            for j in vaj_files:
                # 生成vaj预设
                init_hair = { 
                   "setUnlistedParamsToDefault" : "true", 
                   "storables" : [ 
                      { 
                         "id" : "geometry", 
                         "hair" : [ 
                         ]
                      }
                   ]
                }
                vaj_base_name = "Custom"+j.split("Custom")[1]
                strs_ = { 
                   "id" : f"{pkg_name}:\\{vaj_base_name}".replace("\\","/"), 
                   "internalId" : f"{pkg_name} {j.split("\\")[-1].replace(".vam","")}", 
                   "enabled" : "true"
                }
                init_hair["storables"][0]["hair"].append(strs_)
                with open(j.replace('.vam',".vaj"), 'r', encoding='utf-8') as garment_file:
                    storable_data = json.load(garment_file)["storables"]
                # print(storable_data)
                try:
                    for storable_item in storable_data:
                        # 贴图属性列表
                        texture_properties = [
                            "customTexture_MainTex", "customTexture_SpecTex", 
                            "customTexture_GlossTex", "customTexture_AlphaTex", 
                            "customTexture_BumpMap", "customTexture_DecalTex", 
                            "simTexture"
                        ]
                        for texture_prop in texture_properties:
                            if (texture_prop in storable_item) and (storable_item[texture_prop] != ""):
                                # storable_item中的贴图路径[texture_properties] 全部换完
                                original_texture = storable_item[texture_prop]
                                new_base_path = pkg_name + ":\\" + vaj_base_name
                                path_parts = new_base_path.split("\\", -1)[0:-1]
                                new_texture_path = '\\'.join( part for part in path_parts) + "\\" + original_texture
                                new_texture_path = new_texture_path.replace("./","").replace(" ./","").replace("/","\\").replace("\\","/")
                                print(new_texture_path)                                                    
                                storable_item[texture_prop] = new_texture_path # 轮奸替换
                                # 添加到结果列表
                    init_hair["storables"].append(storable_item)
                    # print(storable_item)
                except Exception as e: 
                    print(str(e)) # 可能是缺少依赖    
                # pprint(init_hair) 
                if init_hair!= "" and init_hair!={ # 过滤掉空文件
                   "setUnlistedParamsToDefault" : "true", 
                   "storables" : [ 
                      { 
                         "id" : "geometry", 
                         "hair" : [ 
                         ]
                      }
                   ]
                }:
                    target_dir = os.path.join(self.output_base_dir,"Custom","Atom","Person","Hair","原始单件",pkg_name)
                    os.makedirs(target_dir, exist_ok=True)
                    # 构建文件路径
                    file_path = os.path.join(target_dir, f"Preset_{pkg_name}_NO_{str(iui)}.vap")
                    with open(file_path, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                        r = json.dumps(init_hair, indent=2, separators=(',', ':'), ensure_ascii=False) 
                        f.write(str(r)) 
                    iui += 1
        
        def gen_hair_vaps_single(package_identifier):
            # 下面的代码是照抄的,每个目录只有一个vaj文件和若干个vap,一个每个vap文件就是vaj文件改了改参数。搬运vap时,直接掏空vaj即可。
            iui = 0
            pkg_name = package_identifier
            path = os.path.join(self.unzip_base_dir,pkg_name,"Custom","Hair")

            # 寻找vaj
            vaj_files = []
            for root, dirs, files in os.walk(path):
                vaj_files.extend(os.path.join(root, f) for f in files if f.endswith('.vam'))

            for j in vaj_files:                
                # 开始一一生成预设
                parts = j.split("\\")[:-1]  # 去掉最后1级,寻找vam的本级目录,定位该目录下的vap
                vap_basepath = "\\".join(parts)
                vap_files = [f for f in os.listdir(vap_basepath) if f.endswith('.vap')]
                for vapfile in vap_files:
                    init_hair = { 
                       "setUnlistedParamsToDefault" : "true", 
                       "storables" : [ 
                          { 
                             "id" : "geometry", 
                             "hair" : [ 
                             ]
                          }
                       ]
                    }
                    vaj_base_name = "Custom"+j.split("Custom")[1]
                    strs_ = { 
                       "id" : f"{pkg_name}:\\{vaj_base_name}".replace("\\","/"), 
                       "internalId" : f"{pkg_name} {j.split("\\")[-1].replace(".vam","")}", 
                       "enabled" : "true"
                    }
                    init_hair["storables"][0]["hair"].append(strs_)

                    with open(os.path.join(vap_basepath,vapfile) , 'r', encoding='utf-8') as garment_file:
                        storable_data = json.load(garment_file)["storables"]
                    try:
                        for storable_item in storable_data:
                            # 贴图属性列表
                            texture_properties = [
                                "customTexture_MainTex", "customTexture_SpecTex", 
                                "customTexture_GlossTex", "customTexture_AlphaTex", 
                                "customTexture_BumpMap", "customTexture_DecalTex", 
                                "simTexture"
                            ]
                            for texture_prop in texture_properties:
                                if (texture_prop in storable_item) and (storable_item[texture_prop] != ""):
                                    # storable_item中的贴图路径[texture_properties] 全部换完
                                    original_texture = storable_item[texture_prop]
                                    new_base_path = pkg_name + ":\\" + vaj_base_name
                                    path_parts = new_base_path.split("\\", -1)[0:-1]
                                    new_texture_path = '\\'.join( part for part in path_parts) + "\\" + original_texture
                                    new_texture_path = new_texture_path.replace("./","").replace(" ./","").replace("/","\\").replace("\\","/")
                                    # print(new_texture_path)                                                    
                                    storable_item[texture_prop] = new_texture_path # 轮奸替换
                                    # 添加到结果列表
                            init_hair["storables"].append(storable_item)
                    except Exception as e: 
                        print(str(e)) # 可能是缺少依赖 
                    # print(init_hair)
                    if init_hair!= "" and init_hair!={ # 过滤掉空文件
                       "setUnlistedParamsToDefault" : "true", 
                       "storables" : [ 
                          { 
                             "id" : "geometry", 
                             "hair" : [ 
                             ]
                          }
                       ]
                    }:
                        target_dir = os.path.join(self.output_base_dir,"Custom","Atom","Person","Hair","vap预设",pkg_name)
                        os.makedirs(target_dir, exist_ok=True)
                        # 构建文件路径
                        file_path = os.path.join(target_dir, f"Preset_{pkg_name}_NO_{str(iui)}.vap")
                        with open(file_path, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                            r = json.dumps(init_hair, indent=2, separators=(',', ':'), ensure_ascii=False) 
                            f.write(str(r)) 
                        iui += 1

        def copy_Atom_Person(package_identifier):
            pkg_name = package_identifier
            # 定义所有需要复制的目录类型
            dir_types = ["Clothing", "Hair", "Skin", "Pose","Appearance"]

            # 遍历所有目录类型
            for dir_type in dir_types:
                # 源目录
                src_dir = os.path.join(self.unzip_base_dir, pkg_name, "Custom", "Atom", "Person", dir_type)
                # 检查源目录是否存在
                if not os.path.exists(src_dir):
                    # print(f"源目录不存在，跳过: {src_dir}")
                    continue
                # 目标目录
                dst_dir = os.path.join(self.output_base_dir, "Custom", "Atom", "Person", dir_type,"预设直提", pkg_name)

                # 确保目标目录存在
                os.makedirs(dst_dir, exist_ok=True)
                
                try:
                    # 复制整个目录树
                    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                    
                    # 遍历目标目录中的所有文件，查找并替换'SELF:'为package_identifier
                    for root, dirs, files in os.walk(dst_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            
                            # 尝试读取文件内容（只处理文本文件）
                            try:
                                # 先尝试以utf-8编码读取
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                
                                # 使用re替换'SELF:'为package_identifier 。直接复制是不行的
                                if 'SELF:' in content:
                                    new_content = re.sub(r'SELF:', f'{pkg_name}:', content)
                                    
                                    # 如果内容有变化，则写回文件
                                    if new_content != content:
                                        with open(file_path, 'w', encoding='utf-8') as f:
                                            f.write(new_content)
                                        print(f"已替换文件中的SELF:: {file_path}")
                            except UnicodeDecodeError:
                                # 如果不是文本文件，跳过
                                continue
                            except Exception as e:
                                print(f"处理文件 {file_path} 时出错: {e}")
                                continue
                    
                    print(f"成功复制并处理: {dir_type}")
                except Exception as e:
                    print(f"复制 {dir_type} 时出错: {e}")


        for package_identifier in self.selected_packages:
            for ii in self.var_data:
                if ii['filename'].replace(".var","") == package_identifier:
                    tags = [tag.strip() for tag in ii['tags'].split(',')] # 去除空格,join时不小心把空格加进去了

                    print(f"待处理的包: {package_identifier}")
                    print(tags)
                    if '衣服' in tags: # 提取服装
                        gen_base_clothing_presets_single(package_identifier)
                        gen_base_clothing_presets_multi(package_identifier)
                        gen_clothing_vaps_single(package_identifier)
                    if '头发' in tags: # 提取头发
                        gen_base_hair_presets_single(package_identifier)
                        gen_base_hair_presets_multi(package_identifier)
                        gen_hair_vaps_single(package_identifier)
            copy_Atom_Person(package_identifier) # 这个直接拷贝，不行，得把SELF替换成对应的包名后面再说。

        # QMessageBox.critical(self, "处理完成", "处理完成")

    def change_sort_criteria(self, criteria_text):
        """改变排序条件"""
        sort_mapping = {
            "包名": "package_name",
            "作者": "author", 
            "图片数量": "images_copied",
            "依赖数量": "dependencies",
            "版本号": "version",
            "被引用次数": "reference_count",  # 新增
            "得分": "score",  # 新增：按得分排序
            "随机排序": "random",  # 添加随机排序
            "创建日期": "creation_date",  # 添加创建日期
            "处理时间": "processed_time",  # 新增：处理时间
        }
        
        if criteria_text in sort_mapping:
            self.sort_by = sort_mapping[criteria_text]
            
             # 如果是得分排序，默认按降序排列（分数高的在前）
            if self.sort_by == "score":
                if self.sort_order == Qt.AscendingOrder:
                    self.toggle_sort_order()  # 切换到降序

            # 如果是随机排序
            if self.sort_by == "random":
                self.is_random_sort = True
                self.sort_order_btn.setEnabled(False)
                self.sort_order_btn.setText("随机")
                self.random_seed_input.setEnabled(True)
                self.refresh_random_btn.setEnabled(True)
                self.sort_order_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #6610f2;
                        color: white;
                        border: none;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-weight: bold;
                    }
                    QPushButton:disabled {
                        background-color: #6c757d;
                        color: #dee2e6;
                    }
                """)
                
                # 如果没有设置随机种子，生成一个
                if self.random_seed is None:
                    import random
                    self.random_seed = random.randint(0, 999999999)
                    self.random_seed_input.setValue(self.random_seed)
            else:
                self.is_random_sort = False
                self.sort_order_btn.setEnabled(True)
                self.random_seed_input.setEnabled(False)
                self.refresh_random_btn.setEnabled(False)
                
                # 根据排序类型设置合适的排序顺序
                if self.sort_by in ["package_name", "author"]:
                    # 文本类型默认按字母顺序
                    if self.sort_order != Qt.AscendingOrder:
                        self.toggle_sort_order()  # 切回升序
                else:
                    # 数字类型默认按降序（数量多的在前）
                    if self.sort_order == Qt.AscendingOrder:
                        self.toggle_sort_order()  # 切换到降序
            
            self.filter_and_display()

    def change_random_seed(self, seed):
        """改变随机种子"""
        self.random_seed = seed
        if self.is_random_sort:
            self.filter_and_display()
            self.statusBar().showMessage(f"随机种子已更新: {seed}", 2000)
    def refresh_random_sort(self):
        """刷新随机排序 - 生成新的随机种子"""
        import random
        
        # 生成新的随机种子
        new_seed = random.randint(0, 999999999)
        self.random_seed = new_seed
        self.random_seed_input.setValue(new_seed)
        
        # 重新筛选和显示
        self.filter_and_display()
        
        # 显示提示信息
        self.statusBar().showMessage(f"已刷新随机排序，新种子: {new_seed}", 3000)
        
        # 添加一个简单的动画效果
        self.animate_refresh_random()

    def animate_refresh_random(self):
        """刷新随机排序的动画效果"""
        original_style = self.refresh_random_btn.styleSheet()
        
        # 高亮按钮
        self.refresh_random_btn.setStyleSheet("""
            QPushButton {
                background-color: #20c997;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-weight: bold;
                border: 2px solid #198754;
            }
            QPushButton:hover {
                background-color: #1ba87e;
            }
        """)
        
        # 使用QTimer恢复原始样式
        QTimer.singleShot(500, lambda: self.refresh_random_btn.setStyleSheet(original_style))

    def keyPressEvent(self, event):
        """处理键盘按键事件"""
        if event.key() == Qt.Key_Escape:
            current_time = time.time()
            
            # 如果上次按 Escape 的时间存在且在5000毫秒内
            if self.last_escape_time and (current_time - self.last_escape_time) < 5:
                self.close()  # 直接关闭窗口
                return
            else:
                # 第一次按 Escape 或间隔时间较长
                # 执行原来的逻辑：退出全屏
                self.setWindowState(Qt.WindowNoState)
                self.setGeometry(100, 100, int(self.config.get_window_size()[0])-300, int(self.config.get_window_size()[1])-300)
                
                # 记录当前时间
                self.last_escape_time = current_time
        else:
            super().keyPressEvent(event)



    def batch_add_tags(self):
        """批量删除标签 - 显示所有标签，但高亮公共标签"""
        if not self.selected_packages:
            QMessageBox.warning(self, "警告", "没有选中的包")
            return
        
        # 获取所有选中包的公共标签
        common_tags = self.get_common_tags_for_selected_packages()
        
        # 创建批量删除标签对话框（显示所有标签）
        dialog = BatchTagDialog(self.all_tags, len(self.selected_packages), "remove", self)
        
        # 传递公共标签信息给对话框
        dialog.common_tags = common_tags
        
        if dialog.exec_() == QDialog.Accepted:
            selected_tags = dialog.get_selected_tags()
            if not selected_tags:
                QMessageBox.information(self, "提示", "没有选择任何标签")
                return
            
            # 确认操作
            reply = QMessageBox.question(
                self, 
                "确认批量添加",
                f"确定要为 {len(self.selected_packages)} 个包添加以下标签吗？\n\n"
                f"标签: {', '.join(selected_tags)}\n\n"
                f"注意：此操作会将标签添加到所有选中的包，不会移除包原有的标签。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 批量更新标签
                updated_count = 0
                
                for package_identifier in self.selected_packages:
                    if self.add_tags_to_package(package_identifier, selected_tags):
                        updated_count += 1
                
                # 保存到CSV文件
                if updated_count > 0:
                    self.save_updated_csv()
                    
                    # 更新显示
                    self.filter_and_display()
                    
                    # 更新所有标签集合
                    for tag in selected_tags:
                        self.all_tags.add(tag)
                    
                    # # 显示成功信息
                    # QMessageBox.information(
                    #     self, 
                    #     "批量添加成功",
                    #     f"成功为 {updated_count}/{len(self.selected_packages)} 个包添加标签"
                    # )
                else:
                    QMessageBox.warning(self, "警告", "没有成功更新任何包")
        self.selected_packages.clear()
        self.update_ui_for_selection()  # 更新UI状态
        self.filter_and_display()


    def batch_remove_tags(self):
        """批量删除标签 - 显示所有标签，但高亮公共标签"""
        if not self.selected_packages:
            QMessageBox.warning(self, "警告", "没有选中的包")
            return
        
        # 获取所有选中包的公共标签
        common_tags = self.get_common_tags_for_selected_packages()
        
        print(f"选中的包 ({len(self.selected_packages)}个) 共有 {len(common_tags)} 个公共标签:")
        for tag in sorted(common_tags):
            print(f"  - {tag}")
        
        # 创建批量删除标签对话框，传递公共标签
        dialog = BatchTagDialog(
            self.all_tags, 
            len(self.selected_packages), 
            "remove", 
            self,
            common_tags  # 传递公共标签
        )
        
        if dialog.exec_() == QDialog.Accepted:
            selected_tags = dialog.get_selected_tags()
            if not selected_tags:
                QMessageBox.information(self, "提示", "没有选择任何标签")
                return
            
            # 确认操作
            reply = QMessageBox.question(
                self, 
                "确认批量删除",
                f"确定要从 {len(self.selected_packages)} 个包中删除以下标签吗？\n\n"
                f"标签: {', '.join(selected_tags)}\n\n"
                f"警告：此操作会从所有选中的包中移除指定的标签！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 批量移除标签
                updated_count = 0
                
                for package_identifier in self.selected_packages:
                    if self.remove_tags_from_package(package_identifier, selected_tags):
                        updated_count += 1
                
                # 保存到CSV文件
                if updated_count > 0:
                    self.save_updated_csv()
                    
                    # 更新显示
                    self.filter_and_display()
                    
                    # 显示成功信息
                    QMessageBox.information(
                        self, 
                        "批量删除成功",
                        f"成功从 {updated_count}/{len(self.selected_packages)} 个包中删除标签"
                    )
                else:
                    QMessageBox.warning(self, "警告", "没有成功更新任何包")
        self.selected_packages.clear()
        self.update_ui_for_selection()  # 更新UI状态
        self.filter_and_display()


    def get_common_tags_for_selected_packages(self):
        """获取选中包的公共标签"""
        if not self.selected_packages:
            return set()
        
        # 存储每个包的标签集合
        tags_sets = []
        
        for package_identifier in self.selected_packages:
            # 解析标识符
            if '.' in package_identifier:
                parts = package_identifier.split('.')
                if len(parts) >= 3:
                    author, package_name, version = parts[0], parts[1], parts[2]
                    
                    # 查找包
                    for package in self.var_data:
                        if (package.get('author') == author and 
                            package.get('package_name') == package_name and 
                            package.get('version') == version):
                            
                            # 获取标签
                            tags_str = package.get('tags', '')
                            tags = set(tag.strip() for tag in tags_str.split(',') if tag.strip())
                            tags_sets.append(tags)
                            break
        
        if not tags_sets:
            return set()
        
        # 计算所有标签集合的交集（公共标签）
        common_tags = tags_sets[0].copy()
        for tag_set in tags_sets[1:]:
            common_tags.intersection_update(tag_set)
        
        return common_tags

    def add_tags_to_package(self, package_identifier, tags_to_add):
        """向包中添加标签"""
        # 解析标识符
        if '.' in package_identifier:
            parts = package_identifier.split('.')
            if len(parts) >= 3:
                author, package_name, version = parts[0], parts[1], parts[2]
                
                # 查找包
                for package in self.var_data:
                    if (package.get('author') == author and 
                        package.get('package_name') == package_name and 
                        package.get('version') == version):
                        
                        # 获取当前标签
                        current_tags_str = package.get('tags', '')
                        current_tags = set(tag.strip() for tag in current_tags_str.split(',') if tag.strip())
                        
                        # 添加新标签
                        current_tags.update(tags_to_add)
                        
                        # 更新标签字段
                        new_tags_str = ','.join(sorted(current_tags)) if current_tags else ''
                        package['tags'] = new_tags_str
                        
                        return True
        
        return False

    def remove_tags_from_package(self, package_identifier, tags_to_remove):
        """从包中移除标签"""
        # 解析标识符
        if '.' in package_identifier:
            parts = package_identifier.split('.')
            if len(parts) >= 3:
                author, package_name, version = parts[0], parts[1], parts[2]
                
                # 查找包
                for package in self.var_data:
                    if (package.get('author') == author and 
                        package.get('package_name') == package_name and 
                        package.get('version') == version):
                        
                        # 获取当前标签
                        current_tags_str = package.get('tags', '')
                        current_tags = set(tag.strip() for tag in current_tags_str.split(',') if tag.strip())
                        
                        # 移除指定的标签
                        for tag in tags_to_remove:
                            current_tags.discard(tag)
                        
                        # 更新标签字段
                        new_tags_str = ','.join(sorted(current_tags)) if current_tags else ''
                        package['tags'] = new_tags_str
                        
                        return True
        
        return False

    def open_specific_path(self, path):
        """打开特定路径"""
        # 检查路径是否存在
        if not os.path.exists(path):
            QMessageBox.warning(self, "目录不存在", 
                               f"目标目录不存在:\n{path}\n\n"
                               f"请检查配置文件中的路径设置。")
            return
        
        try:
            # Windows系统
            if sys.platform == 'win32':
                # 使用explorer打开目录
                os.startfile(path)
            
            # macOS系统
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(['open', path])
            
            # Linux系统
            else:
                import subprocess
                subprocess.run(['xdg-open', path])
            
            print(f"已打开目录: {path}")
            
            # 在状态栏显示信息
            folder_name = os.path.basename(path)
            self.statusBar().showMessage(f"已打开: {folder_name}", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "打开失败", 
                               f"无法打开目录:\n{path}\n\n错误: {str(e)}")

    def extract_json_baby(self):
        def generate_clothing_preset(person_data,pkg_name):
            # print(pkg_name)
            for ci,json_path in person_data: # 每个包有多个json(ci)
                for item in ci:
                    if item.get("id") == "geometry":
                        clothing_data = item.get("clothing") # 只添加和替换clothing
                        # 1 纠正包路径
                        for  pat in clothing_data: 
                            # print(pat)
                            # pat["id"] = Hunting-Succubus.Enhanced_Eyes.latest:/Custom/Clothing/Female/HUNTING-SUCCUBUS/Enhanced_Eyes/Enhanced Eyes Realastic.vam
                            if (":" in pat["id"]) and ("SELF" not in pat["id"]): # 外部依赖
                                pkg_name_before = pat["id"].split(":",-1)[0].split(".",-1)[:-1]
                                pkg_name_before = '.'.join(str(x) for x in pkg_name_before) # 版本号配对,很麻烦
                                # pkg_name_before = Hunting-Succubus.Enhanced_Eyes
                                pkg_name_before_daimaohao = pat["id"].split(":",-1)[0].split(".",-1)[:-1]
                                # print(pkg_name_before_daimaohao)
                                # dirs = os.listdir(self.unzip_base_dir)
                                dirs_ = os.listdir(self.var_scan_dir)
                                dirs = [d[:-4] for d in dirs_]
                                # print(dirs)
                                for package_real_name in dirs:
                                    # print( package_real_name)
                                    if  package_real_name.__contains__(pkg_name_before): # package_real_name = Hunting-Succubus.Enhanced_Eyes.3
                                        # clothing_data = [{'id': 'Harli Heels', 'enabled': 'true'}, {'id': 'Heat Up Panty Sim', 'enabled': 'true'}, {'id': 'Red Rabbit Dress', 'enabled': 'true'}, {'id': 'Hunting-Succubus.Enhanced_Eyes.3:/Custom/Clothing/Female/HUNTING-SUCCUBUS/Enhanced_Eyes/Enhanced Eyes Realastic.vam', 'internalId': 'HUNTING-SUCCUBUS:Enhanced Eyes Realastic', 'enabled': 'true'}]
                                        clothing_data = eval( str(clothing_data).replace(pat["id"].split(":",-1)[0], package_real_name) )
                                        # print(clothing_data)
                            elif "SELF" in pat["id"]:
                                clothing_data = eval( str(clothing_data).replace("SELF", pkg_name) ) # 包内
                        # print(clothing_data,"\n")
                        # 将item内的item.get("clothing") 替换为 clothing_data
                        item["clothing"] = clothing_data # 这一步不知道对不对

                        try: # 这个包可能是没有依赖的
                            # # 2 添加vaj服装细节文件并纠正路径,每一个的路径在id,继续寻找服装细致文件
                            clothing_detail_data = [] # 服装超精准配置存放,清0
                            for clothing_item in clothing_data:
                                # print(clothing_item["id"])
                                if ":" in clothing_item["id"]:
                                    pkg_name_ = clothing_item["id"].split(":")[0]
                                    vaj_base_name = clothing_item["id"].split(":")[1].replace("vam","vaj").replace("/", "\\")
                                    vaj_full_name = os.path.join(pkg_name_ + vaj_base_name) # 从主目录找文件
                                    
                                    # print("    吸收细节",vaj_full_name)
                                    # 根据json 中的vaj文件路径,定位文件,并找到服装的具体参数
                                    with open( os.path.join(self.unzip_base_dir,vaj_full_name), 'r', encoding='utf-8') as garment_file:
                                        storable_data = json.load(garment_file)["storables"]
                                    # print(storable_data)
                                    for storable_item in storable_data:
                                        # 贴图属性列表
                                        texture_properties = [
                                            "customTexture_MainTex", "customTexture_SpecTex", 
                                            "customTexture_GlossTex", "customTexture_AlphaTex", 
                                            "customTexture_BumpMap", "customTexture_DecalTex", 
                                            "simTexture"
                                        ]
                                        for texture_prop in texture_properties:
                                            if (texture_prop in storable_item) and (storable_item[texture_prop] != ""):
                                                # storable_item中的贴图路径[texture_properties] 全部换完
                                                original_texture = storable_item[texture_prop]
                                                new_base_path = pkg_name_ + ":" + vaj_base_name
                                                path_parts = new_base_path.split("\\", -1)[0:-1]
                                                new_texture_path = '\\'.join( part for part in path_parts) + "\\" + original_texture
                                                new_texture_path = new_texture_path.replace("./","").replace(" ./","").replace("/","\\")
                                                # print(new_texture_path)                                                    
                                                storable_item[texture_prop] = new_texture_path # 轮奸替换
                                                # 添加到结果列表
                                        clothing_detail_data.append(storable_item) # 可能有问题,替换完了加到这个表里面
                                        # 遍历clothing_detail_data，把他的每一项添加进item
                                        for detail_item in clothing_detail_data:
                                            ci.append(detail_item)
                        except Exception as e: 
                            print(str(e)) # 可能是缺少依赖

            # 头发
            for ci,json_path in person_data:
                for item in ci:
                    if item.get("id") == "geometry":
                        clothing_data = item.get("hair") # 只添加和替换clothing
                        # print(f"   正在读取 {PKG_name} 内 {json_file}  的hair数据")
                        # 1 纠正包路径
                        for  pat in clothing_data: 
                            # print(pat)
                            # pat["id"] = Hunting-Succubus.Enhanced_Eyes.latest:/Custom/Clothing/Female/HUNTING-SUCCUBUS/Enhanced_Eyes/Enhanced Eyes Realastic.vam
                            if (":" in pat["id"]) and ("SELF" not in pat["id"]): # 外部依赖
                                pkg_name_before = pat["id"].split(":",-1)[0].split(".",-1)[:-1]
                                pkg_name_before = '.'.join(str(x) for x in pkg_name_before) # 版本号配对,很麻烦
                                # pkg_name_before = Hunting-Succubus.Enhanced_Eyes
                                pkg_name_before_daimaohao = pat["id"].split(":",-1)[0].split(".",-1)[:-1]
                                # print(pkg_name_before_daimaohao)
                                # dirs = os.listdir(self.unzip_base_dir)
                                dirs_ = os.listdir(self.var_scan_dir)
                                dirs = [d[:-4] for d in dirs_]
                                for package_real_name in dirs:
                                    if  package_real_name.__contains__(pkg_name_before): # package_real_name = Hunting-Succubus.Enhanced_Eyes.3
                                        # clothing_data = [{'id': 'Harli Heels', 'enabled': 'true'}, {'id': 'Heat Up Panty Sim', 'enabled': 'true'}, {'id': 'Red Rabbit Dress', 'enabled': 'true'}, {'id': 'Hunting-Succubus.Enhanced_Eyes.3:/Custom/Clothing/Female/HUNTING-SUCCUBUS/Enhanced_Eyes/Enhanced Eyes Realastic.vam', 'internalId': 'HUNTING-SUCCUBUS:Enhanced Eyes Realastic', 'enabled': 'true'}]
                                        clothing_data = eval( str(clothing_data).replace(pat["id"].split(":",-1)[0], package_real_name) )
                                        # print(clothing_data)
                            elif "SELF" in pat["id"]:
                                clothing_data = eval( str(clothing_data).replace("SELF", pkg_name) ) # 包内
                        # print(clothing_data,"\n")
                        # 将item内的item.get("clothing") 替换为 clothing_data
                        item["hair"] = clothing_data # 这一步不知道对不对

                        try:
                            # # 2 添加vaj服装细节文件并纠正路径,每一个的路径在id,继续寻找服装细致文件
                            clothing_detail_data = [] # 服装超精准配置存放,清0
                            for clothing_item in clothing_data:
                                # print(clothing_item["id"])
                                if ":" in clothing_item["id"]:
                                    pkg_name_ = clothing_item["id"].split(":")[0]
                                    vaj_base_name = clothing_item["id"].split(":")[1].replace("vam","vaj").replace("/", "\\")
                                    vaj_full_name = os.path.join(self.unzip_base_dir, pkg_name_ + vaj_base_name) # 从主目录找文件
                                    # print("    吸收细节",vaj_full_name)
                                    # 根据json 中的vaj文件路径,定位文件,并找到服装的具体参数
                                    with open(os.path.join(self.unzip_base_dir,vaj_full_name), 'r', encoding='utf-8') as garment_file:
                                        storable_data = json.load(garment_file)["storables"]
                                    # print(storable_data)
                                    for storable_item in storable_data:
                                        # 贴图属性列表
                                        texture_properties = [
                                            "customTexture_MainTex", "customTexture_SpecTex", 
                                            "customTexture_GlossTex", "customTexture_AlphaTex", 
                                            "customTexture_BumpMap", "customTexture_DecalTex", 
                                            "simTexture"
                                        ]
                                        for texture_prop in texture_properties:
                                            if (texture_prop in storable_item) and (storable_item[texture_prop] != ""):
                                                # storable_item中的贴图路径[texture_properties] 全部换完
                                                original_texture = storable_item[texture_prop]
                                                new_base_path = pkg_name_ + ":" + vaj_base_name
                                                path_parts = new_base_path.split("\\", -1)[0:-1]
                                                new_texture_path = '\\'.join( part for part in path_parts) + "\\" + original_texture
                                                new_texture_path = new_texture_path.replace("./","").replace(" ./","").replace("/","\\")
                                                # print(new_texture_path)                                                    
                                                storable_item[texture_prop] = new_texture_path # 轮奸替换
                                                # 添加到结果列表
                                        clothing_detail_data.append(storable_item) # 可能有问题,替换完了加到这个表里面
                                        # 遍历clothing_detail_data，把他的每一项添加进item
                                        for detail_item in clothing_detail_data:
                                            ci.append(detail_item)
                        except Exception as e:
                            print(str(e)) # 可能是缺少依赖
            
            # 皮肤
            for ci,json_path in person_data:
                for item in ci:
                    if item.get("id") == "textures":
                        skintypes = ["faceDiffuseUrl","torsoDiffuseUrl","genitalsDiffuseUrl","faceDecalUrl","limbsDiffuseUrl","faceSpecularUrl","torsoSpecularUrl","limbsSpecularUrl"\
                        ,"genitalsSpecularUrl","faceGlossUrl","torsoGlossUrl","limbsGlossUrl","genitalsGlossUrl","faceNormalUrl","torsoNormalUrl","limbsNormalUrl","genitalsNormalUrl","torsoDetailUrl"\
                        ,"limbsDetailUrl","faceDecalUrl","genitalsDetailUrl","limbsDecalUrl","torsoDecalUrl","genitalsDecalUrl"]
                        # print(f"   正在读取 {PKG_name} 内 {json_file}  的textures数据")
                        for  iasad in skintypes:
                            clothing_data = item.get(iasad)
                            # print(clothing_data)
                            if clothing_data is not None:
                                # 1 一个一个纠正包路径
                                if (":" in clothing_data) and ("SELF" not in clothing_data): # 外部依赖
                                    pkg_name_before = clothing_data.split(":",-1)[0].split(".",-1)[:-1]
                                    pkg_name_before = '.'.join(str(x) for x in pkg_name_before) # 版本号配对,很麻烦
                                    # print(pkg_name_before)
                                    pkg_name_before_daimaohao = clothing_data.split(":",-1)[0]
                                    # print(pkg_name_before_daimaohao)
                                    # dirs = os.listdir(self.unzip_base_dir)
                                    dirs_ = os.listdir(self.var_scan_dir)
                                    dirs = [d[:-4] for d in dirs_]
                                    for package_real_name in dirs:
                                        if  package_real_name.__contains__(pkg_name_before):
                                            clothing_data = clothing_data.replace(pkg_name_before_daimaohao, package_real_name)
                                            # print(clothing_data)
                                elif "SELF" in clothing_data:
                                    # print(clothing_data,"TYU")
                                    clothing_data = clothing_data.replace("SELF", pkg_name)# 包内
                                    # print(clothing_data)
                                    item[iasad]=clothing_data
                                else: # 类似这种和json文件同一个目录的最难处理!: "faceDiffuseUrl" : "Alexandr_face_MH.jpg", 
                                    base_path = os.path.join(self.unzip_base_dir,pkg_name)
                                    fffff = json_path.replace(base_path,"").split("\\",-1)
                                    tmpp = "\\".join(fffff[0:-1])+"\\" # 有些的文件路径不是\，需要特殊处理

                                    clothing_data = pkg_name+":"+tmpp+ clothing_data
                                    item[iasad]= clothing_data
                            # print(clothing_data)
                pat = '"SELF:'
                yyyyy = str(ci)
                ci = eval(yyyyy.replace(pat,f'"{pkg_name}:')) # eval可能会消耗性能
                # { 
                #    "id" : "teeth", 
                #    "customTexture_MainTex" : "SELF:/Custom/Atom/Person/Textures/Eye and Mouth/MouthD.jpg"
                # } 除了皮肤,还有形体的问题
                # 直接暴力把SELF re 替换最快
                    

            return person_data


        Femile_character_id = ["Female Dummy","Female 1", "Female 2", "Female 3", "Female 4", "Female 5", "Female 6", "Female 7", "Female 8", "Female 9", "Female 10", "Female 11", "Female 12", "Female 13", "Female 14", "Female 15", "Female 16", "Female 17"\
        ,"Candy","Evey","Janie","Kayla","Lexi","Maria","Mia","Simone","Tara","Tina","Female Custom"]
        for pkg_name in self.selected_packages:
            result = []
            # 进入单个包目录,提取json名，一个包有多个json
            json_path = os.path.join(self.unzip_base_dir,pkg_name)
            json_dir = []
            for root, dirs, files in os.walk(json_path):
                for file in files:
                    if file.endswith('.json') and file!="meta.json":
                        src = os.path.join(root, file)
                        json_dir.append(src)
            # 打开json提取信息
            for json_path in json_dir:
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f,strict=False)
                # 查找所有type为Person的atom
                print("[+] 打开",pkg_name)
                for atom in json_data.get("atoms", []):
                    if atom.get("type") == "Person":
                        for jj in atom.get("storables"):
                            if jj.get("id") == "geometry":
                                if jj['character'] in Femile_character_id:
                                    print("    id = ",atom.get("id"),",所选人物是女性")
                                    result.append( [atom.get("storables", {}),json_path])
                                else:
                                    print("    所选人物非女性")
            S = generate_clothing_preset(result,pkg_name)
            
            directories = [
                os.path.join(os.getcwd(),self.output_base_dir,"Custom","Atom","Person","Clothing"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Hair"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Pose"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Appearance"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Morphs"),
                os.path.join(os.getcwd(), self.output_base_dir, "Custom", "Atom", "Person", "Skin")]


            count = 0
            # 使用进度条
            for i in tqdm(range(len(S)), desc="生成预设文件"):
                print(f"\n正在写入{pkg_name}__{count} json文件")
                clothing_preset = {"setUnlistedParamsToDefault": "true", "storables": S[i][0]}
                # 使用最紧凑的JSON格式
                json_str = json.dumps(clothing_preset, separators=(',', ':'), ensure_ascii=False) # , indent=2
                # 基础文件名
                base_name = f"Preset_{pkg_name}"

                # 写入5个文件
                files = [
                    os.path.join(directories[0], "json提取", f"{base_name}_NO_{i}.vap"),
                    os.path.join(directories[1], "json提取", f"{base_name}_NO_{i}.vap"),
                    os.path.join(directories[2], "json提取", f"{base_name}_NO_{i}.vap"),
                    os.path.join(directories[3], "json提取", f"{base_name}_A_{i}.vap"),
                    os.path.join(directories[4], "json提取", f"{base_name}_NO_{i}.vap")
                ]
                files1 = [
                    os.path.join(directories[0], "json提取"),
                    os.path.join(directories[1], "json提取"),
                    os.path.join(directories[2], "json提取"),
                    os.path.join(directories[3], "json提取"),
                    os.path.join(directories[4], "json提取")
                ]
                for kkk in files1:
                    os.makedirs(kkk, exist_ok=True)

                for file_path in files:
                    # 尝试写入文件，如果失败可能是文件名编码问题
                    try:
                        with open(file_path, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                            f.write(json_str)
                    except (PermissionError, OSError) as e:
                        # 如果因为中文字符失败，尝试编码处理
                        print(f"尝试写入 {file_path} 失败: {e}")
                        # 方案A: 尝试使用gbk编码的路径
                        try:
                            # 将路径转换为gbk
                            file_path_gbk = file_path.encode('gbk').decode('gbk')
                            # 有的 json 文件几包mb,必须要 buffering
                            with open(file_path_gbk, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                                f.write(json_str)
                            print(f"使用gbk编码路径写入成功")
                        except:
                            # 方案B: 去除中文字符
                            dir_path = os.path.dirname(file_path)
                            file_name = os.path.basename(file_path)
                            
                            # 将"json提取"改为英文
                            if "json提取" in dir_path:
                                dir_path = dir_path.replace("json提取", "json_extract")
                                os.makedirs(dir_path, exist_ok=True)
                                new_file_path = os.path.join(dir_path, file_name)
                                
                                with open(new_file_path, "w", encoding="utf-8", buffering=16*1024*1024) as f:
                                    f.write(json_str)
                                print(f"使用英文路径写入成功")
                count += 1

    def download_vars_from_hub(self,pkg_list):
        print(1)

    def extract_json(self):
        def get_all_dependencies_on_json(saves_directory):
            res = []
            pattern = r':.*"(.*):'
            for root, dirs, files in os.walk(saves_directory):
                for file in files:
                    # 检查文件是否是JSON文件
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            # 读取JSON文件
                            with open(file_path, 'r', encoding='utf-8') as f:
                                match = re.compile(pattern).findall(f.read())
                                for j in match:
                                    if "." in j:
                                        res.append(j)
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON解析错误: {file_path} - {e}")
            return res
                # 查找所有目录下的json 获取额外的依赖,避免json加载失败，其他的如vap则无所谓。
        def find_dependencies(dependencies):
            need_download_package = []
            for package in dependencies:
                # 格式化
                i = package.split(".",-1)
                if len(i)==3:
                    dep = {
                    'author': i[0],
                    'package_name': i[1],
                    'version': i[2]
                    }
                else:
                    continue
                # 查询var文件
                if dep['version'].lower() == 'latest':
                    # 查询最新版本
                    latest_mask = (var_packages['author'] == dep['author']) & (var_packages['package_name'] == dep['package_name'])
                    latest_versions = var_packages[latest_mask]
                    if latest_versions.empty:
                        need_download_package.append(package)
                else:
                    dep_mask = (var_packages['author'] == dep['author']) & (var_packages['package_name'] == dep['package_name']) & (var_packages['version'] == dep['version'])
                    dep_row = var_packages[dep_mask]
                    if dep_row.empty:
                        need_download_package.append(package)
            # print("\n\n待补全的包；",need_download_package)
            return need_download_package


        try:
            var_packages = pd.read_csv(self.csv_file, encoding="gb18030")
            all_need_download_package = []
            for i in self.selected_packages:
                # 从包目录中找到当前的包所有的额外依赖
                path = os.path.join(self.unzip_base_dir, i)
                extra_dependencies = get_all_dependencies_on_json(path)
                # print(extra_dependencies)

                # 从CSV数据中获取当前包的基本依赖
                current_depends = []
                for package_data in self.var_data:
                    if package_data.get('filename', '').replace('.var', '') == i:
                        depends_str = package_data.get('dependencies', '')
                        if depends_str and depends_str not in ["无依赖", "无meta.json", "meta.json解析错误"]:
                            current_depends = [d.strip() for d in depends_str.split(',')]
                        break
                
                print(f"  CSV中的基础依赖 ({len(current_depends)}个):")
                
                # 合并依赖
                all_dependencies = list(set(current_depends + extra_dependencies))
                print(f"额外依赖 ({len(extra_dependencies)}个)，基本依赖 ({len(current_depends)}个)，  合并后总依赖 ({len(all_dependencies)}个):")
                for dep in sorted(all_dependencies):
                    print(f"    - {dep}")

                need_download_package = find_dependencies(all_dependencies)
                all_need_download_package.extend(need_download_package)
            # 下载包
            all_need_download_package = list(set(all_need_download_package))
            # all_need_download_package = ["_bury.AE_Inflate_cleaned.1"]
            print("待下载的全部包",all_need_download_package)
            self.download_vars_from_hub( need_download_package )

        except Exception as e:
            print(i,"该文件出错了，请删除后复盘")
            print(str(e))
        QMessageBox.critical(self, "更新完成!", "查看完成!")
    
    def open_ai_analyzer(self):
        """搜索meta.json并复制contentList到剪贴板"""
        print("\n")
        all_content = ["你好，你是virt a mate分析师 我给你一个分析样本格式： ABCgirls.[ABCgirls]Ninja_Girl_Suit.1: ['Custom/Clothing/Female/ABCgirls/ABC 073 2', 'Custom/Clothing/Female/ABCgirls/ABC 073 1', 'Custom/Clothing/Female/ABCgirls/ABC 063 HEAD', 'Custom/Clothing/Female/ABCgirls/ABC 005 BOOTS', 'Custom/Clothing/Female/ABCgirls/ABC 005 ARM']\n输出:ABCgirls.[ABCgirls]Ninja_Girl_Suit.1: ABCgirls发布的包含忍者主题连体衣、头部配饰、靴子和手臂护甲的完整女忍者套装服装资源。\n注意输出的内容不需要分析结果，只需要一句话，服装头发等都要知道类型，场景需要知道玩法，根据:后面的文件名内容详细分析。\n\n接下来是我的其他样本，你按照这个格式继续生成"]
        
        for package in self.selected_packages:
            meta_path = os.path.join(self.unzip_base_dir, package, "meta.json")
            content = f"{package}: "
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        contentlist = data.get("contentList", [])
                        content += str(contentlist)
                except:
                    content += "读取失败"
            else:
                content += "无meta.json"
            
            print(content)
            all_content.append(content)
        
        # 复制到剪贴板
        if all_content:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(all_content))
            print(f"\n已复制 {len(all_content)} 条结果到剪贴板")
    
    def get_package_ai_description(self,ai_search_text,ai_exclude_text):
        ai_tigs = ai_search_text.split(" ",-1)
        ai_exclde_tigs = ai_exclude_text.split(" ",-1)

        # 加载AI特征文件
        ai_feature_file = os.path.join(os.getcwd(), "Files", "AI_包特征.txt")
        ai_features = {}
        res = []
        if os.path.exists(ai_feature_file):
            try:
                with open(ai_feature_file, 'r', encoding='gb18030') as f:
                    lines = f.readlines()
                    for line in lines:
                        can_append = True
                        for j in ai_exclde_tigs:
                            if j in line and j!="":
                                can_append = False
                        for i in ai_tigs:
                            if i not in line:
                                can_append = False
                                break
                        if can_append:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                pkg_id = parts[0].strip()
                                res.append( pkg_id )
            except Exception as e:
                print(f"加载AI特征文件失败: {e}")
        return res

    def get_package_packages(self,File_info_text):
        patt = File_info_text.split(r"===",-1)
        rse = []
        for File_info in self.File_info_data:
            can_append = True
            for j in patt:
                if j.lower() not in File_info.lower():
                    can_append = False
                    break
            if can_append:
                # print(File_info.split(":::",-1)[0])
                tmp = File_info.split(":::",-1)
                pkg_name = tmp[0]
                pkg_name = ".".join(pkg_name.split(".",-1)[:-1])
                # print(pkg_name)
                rse.append(pkg_name)
        return rse

    def load_dependency_stats(self):
        """加载依赖统计信息"""
        if os.path.exists(self.csv_file):
            try:
                with open(self.csv_file, 'r', encoding='gb18030') as f:
                    dependencies = [row['dependencies'] for row in csv.DictReader(f)]
                
                dep_counter = Counter()
                for deps in dependencies:
                    if deps and deps not in ["无依赖", "无meta.json", "meta.json解析错误"]:
                        dep_items = [d.strip() for d in deps.split(",") if d.strip()]
                        
                        # 处理依赖项
                        for dep in dep_items:
                            parts = dep.split(".")
                            if len(parts) > 1:
                                # 取从开始到倒数第二个部分（去除版本号）
                                processed_dep = ".".join(parts[0:-1])
                                dep_counter.update([processed_dep])
                
                self.dependency_counter = dep_counter
                print(f"已加载 {len(dep_counter)} 个依赖项的统计信息")
                
                # 可选：保存到文件
                self.save_dependency_stats()
                
            except Exception as e:
                print(f"加载依赖统计失败: {e}")
    
    def save_dependency_stats(self):
        """保存依赖统计到文件"""
        try:
            with open(self.dep_stats_file, 'w', newline='', encoding='gb18030') as f:
                writer = csv.writer(f)
                writer.writerow(['dependency', 'count'])
                for dep, count in self.dependency_counter.most_common():
                    writer.writerow([dep, count])
            print(f"依赖统计已保存到 {self.dep_stats_file}")
        except Exception as e:
            print(f"保存依赖统计失败: {e}")
    
    def get_dependency_reference_count(self, author, package_name):
        """获取包的被引用次数"""
        # 构建包标识（不含版本号）
        package_identifier = f"{author}.{package_name}"
        
        # 获取引用次数
        reference_count = self.dependency_counter.get(package_identifier, 0)
        return reference_count

    def print_selected_packages(self):
        """打印选中的包名"""
        print("当前选中的包:")
        for package_name in sorted(self.selected_packages):
            print(f"  - {package_name}")
            for File_info in self.File_info_data:
                tmp = File_info.split(":::",-1)
                pkg_name = tmp[0]
                if pkg_name==package_name:
                    print(tmp[1])
        print(f"总共选中 {len(self.selected_packages)} 个包")

    def show_reference_details(self, author, package_name):
        """显示包的引用详情 - 添加已安装/未安装状态"""
        package_identifier = f"{author}.{package_name}"
        
        # 查找哪些包引用了这个包
        referencing_packages = []
        for package in self.var_data:
            deps_str = package.get('dependencies', '')
            if deps_str and deps_str not in ["无依赖", "无meta.json", "meta.json解析错误"]:
                deps = [d.strip() for d in deps_str.split(",") if d.strip()]
                for dep in deps:
                    dep_parts = dep.split(".")
                    if len(dep_parts) > 1:
                        dep_identifier = ".".join(dep_parts[0:-1])
                        if dep_identifier == package_identifier:
                            referencing_packages.append(package)
                            break
        
        # 创建详情对话框并居中显示
        dialog = QDialog(self)
        dialog.setWindowTitle(f"引用详情 - {author}.{package_name}")
        
        # 获取主窗口中心位置
        center_point = self.geometry().center()
        
        # 设置对话框位置和大小
        dialog_width = 800
        dialog_height = 600
        dialog.setGeometry(
            center_point.x() - dialog_width // 2,
            center_point.y() - dialog_height // 2,
            dialog_width,
            dialog_height
        )
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel(f"包 {author}.{package_name} 被以下 {len(referencing_packages)} 个包引用：")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 列表显示
        self.reference_list_widget = QListWidget()
        self.reference_list_widget.setSelectionMode(QListWidget.MultiSelection)  # 允许多选
        
        # 存储包数据，用于点击跳转
        self.reference_package_data = []
        
        for package in referencing_packages:
            # 检查引用包是否存在（已安装）
            ref_exists = True  # 默认已安装（因为来自var_data）
            
            # 构建显示文本
            status_icon = "✓"
            status_color = "#28a745"
            status_text = "（已安装）"
            
            item_text = f"{status_icon} {package.get('author', '')}.{package.get('package_name', '')}.{package.get('version', '')} {status_text}"
            
            # 创建自定义项
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, package)
            
            # 设置颜色
            item.setForeground(QColor(status_color))
            
            self.reference_list_widget.addItem(item)
            self.reference_package_data.append(package)
        
        # 全选按钮
        select_all_btn = QPushButton("全选所有引用包")
        select_all_btn.clicked.connect(self.select_all_referencing_packages)
        layout.addWidget(select_all_btn)
        
        layout.addWidget(self.reference_list_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 查看选中包按钮
        view_btn = QPushButton("查看选中包")
        view_btn.clicked.connect(lambda: self.view_selected_referencing_packages(dialog))
        button_layout.addWidget(view_btn)
        
        # +++ 新增：PLUS版本按钮 - 递归查看引用 +++
        view_btn_plus = QPushButton("查看选中引用包PLUS")
        view_btn_plus.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
        """)
        view_btn_plus.clicked.connect(lambda: self.open_references_details_window(dialog))
        button_layout.addWidget(view_btn_plus)

        # 批量添加到选择按钮
        add_to_selection_btn = QPushButton("批量添加到选择")
        add_to_selection_btn.clicked.connect(lambda: self.add_references_to_selection(dialog))
        button_layout.addWidget(add_to_selection_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("关闭")
        cancel_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def add_references_to_selection(self, dialog):
        """将引用包添加到当前选择（不切换视图）"""
        if not hasattr(self, 'reference_list_widget'):
            return
        
        selected_items = self.reference_list_widget.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(dialog, "提示", "请先选择要添加的引用包")
            return
        
        added_count = 0
        for item in selected_items:
            row = self.reference_list_widget.row(item)
            if row < len(self.reference_package_data):
                package = self.reference_package_data[row]
                package_identifier = f"{package.get('author', '')}.{package.get('package_name', '')}.{package.get('version', '')}"
                self.selected_packages.add(package_identifier)
                added_count += 1
        
        # 更新UI
        self.update_ui_for_selection()
        
        # 显示提示但不关闭对话框
        QMessageBox.information(dialog, "成功", f"已添加 {added_count} 个引用包到当前选择")

    def select_all_referencing_packages(self):
        """全选所有引用包"""
        self.reference_list_widget.selectAll()

    def view_selected_referencing_packages(self, dialog):
        """查看选中的引用包"""
        selected_items = self.reference_list_widget.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(dialog, "提示", "请先选择要查看的包")
            return
        
        # 清空当前选择
        self.selected_packages.clear()
        
        # 将选中的引用包添加到当前选择
        for item in selected_items:
            row = self.reference_list_widget.row(item)
            if row < len(self.reference_package_data):
                package = self.reference_package_data[row]
                package_identifier = f"{package.get('author', '')}.{package.get('package_name', '')}.{package.get('version', '')}"
                self.selected_packages.add(package_identifier)
        
        # 关闭对话框
        dialog.accept()
        
        # 切换到"查看选中包"模式
        self.view_selected_packages()
        
        # 滚动到第一个选中的包
        if self.selected_packages:
            first_package = next(iter(self.selected_packages))
            # 这里可以添加滚动到指定包的功能
            self.statusBar().showMessage(f"已选择 {len(selected_items)} 个引用包", 3000)








    def show_dependency_details_window(self, author, package_name, dep_count):
        """显示依赖详情窗口"""
        # 构建包标识符（带版本号）
        package_identifier = None
        package_version = None
        print(len(self.var_data))
        # 查找包的完整标识符
        for package in self.var_data:
            if package.get('author') == author and package.get('package_name') == package_name:
                package_identifier = f"{author}.{package.get('package_name', '')}.{package.get('version', '')}"
                package_version = package.get('version', '')
                dependencies_str = package.get('dependencies', '')
                break
        
        if not package_identifier:
            QMessageBox.warning(self, "警告", f"未找到包: {author}.{package_name}")
            return
        
        # 解析依赖项
        dependencies = []
        if dependencies_str and dependencies_str not in ["无依赖", "无meta.json", "meta.json解析错误"]:
            deps = [d.strip() for d in dependencies_str.split(",") if d.strip()]
            for dep in deps:
                parts = dep.split(".")
                if len(parts) >= 3:
                    dependencies.append({
                        'author': parts[0],
                        'package_name': parts[1],
                        'version': parts[2],
                        'full_identifier': dep
                    })
                elif len(parts) == 2:
                    dependencies.append({
                        'author': parts[0],
                        'package_name': parts[1],
                        'version': 'latest',
                        'full_identifier': dep + ".latest"
                    })
        
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"依赖详情 - {author}.{package_name}.{package_version}")
        
        # 设置对话框大小和位置
        dialog_width = 800
        dialog_height = 600
        dialog.setGeometry(
            self.geometry().center().x() - dialog_width // 2,
            self.geometry().center().y() - dialog_height // 2,
            dialog_width,
            dialog_height
        )
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel(f"包 {author}.{package_name}.{package_version} 依赖以下 {len(dependencies)} 个包：")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 如果依赖为空，显示提示
        if not dependencies:
            no_deps_label = QLabel("此包没有依赖项")
            no_deps_label.setStyleSheet("font-size: 14px; color: #666; padding: 20px;")
            layout.addWidget(no_deps_label)
        else:
            # 依赖列表
            self.dependency_list_widget = QListWidget()
            self.dependency_list_widget.setSelectionMode(QListWidget.MultiSelection)  # 允许多选
            
            # 存储依赖数据
            self.dependency_data = []
            
            for dep in dependencies:
                # 检查依赖包是否存在
                dep_exists = False
                for package in self.var_data:
                    if (package.get('author') == dep['author'] and 
                        package.get('package_name') == dep['package_name']):
                        dep_exists = True
                        break
                
                # 构建显示文本
                status_icon = "✓" if dep_exists else "✗"
                status_color = "#28a745" if dep_exists else "#dc3545"
                status_text = "（已安装）" if dep_exists else "（未安装）"
                
                item_text = f"{status_icon} {dep['author']}.{dep['package_name']}.{dep['version']} {status_text}"
                
                # 创建自定义项
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, dep)
                
                # 设置颜色
                item.setForeground(QColor(status_color))
                
                self.dependency_list_widget.addItem(item)
                self.dependency_data.append(dep)
            
            # 全选按钮
            select_all_btn = QPushButton("全选所有依赖包")
            select_all_btn.clicked.connect(self.select_all_dependencies)
            layout.addWidget(select_all_btn)
            
            layout.addWidget(self.dependency_list_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        if dependencies:
            # 查看选中依赖按钮
            view_btn = QPushButton("查看选中依赖包")
            view_btn.clicked.connect(lambda: self.view_selected_dependencies(dialog))
            button_layout.addWidget(view_btn)
            
            # +++ 新增：PLUS版本按钮 - 递归查看依赖 +++
            view_btn_plus = QPushButton("查看选中依赖包PLUS")
            view_btn_plus.setStyleSheet("""
                QPushButton {
                    background-color: #6f42c1;
                    color: white;
                    font-weight: bold;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #5a32a3;
                }
            """)
            view_btn_plus.clicked.connect(lambda: self.open_dependency_details_window(dialog))
            button_layout.addWidget(view_btn_plus)

            # 批量添加到选择按钮
            add_to_selection_btn = QPushButton("批量添加到选择")
            add_to_selection_btn.clicked.connect(lambda: self.add_dependencies_to_selection(dialog))
            button_layout.addWidget(add_to_selection_btn)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def select_all_dependencies(self):
        """全选所有依赖包"""
        if hasattr(self, 'dependency_list_widget'):
            self.dependency_list_widget.selectAll()
    def view_selected_dependencies(self, dialog):
        """查看选中的依赖包"""
        if not hasattr(self, 'dependency_list_widget'):
            return
        
        selected_items = self.dependency_list_widget.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(dialog, "提示", "请先选择要查看的依赖包")
            return
        
        # 清空当前选择
        self.selected_packages.clear()
        
        # 将选中的依赖包添加到当前选择
        for item in selected_items:
            dep = item.data(Qt.UserRole)
            if dep:
                # 查找完整版本
                full_identifier = None
                for package in self.var_data:
                    if (package.get('author') == dep['author'] and 
                        package.get('package_name') == dep['package_name']):
                        
                        # 如果是latest，使用最新版本
                        if dep['version'].lower() == 'latest':
                            full_identifier = f"{dep['author']}.{dep['package_name']}.{package.get('version', '')}"
                        else:
                            # 查找精确版本
                            if package.get('version') == dep['version']:
                                full_identifier = f"{dep['author']}.{dep['package_name']}.{dep['version']}"
                        
                        if full_identifier:
                            self.selected_packages.add(full_identifier)
                            break
        
        # 关闭对话框
        dialog.accept()
        
        # 切换到"查看选中包"模式
        self.view_selected_packages()
        
        # 显示提示
        self.statusBar().showMessage(f"已选择 {len(selected_items)} 个依赖包", 3000)

    def add_dependencies_to_selection(self, dialog):
        """将依赖包添加到当前选择（不切换视图）"""
        if not hasattr(self, 'dependency_list_widget'):
            return
        
        selected_items = self.dependency_list_widget.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(dialog, "提示", "请先选择要添加的依赖包")
            return
        
        added_count = 0
        for item in selected_items:
            dep = item.data(Qt.UserRole)
            if dep:
                # 查找完整版本
                for package in self.var_data:
                    if (package.get('author') == dep['author'] and 
                        package.get('package_name') == dep['package_name']):
                        
                        full_identifier = f"{dep['author']}.{dep['package_name']}.{package.get('version', '')}"
                        self.selected_packages.add(full_identifier)
                        added_count += 1
                        break
        
        # 更新UI
        self.update_ui_for_selection()
        
        # 显示提示但不关闭对话框
        QMessageBox.information(dialog, "成功", f"已添加 {added_count} 个依赖包到当前选择")






    def calculate_package_score(self, package):
        # 定位1
        """计算包的得分"""
        score_details = {}
        total_score = 0
        
        # 1. 依赖情况得分
        dependencies = package.get('dependencies', '')
        
        # 先检查是否有依赖
        if not dependencies or dependencies in ["无依赖", "无meta.json", "meta.json解析错误"]:
            # 没有依赖：+100分
            score_details["无依赖"] = self.score_weights["no_dependencies"]
            total_score += score_details["无依赖"]
        else:
            # 有依赖：计算依赖数量并扣分
            try:
                # 解析依赖项，统计数量
                dep_items = [d.strip() for d in dependencies.split(",") if d.strip()]
                dep_count = len(dep_items)
                
                # 每引用一个依赖扣5分
                dep_deduction = dep_count * 5
                score_details[f"依赖{dep_count}个(扣{abs(dep_deduction)}分)"] = -dep_deduction
                total_score -= dep_deduction
                
                # 也可以显示具体的依赖项
                if dep_count <= 5:  # 如果依赖不多，显示具体依赖
                    for i, dep in enumerate(dep_items[:3]):
                        score_details[f"依赖{i+1}"] = -5
                elif dep_count > 5:  # 依赖太多，只显示前几个
                    for i in range(3):
                        score_details[f"依赖{i+1}"] = -5
                    score_details[f"...等{dep_count}个依赖"] = -(dep_count - 3) * 5
                    
            except Exception as e:
                print(f"解析依赖失败: {e}")
                # 如果解析失败，也视作有依赖，扣基础分
                score_details["依赖解析失败"] = -10
                total_score -= 10
        
        # 2. 被引用次数得分（每被引用1次+5分） - 现在更珍贵了
        author = package.get('author', '')
        package_name = package.get('package_name', '')
        reference_count = self.get_dependency_reference_count(author, package_name)
        if reference_count > 0:
            reference_score = reference_count * self.score_weights["per_reference"]
            score_details[f"被引用{reference_count}次"] = reference_score
            total_score += reference_score
        
        # 3. 标签得分（先计算标签分数，用于判断包类型）
        tags_str = package.get('tags', '')
        has_scene = False
        has_specific_tags = False
        
        # 需要特殊处理的标签组
        specific_tags = ["衣服", "衣服预设", "头发", "头发预设", "皮肤预设", "外观预设"]
        
        if tags_str and tags_str != "无":
            tags = [tag.strip() for tag in tags_str.split(',')]
            
            # 检查是否有场景标签
            if any('场景' in tag for tag in tags):
                has_scene = True
            
            # 检查是否有特定标签
            for tag in tags:
                for specific_tag in specific_tags:
                    if specific_tag in tag:
                        has_specific_tags = True
                        break
            
            # 根据标签权重计算分数
            for tag in tags:
                if tag in self.tag_weights:
                    tag_score = self.tag_weights[tag]
                    score_details[tag] = tag_score
                    total_score += tag_score
                else:
                    # 检查是否有部分匹配
                    for key in self.tag_weights:
                        if key in tag:
                            tag_score = self.tag_weights[key]
                            if tag not in score_details or score_details[tag] < tag_score:
                                score_details[tag] = tag_score
                                total_score += tag_score
        
        # 4. 图片数量得分（根据包类型差异化）
        image_count_str = package.get('images_copied', '0')
        try:
            image_count = int(image_count_str)
            if image_count > 0:
                if has_scene:
                    # 含场景的包：每张图片+10分
                    image_score = image_count * 20
                    total_score+= dep_count*6
                    score_details[f"含场景{image_count}张图片"] = image_score
                elif has_specific_tags:
                    # 含特定标签的包：每张图片+3分
                    image_score = image_count * 3
                    score_details[f"特定类型{image_count}张图片"] = image_score
                else:
                    # 其他类型：每张图片+1分
                    image_score = image_count * self.score_weights["per_image"]
                    score_details[f"{image_count}张图片"] = image_score
                
                total_score += image_score
        except:
            pass
        
        # 保存得分详情
        package['score'] = total_score
        package['score_details'] = score_details
        
        return total_score, score_details

    def get_package_score_details(self, author, package_name, version):
        """获取包的得分详情"""
        for package in self.var_data:
            if (package.get('author') == author and 
                package.get('package_name') == package_name and 
                package.get('version') == version):
                
                # 如果还没有计算过得分，则计算
                if 'score' not in package:
                    score, details = self.calculate_package_score(package)
                
                return {
                    'total_score': package.get('score', 0),
                    'details': package.get('score_details', {}),
                    'reference_count': self.get_dependency_reference_count(author, package_name),
                    'image_count': package.get('images_copied', '0'),
                    'dependency_count': self.get_dependency_count(package.get('dependencies', ''))
                }
        return None





    def initLanguageMenu(self):
        """初始化语言菜单"""
        # 创建菜单栏
        menubar = self.menuBar()
        
        # 语言菜单
        language_menu = menubar.addMenu(self.tr('menu_language'))
        
        # 中文选项
        chinese_action = QAction("简体中文", self)
        chinese_action.triggered.connect(lambda: self.switch_language('zh_CN'))
        language_menu.addAction(chinese_action)
        
        # 英文选项
        english_action = QAction("English", self)
        english_action.triggered.connect(lambda: self.switch_language('en_US'))
        language_menu.addAction(english_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu(self.tr('menu_help'))
        about_action = QAction("关于 / About", self)
        about_action.triggered.connect(self.show_about)

        github_star_action = QAction("在GitHub上点一个星星", self)
        github_star_action.triggered.connect(self.open_github)
        help_menu.addAction(about_action)
        help_menu.addAction(github_star_action)
    
    def switch_language(self, language_code):
        """切换语言"""
        # 保存语言设置
        self.config.set_language(language_code)
        
        # 重新加载语言文件
        self.language_manager.switch_language(language_code)
        
        # 重新设置所有界面文本
        self.retranslateUI()
        
        # 显示提示
        if language_code == 'zh_CN':
            message = "已切换到简体中文"
        else:
            message = "Switched to English"
        
        self.statusBar().showMessage(message, 3000)
    
    def retranslateUI(self):
        """重新翻译所有UI文本"""
        # 设置窗口标题
        self.setWindowTitle(self.tr('window_title'))
        
        # 更新工具栏文本
        self.search_input.setPlaceholderText(self.tr('search_placeholder'))
        self.sort_combo.setItemText(0, self.tr('sort_author'))
        self.sort_combo.setItemText(1, self.tr('sort_package_name'))
        self.sort_combo.setItemText(2, self.tr('sort_image_count'))
        self.sort_combo.setItemText(3, self.tr('sort_dependency_count'))
        self.sort_combo.setItemText(4, self.tr('sort_version'))
        self.sort_combo.setItemText(5, self.tr('sort_reference_count'))
        self.sort_combo.setItemText(6, self.tr('sort_score'))
        self.sort_combo.setItemText(7, self.tr('sort_random'))
        
        # 更新排序按钮文本
        if self.is_random_sort:
            self.sort_order_btn.setText(self.tr('sort_random_direction'))
        elif self.sort_order == Qt.AscendingOrder:
            self.sort_order_btn.setText(self.tr('sort_ascending'))
        else:
            self.sort_order_btn.setText(self.tr('sort_descending'))
        
        # 更新其他按钮文本
        self.random_seed_input.setPrefix(self.tr('random_seed_label'))
        self.refresh_random_btn.setText(self.tr('refresh_random'))
        self.tag_filter_btn.setText(self.tr('tag_filter_btn'))
        self.tag_display_label.setText(self.tr('filter_label'))
        
        # 更新分页控件
        self.prev_page_btn.setText(self.tr('prev_page'))
        self.next_page_btn.setText(self.tr('next_page'))
        self.jump_btn.setText(self.tr('jump_btn'))
        
        # 更新操作按钮
        self.json_deps_checkbox.setText(self.tr('find_json_deps'))
        self.export_select_btn.setText(self.tr('export_select_csv'))
        self.locate_btn.setText(self.tr('locate_package'))
        self.view_selected_btn.setText(self.tr('view_selected'))
        self.view_all_btn.setText(self.tr('view_all'))
        self.extract_btn.setText(self.tr('extract_package'))
        
        # 更新路径按钮
        self.open_scan_btn.setText(self.tr('open_var_dir'))
        self.open_unzip_btn.setText(self.tr('open_unzip_dir'))
        self.open_output_btn.setText(self.tr('open_exe_dir'))
        self.open_person_btn.setText(self.tr('open_person_dir'))
        self.open_scene_btn.setText(self.tr('open_scene_dir'))
        
        # 更新特殊功能按钮
        self.extract_json_btn.setText(self.tr('extract_json_baby'))
        self.json_extractor_btn.setText(self.tr('json_extractor'))
        self.ai_analyze_btn.setText(self.tr('ai_analyze'))
        self.ai_search_input.setPlaceholderText(self.tr('ai_search_placeholder'))
        self.ai_exclude_input.setPlaceholderText(self.tr('ai_exclude_placeholder'))
        self.File_info_input.setPlaceholderText(self.tr('file_info_search'))
        
        # 更新状态栏
        self.update_selected_count()
        self.statusBar().showMessage(self.tr('ready_status'))
        
        # 更新菜单栏
        menubar = self.menuBar()
        for action in menubar.actions():
            if action.text() == "语言" or action.text() == "Language":
                action.setText(self.tr('menu_language'))
            elif action.text() == "帮助" or action.text() == "Help":
                action.setText(self.tr('menu_help'))
    
    def update_selected_count(self):
        """更新选中包数量的显示"""
        count = len(self.selected_packages)
        self.selected_count_label.setText(self.tr('selected_count', count))
    
    def show_about(self):
        """显示关于对话框"""
        about_text = f"""
        Virt-A-Mate Supernova
        
        版本: 1.0
        作者: 荒野79
        
        Virt-A-Mate Supernova是一款空间换时间的var包管理器。本软件的优点是设计思路相对超前，UI界面简单粗暴，功能直接。缺点也是相当明显，软件的上手难度十分之高，操作者需要对计算机软件及系统有相当的认知。软件会占用大量的磁盘空间。故而该软件并非适合所有人。软件功能极为复杂，长达100页的PPT也难以详尽展示，遗漏与表述不清之处在所难免，恳请海涵。本软件绝大部分代码由AI编写。本人对代码没有过多讲究，写得天马行空。
        VAM 2.0尚不知何时到来，但我衷心希望后来者能从这个项目中获得启发。由于时间和精力的关系，本人的开发暂时到此为止。
        大家可以在我的Github上点个星星。
        https://github.com/SONG-ROOT

        谢谢大家！
                                ---------   2026.2.25   荒野79

        """
        
        QMessageBox.about(self, "关于 / About", about_text)

    def load_analysis_data(self):
        """加载var_analysis_results.csv文件"""
        if not os.path.exists(self.analysis_csv_file):
            print(f"分析结果文件不存在: {self.analysis_csv_file}")
            return
        
        try:
            with open(self.analysis_csv_file, 'r', encoding='gb18030') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    filename = row.get('filename', '')
                    tags_str = row.get('tags', '')
                    
                    if filename and tags_str:
                        # 移除.var扩展名
                        if filename.endswith('.var'):
                            pkg_identifier = filename[:-4]  # 移除.var
                        else:
                            pkg_identifier = filename
                        
                        # 解析tags
                        tags = [tag.strip() for tag in tags_str.split('.') if tag.strip()]
                        
                        # 存储数据
                        self.analysis_data[pkg_identifier] = {
                            'tags': tags,
                            'creation_date': row.get('creation_date', '')
                        }
                        
                        # 收集所有分析标签
                        for tag in tags:
                            self.analysis_tags.add(tag)
            
            print(f"已加载 {len(self.analysis_data)} 条分析记录，共 {len(self.analysis_tags)} 个分析标签")
            
        except Exception as e:
            print(f"加载分析结果文件失败: {e}")




















    # 7 advanced_package_grabber.py
    def open_analysis_filter(self):
        """打开分析标签筛选对话框"""
        if not self.analysis_tags:
            QMessageBox.information(self, "提示", "没有可筛选的分析标签")
            return
        
        dialog = AnalysisTagFilterDialog(
            self.analysis_tags, 
            self.selected_analysis_tags, 
            self.exclude_analysis_tags, 
            self
        )
        
        if dialog.exec_() == QDialog.Accepted:
            self.selected_analysis_tags = dialog.get_selected_tags()
            self.exclude_analysis_tags = dialog.get_exclude_tags()
            self.update_analysis_display()
            self.filter_and_display()

    def clear_analysis_filters(self):
        """清除分析标签筛选"""
        self.selected_analysis_tags.clear()
        self.exclude_analysis_tags.clear()
        self.update_analysis_display()

    def update_analysis_display(self):
        """更新分析标签筛选显示"""
        display_texts = []
        
        if self.selected_analysis_tags:
            include_text = ",".join(sorted(self.selected_analysis_tags))
            if len(include_text) > 30:
                include_text = include_text[:27] + "..."
            display_texts.append(f"包含: {include_text}")
        
        if self.exclude_analysis_tags:
            exclude_text = ",".join(sorted(self.exclude_analysis_tags))
            if len(exclude_text) > 30:
                exclude_text = exclude_text[:27] + "..."
            display_texts.append(f"排除: {exclude_text}")
        
        if display_texts:
            display_text = " | ".join(display_texts)
            self.analysis_display_label.setText(f"自动分类: {display_text}")
        else:
            self.analysis_display_label.setText("自动分类: 无")

    def clear_filters(self):
        """清除所有筛选（原有方法更新）"""
        self.search_input.clear()
        self.filter_tags.clear()
        self.exclude_tags.clear()
        self.ai_search_input.clear()
        self.ai_exclude_input.clear()
        self.File_info_input.clear()
        
        # 清除分析标签筛选
        self.clear_analysis_filters()
        
        # 更新显示
        self.update_tag_display()
        self.filter_and_display()










    # 日期相关
    def format_analysis_text(self, tags):
        """格式化分析标签显示文本"""
        if not tags:
            return "无分析类别"
        
        if len(tags) <= 3:
            return " • ".join(tags)
        else:
            return " • ".join(tags[:3]) + " • ..."    
    def get_package_creation_date(self, package):
        """获取包的创建日期"""
        author = package.get('author', '')
        package_name = package.get('package_name', '')
        version = package.get('version', '')
        
        # 构建包标识符
        pkg_identifier = f"{author}.{package_name}.{version}"
        
        # 从分析数据中获取创建日期
        if pkg_identifier in self.analysis_data:
            date_str = self.analysis_data[pkg_identifier].get('creation_date', '')
            return date_str
        
        return ""
    def parse_creation_date(self, date_str):
        """解析创建日期字符串为可排序的日期对象"""
        if not date_str or date_str.strip() == "":
            return datetime.min  # 返回最小日期作为默认值
        
        try:
            # 支持的日期格式
            date_formats = [
                '%Y-%m-%d %H:%M:%S',  # 2023-07-29 22:05:58
                '%Y/%m/%d %H:%M:%S',  # 2023/07/29 22:05:58
                '%Y-%m-%d',           # 2023-07-29
                '%Y/%m/%d',           # 2023/07/29
                '%Y年%m月%d日',        # 2023年07月29日
            ]
            
            # 尝试各种格式
            date_str_clean = date_str.strip()
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str_clean, fmt)
                except ValueError:
                    continue
            
            # 尝试提取日期部分
            import re
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
            if date_match:
                try:
                    return datetime.strptime(date_match.group(), '%Y-%m-%d')
                except:
                    pass
            
            # 返回最小日期
            return datetime.min
            
        except Exception as e:
            print(f"解析日期失败: {date_str}, 错误: {e}")
            return datetime.min

    def parse_processed_time(self, time_str):
        """解析处理时间字符串"""
        if not time_str or time_str.strip() == "":
            # 如果没有处理时间，返回最小时间值
            return datetime.min
        
        try:
            # processed_time 可能的格式：
            # 1. 完整日期时间格式：2024-01-15 14:30:25
            # 2. 只包含日期：2024-01-15
            # 3. 其他格式...
            # 尝试常见的时间格式
            time_formats = [
                '%Y-%m-%d %H:%M:%S',  # 2024-01-15 14:30:25
                # '%Y/%m/%d %H:%M:%S',  # 2024/01/15 14:30:25
                # '%Y-%m-%d',           # 2024-01-15
                # '%Y/%m/%d',           # 2024/01/15
                # '%Y%m%d%H%M%S',       # 20240115143025
            ]
            
            time_str_clean = time_str.strip()
            
            for fmt in time_formats:
                try:
                    return datetime.strptime(time_str_clean, fmt)
                except ValueError:
                    continue
            
            # 如果都无法解析，尝试其他可能的格式
            # 移除可能的时区信息
            if 'T' in time_str_clean:
                try:
                    # ISO格式：2024-01-15T14:30:25
                    iso_str = time_str_clean.split('T')[0] + ' ' + time_str_clean.split('T')[1].split('+')[0]
                    return datetime.strptime(iso_str, '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            # 如果还是无法解析，尝试提取日期部分
            import re
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', time_str_clean)
            if date_match:
                try:
                    return datetime.strptime(date_match.group(), '%Y-%m-%d')
                except:
                    pass
            
            # 如果所有尝试都失败，返回最小时间值
            print(f"无法解析处理时间: {time_str}")
            return datetime.min
            
        except Exception as e:
            print(f"解析处理时间失败: {time_str}, 错误: {e}")
            return datetime.min
    








    def open_dependency_details_window(self, parent_dialog):
        """打开独立的依赖详情窗口（PLUS版本）- 在一个窗口中显示所有选中的依赖包"""
        
        if not hasattr(self, 'dependency_list_widget'):
            return
        
        selected_items = self.dependency_list_widget.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(parent_dialog, "提示", "请先选择要查看的依赖包")
            return
        
        # ========== 收集所有选中的依赖包信息 ==========
        dependencies_info = []
        
        for item in selected_items:
            dep = item.data(Qt.UserRole)
            if not dep:
                continue
            
            # 查找这个依赖包的完整信息
            for package in self.var_data:
                if (package.get('author') == dep['author'] and 
                    package.get('package_name') == dep['package_name']):
                    
                    # 获取实际版本
                    if dep['version'].lower() == 'latest':
                        actual_version = package.get('version', '')
                    else:
                        actual_version = dep['version']
                    
                    # 获取依赖字符串
                    dependencies_str = package.get('dependencies', '')
                    
                    dependencies_info.append({
                        'author': dep['author'],
                        'package_name': dep['package_name'],
                        'version': actual_version,
                        'dependencies_str': dependencies_str,
                        'filename': f"{dep['author']}.{dep['package_name']}.{actual_version}.var",
                        'tags': package.get('tags', ''),
                        'images_copied': package.get('images_copied', '0'),
                        'processed_time': package.get('processed_time', '')
                    })
                    break
        
        if not dependencies_info:
            QMessageBox.warning(parent_dialog, "错误", "未找到任何有效的依赖包信息")
            return
        
        # 关闭父对话框
        parent_dialog.accept()
        
        # ========== 创建临时CSV文件，包含所有选中的依赖包 ==========
        try:
            with open("tmp_selectedcsv.csv", 'w', newline='', encoding='gb18030') as f:
                fieldnames = ['filename', 'author', 'package_name', 'version', 
                             'dependencies', 'tags', 'images_copied', 'processed_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                
                for info in dependencies_info:
                    package_data = {
                        'filename': info['filename'],
                        'author': info['author'],
                        'package_name': info['package_name'],
                        'version': info['version'],
                        'dependencies': info['dependencies_str'] if info['dependencies_str'] else '无依赖',
                        'tags': info.get('tags', ''),
                        'images_copied': info.get('images_copied', '0'),
                        'processed_time': info.get('processed_time', '')
                    }
                    writer.writerow(package_data)
            
            print(f"已创建临时CSV文件，包含 {len(dependencies_info)} 个包")
            
        except Exception as e:
            QMessageBox.critical(parent_dialog, "错误", f"创建临时CSV文件失败: {e}")
            return
        
        # ========== 创建单个窗口，显示所有选中的依赖包 ==========
        # 为了在一个窗口中显示多个包，我们使用第一个包的信息创建窗口
        # 但通过设置一个标志来加载所有包的数据
        first_info = dependencies_info[0]
        
        dep_window = DependencyDetailsWindow(
            first_info['author'],
            first_info['package_name'],
            first_info['version'],
            first_info['dependencies_str'],
            self  # 传入父窗口引用
        )
        
        # 设置窗口标题，显示包的数量
        if len(dependencies_info) == 1:
            dep_window.setWindowTitle(f"依赖详情 - {first_info['author']}.{first_info['package_name']}.{first_info['version']}")
        else:
            dep_window.setWindowTitle(f"依赖详情 - 已选择 {len(dependencies_info)} 个包")
        
        # 设置多包模式
        dep_window.view_mode = "multi_package"
        dep_window.multi_package_data = dependencies_info
        
        # 重新加载所有包的数据
        dep_window.load_multi_package_data(dependencies_info)
        
        # 显示窗口
        dep_window.show()
    
    def open_references_details_window(self, parent_dialog):
        """打开独立的引用详情窗口（PLUS版本）- 在一个窗口中显示所有选中的引用包"""
        
        if not hasattr(self, 'reference_list_widget'):
            return
        
        selected_items = self.reference_list_widget.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(parent_dialog, "提示", "请先选择要查看的引用包")
            return
        
        # ========== 收集所有选中的引用包信息 ==========
        references_info = []
        
        for item in selected_items:
            row = self.reference_list_widget.row(item)
            if row < len(self.reference_package_data):
                package = self.reference_package_data[row]
                
                # 获取包的完整信息
                author = package.get('author', '')
                package_name = package.get('package_name', '')
                version = package.get('version', '')
                
                # 获取依赖字符串
                dependencies_str = package.get('dependencies', '')
                
                references_info.append({
                    'author': author,
                    'package_name': package_name,
                    'version': version,
                    'dependencies_str': dependencies_str,
                    'filename': f"{author}.{package_name}.{version}.var",
                    'tags': package.get('tags', ''),
                    'images_copied': package.get('images_copied', '0'),
                    'processed_time': package.get('processed_time', '')
                })
        
        if not references_info:
            QMessageBox.warning(parent_dialog, "错误", "未找到任何有效的引用包信息")
            return
        
        # 关闭父对话框
        parent_dialog.accept()
        
        # ========== 创建临时CSV文件，包含所有选中的引用包 ==========
        try:
            with open("tmp_selectedcsv.csv", 'w', newline='', encoding='gb18030') as f:
                fieldnames = ['filename', 'author', 'package_name', 'version', 
                             'dependencies', 'tags', 'images_copied', 'processed_time']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                
                for info in references_info:
                    package_data = {
                        'filename': info['filename'],
                        'author': info['author'],
                        'package_name': info['package_name'],
                        'version': info['version'],
                        'dependencies': info['dependencies_str'] if info['dependencies_str'] else '无依赖',
                        'tags': info.get('tags', ''),
                        'images_copied': info.get('images_copied', '0'),
                        'processed_time': info.get('processed_time', '')
                    }
                    writer.writerow(package_data)
            
            print(f"已创建临时CSV文件，包含 {len(references_info)} 个引用包")
            
        except Exception as e:
            QMessageBox.critical(parent_dialog, "错误", f"创建临时CSV文件失败: {e}")
            return
        
        # ========== 创建单个窗口，显示所有选中的引用包 ==========
        first_info = references_info[0]
        
        dep_window = DependencyDetailsWindow(
            first_info['author'],
            first_info['package_name'],
            first_info['version'],
            first_info['dependencies_str'],
            self
        )
        
        # 设置窗口标题
        if len(references_info) == 1:
            dep_window.setWindowTitle(f"引用详情 - {first_info['author']}.{first_info['package_name']}.{first_info['version']}")
        else:
            dep_window.setWindowTitle(f"引用详情 - 已选择 {len(references_info)} 个包")
        
        # 设置多包模式
        dep_window.view_mode = "multi_package"
        dep_window.multi_package_data = references_info
        
        # 重新加载所有包的数据
        dep_window.load_multi_package_data(references_info)
        
        # 显示窗口
        dep_window.show()

    def extract_Animation_from_scenes(self):
        for filename_short in self.selected_packages:
            # 构建可能的场景目录路径
            scene_dir = os.path.join(self.unzip_base_dir,filename_short, "Saves", "scene")

            found_files = []
            # print(scene_dir)
            # 使用os.walk递归查找json
            for root, dirs, files in os.walk(scene_dir):
                for file in files:
                    if file.endswith('.json'):
                        full_path = os.path.join(root, file)
                        found_files.append(full_path)
            # print(found_files)
            if found_files:
                count = 0
                for j, file_path in enumerate(found_files):
                    file_size = os.path.getsize(file_path)
                    print(f"     - {file_path} ({ round(file_size/(1024*1024),3)} mbytes)")
                    person_id = []
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            # file_content = f.read()
                            data = json.load(f) # json加载缓慢,但是先这样试试。
                            atoms = data.get("atoms")
                            # 把人物加进来早说,其他的不关注
                            for atom_idx, atom in enumerate(atoms):
                                if atom.get("type") == "Person":
                                    # for  i in atom:
                                    #     pprint(i)
                                    person_id.append(atom)
                                else:
                                    # print(atom)
                                    pass
                    except Exception as e:
                        # raise
                        print(f"       读取文件出错: {e}")

                    # 写入文件
                    try:
                        with open( "empty_scene.json", 'r', encoding='utf-8') as gh:
                            empty_scene = json.load(gh)
                        for j in person_id:
                            empty_scene["atoms"].append(j)
                        os.makedirs(os.path.join(self.output_base_dir, "Saves", "scene","Auto_Gen_Jsons"),exist_ok=True)
                        with open(os.path.join(self.output_base_dir, "Saves", "scene","Auto_Gen_Jsons", f"{filename_short}_No.{count}.json"), 'w', encoding='utf-8') as f:
                            json.dump(empty_scene, f, ensure_ascii=False, indent=2)  # 使用 json.dump 直接写入文件

                        count += 1
                    except Exception as e:
                        # raise
                        print(f"       读取文件出错: {e}")

    def extract_Animation_from_scenes_Tset(self):
        # def parse_vam_float_with_sign(hex_str):
        #     # print(len(hex_str))
        #     """
        #     正确解析VAM浮点数，包括负数
        #     """
        #     # 提取8位十六进制
        #     hex_match = re.search(r'[0-9A-Fa-f]{8}', hex_str)
        #     if not hex_match:
        #         return None
            
        #     hex_data = hex_match.group()
        #     # 转为字节
        #     byte_data = binascii.unhexlify(hex_data)
        #     # 小端序解析
        #     value = struct.unpack('<f', byte_data)[0]
        #     return value

        # # 测试一些数据
        # test_data = [
        #     "BA3DAB3F",  # 应该是负数
        #     "C83DAB3F",
        #     "7D3BAB3F",
        #     "C039AB3F",
        # ]

        # for hex_str in test_data:
        #     val = parse_vam_float_with_sign(hex_str)
        #     print(f"0x{hex_str} -> {val:.6f}")

        # def format_animation_data(controller_data):
        #     # 解析各个轴的数据
        #     axes = ['X', 'Y', 'Z', 'RotX', 'RotY', 'RotZ', 'RotW']
        #     for axis in axes:
        #         print(len(controller_data[axis]))
        #         if axis in controller_data:
        #             raw_data = controller_data[axis]
        #             # print(raw_data)
        #             parsed = parse_vam_float_data(raw_data)
        #             print(parsed)
        #     #         result['data'][axis] = {
        #     #             'parsed': parsed,
        #     #             'count': len(parsed),
        #     #             'range': (min(parsed) if parsed else 0, max(parsed) if parsed else 0)
        #     #         }
            
        #     return result

        # for filename_short in self.selected_packages:
        #     # 构建可能的场景目录路径
        #     scene_dir = os.path.join(self.unzip_base_dir,filename_short, "Saves", "scene")

        #     found_files = []
        #     # print(scene_dir)
        #     # 使用os.walk递归查找json
        #     for root, dirs, files in os.walk(scene_dir):
        #         for file in files:
        #             if file.endswith('.json'):
        #                 full_path = os.path.join(root, file)
        #                 found_files.append(full_path)
        #     # print(found_files)
        #     if found_files:
        #         count = 0
        #         for j, file_path in enumerate(found_files):
        #             file_size = os.path.getsize(file_path)
        #             print(f"     - {file_path} ({ round(file_size/(1024*1024),3)} mbytes)")
        #             person_id = []
        #             try:
        #                 with open(file_path, 'r', encoding='utf-8') as f:
        #                     # file_content = f.read()
        #                     data = json.load(f) # json加载缓慢,但是先这样试试。
        #                     atoms = data.get("atoms")
        #                     # 把人物加进来早说,其他的不关注
        #                     for atom_idx, atom in enumerate(atoms):
        #                         if atom.get("type") == "Person":
        #                             # for i in atom:
        #                             #     pprint(i)

        #                             # 配方1 timeline.282
        #                             storables = atom.get("storables")
        #                             for ii in storables:
        #                                 if "VamTimeline.AtomPlugin" in ii["id"]:
        #                                     animations = ii['Animation']["Clips"]
        #                                     # 依次的。单个 animation
        #                                     for jgg in animations:
        #                                         AnimationName = jgg['AnimationName']
        #                                         Controllers = jgg['Controllers']
        #                                         # clip_data = {
        #                                         #     'name': jgg.get('name', f'Clip_{clip_index}'),
        #                                         #     'controllers': []
        #                                         # }
        #                                         for jjjj in Controllers:
        #                                             # 控制身体部位的动画
        #                                             Controller_name = jjjj['Controller']
        #                                             print(AnimationName,Controller_name)
        #                                             # X = jjjj["X"]
        #                                             # Y = jjjj["Y"]
        #                                             # Z = jjjj["Z"]
        #                                             # RotX = jjjj["RotX"]
        #                                             # RotY = jjjj["RotY"]
        #                                             # RotZ = jjjj["RotZ"]
        #                                             # RotW = jjjj["RotW"]
        #                                             controller_info = format_animation_data(jjjj)
        #                                             print(controller_info)



        #                             person_id.append(atom)
        #                         else:
        #                             # print(atom)
        #                             pass
        #             except Exception as e:
        #                 # raise
        #                 print(f"       读取文件出错: {e}")
                    # 研究失败,不做这个功能了
        for filename_short in self.selected_packages:
            # 构建可能的场景目录路径
            scene_dir = os.path.join(self.unzip_base_dir,filename_short, "Saves", "scene")

            found_files = []
            # print(scene_dir)
            # 使用os.walk递归查找json
            for root, dirs, files in os.walk(scene_dir):
                for file in files:
                    if file.endswith('.json'):
                        full_path = os.path.join(root, file)
                        target_dir = os.path.join(self.output_base_dir, "Saves", "scene", "Auto_Gen_Jsons")
                        os.makedirs(target_dir, exist_ok=True)
                        target_path = os.path.join(target_dir, file)
                        shutil.copy(full_path, target_path)

    def open_github(self):
        webbrowser.open("https://github.com/SONG-ROOT")






























































# 定位3

class DependencyDetailsWindow(VARManager):
    """依赖详情窗口 - 独立显示，支持单包和多包模式"""
    
    def __init__(self, author, package_name, version, dependencies_str, parent=None):
        # 设置CSV文件路径为临时文件
        # self.csv_file = "tmp_selectedcsv.csv"
        
        # 先调用父类的__init__方法
        super().__init__()

        # 保存包信息
        self.target_author = author
        self.target_package_name = package_name
        self.target_version = version
        self.target_dependencies_str = dependencies_str
        
        # 设置视图模式
        self.view_mode = "single_package"  # 默认单包模式
        self.multi_package_data = []
        
        # 设置窗口标题（稍后可能会被覆盖）
        self.setWindowTitle(f"依赖和引用查看窗口 - {author}.{package_name}.{version}")
    
    def initUI(self):
        self.setGeometry(0, 0, self.config.get_window_size()[0], self.config.get_window_size()[1]-150)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        # ====== 创建工具栏容器 ======
        toolbar_container = QVBoxLayout()
        # ====== 第一行工具栏：搜索、筛选、排序 ======
        # 改为使用QWidget容器实现居中布局
        toolbar_row1_widget = QWidget()
        toolbar_row1_layout = QHBoxLayout(toolbar_row1_widget)
        toolbar_row1_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_row1_layout.setSpacing(10)
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索包名、作者或标签...')
        self.search_input.textChanged.connect(self.filter_and_display)
        self.search_input.setMaximumWidth(200)
        toolbar_row1_layout.addWidget(self.search_input)
        # 分隔符
        toolbar_row1_layout.addWidget(self.create_vertical_line())
        # 排序控件组
        toolbar_row1_layout.addWidget(QLabel("排序:"))
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["作者", "包名" , "图片数量", "依赖数量", "版本号","被引用次数", "随机排序", "得分","创建日期", "处理时间"])
        self.sort_combo.setCurrentText("作者")
        self.sort_combo.currentTextChanged.connect(self.change_sort_criteria)
        self.sort_combo.setMaximumWidth(100)
        toolbar_row1_layout.addWidget(self.sort_combo)
        
        self.sort_order_btn = QToolButton()
        self.sort_order_btn.setText("升序")
        self.sort_order_btn.setCheckable(False)
        self.sort_order_btn.clicked.connect(self.toggle_sort_order)
        self.sort_order_btn.setMaximumWidth(60)
        toolbar_row1_layout.addWidget(self.sort_order_btn)
        
        # 随机种子控件
        toolbar_row1_layout.addWidget(self.create_vertical_line())
        toolbar_row1_layout.addWidget(QLabel("随机种子:"))
        
        self.random_seed_input = QSpinBox()
        self.random_seed_input.setRange(0, 999999999)
        self.random_seed_input.setValue(0)
        self.random_seed_input.setEnabled(False)
        self.random_seed_input.valueChanged.connect(self.change_random_seed)
        self.random_seed_input.setMaximumWidth(100)
        toolbar_row1_layout.addWidget(self.random_seed_input)
        
        self.refresh_random_btn = QToolButton()
        self.refresh_random_btn.setText("刷新随机")
        self.refresh_random_btn.setEnabled(False)
        self.refresh_random_btn.clicked.connect(self.refresh_random_sort)
        self.refresh_random_btn.setMaximumWidth(100)
        toolbar_row1_layout.addWidget(self.refresh_random_btn)
        
        # 标签筛选控件
        toolbar_row1_layout.addWidget(self.create_vertical_line())
        # 右侧弹性空间
        toolbar_row1_layout.addStretch()

        # 在标签筛选按钮附近添加
        self.analysis_filter_btn = QToolButton()
        self.analysis_filter_btn.setText("自动包分类")
        self.analysis_filter_btn.clicked.connect(self.open_analysis_filter)
        self.analysis_filter_btn.setStyleSheet("""
            QToolButton {
                background-color: #6610f2;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #590bd1;
            }
        """)
        toolbar_row1_layout.addWidget(self.analysis_filter_btn)
        self.analysis_display_label = QLabel("自动分类: 无")
        self.analysis_display_label.setStyleSheet("color: #6610f2; font-weight: bold; padding: 0 5px;")
        toolbar_row1_layout.addWidget(self.analysis_display_label)

        

        self.tag_filter_btn = QToolButton()
        self.tag_filter_btn.setText("标签筛选")
        self.tag_filter_btn.clicked.connect(self.open_tag_filter)
        self.tag_filter_btn.setStyleSheet("""
            QToolButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #218838;
            }
        """)
        toolbar_row1_layout.addWidget(self.tag_filter_btn)
        
        self.tag_display_label = QLabel("筛选: 无")
        self.tag_display_label.setStyleSheet("color: #0078d7; font-weight: bold; padding: 0 5px;")
        toolbar_row1_layout.addWidget(self.tag_display_label)
        
        clear_filter_btn = QToolButton()
        clear_filter_btn.setText("清除筛选")
        clear_filter_btn.clicked.connect(self.clear_filters)
        # 清除筛选按钮也添加对7 advanced_package_grabber.py 的支持
        clear_filter_btn.clicked.connect(lambda: (self.clear_filters(), self.clear_analysis_filters()))

        toolbar_row1_layout.addWidget(clear_filter_btn)

        select_all_btn = QToolButton()
        select_all_btn.setText("全选当前页")
        select_all_btn.clicked.connect(self.select_all_current_page)
        toolbar_row1_layout.addWidget(select_all_btn)
        
        clear_selection_btn = QToolButton()
        clear_selection_btn.setText("清除选择")
        clear_selection_btn.clicked.connect(self.clear_selection)
        toolbar_row1_layout.addWidget(clear_selection_btn)

















        # 添加标签按钮组（居中区域）
        tag_buttons_container = QWidget()
        tag_buttons_layout = QHBoxLayout(tag_buttons_container)
        tag_buttons_layout.setSpacing(5)
        tag_buttons_layout.setContentsMargins(0, 0, 0, 0)

        # 添加弹性空间使内容居中
        toolbar_row1_layout.addStretch()

        self.add_tag_btn = QToolButton()
        self.batch_add_tag_btn = QToolButton()
        self.batch_remove_tag_btn = QToolButton()
        
        # 右侧弹性空间
        toolbar_row1_layout.addStretch()
        
        # ====== 第二行工具栏：分页、操作、显示控制 ======
        toolbar_row2_widget = QWidget()
        toolbar_row2_layout = QHBoxLayout(toolbar_row2_widget)
        toolbar_row2_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_row2_layout.setSpacing(10)
        
        # 分页控件组（左对齐）
        page_container = QWidget()
        page_layout = QHBoxLayout(page_container)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(5)
        
        self.prev_page_btn = QToolButton()
        self.prev_page_btn.setText("◀ 上一页")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.prev_page_btn.setEnabled(False)
        page_layout.addWidget(self.prev_page_btn)
        
        self.page_label = QLabel("第 1 页")
        self.page_label.setStyleSheet("font-weight: bold; padding: 0 10px;")
        page_layout.addWidget(self.page_label)
        
        self.next_page_btn = QToolButton()
        self.next_page_btn.setText("下一页 ▶")
        self.next_page_btn.clicked.connect(self.next_page)
        self.next_page_btn.setEnabled(False)
        page_layout.addWidget(self.next_page_btn)
        
        toolbar_row2_layout.addWidget(page_container)
        toolbar_row2_layout.addWidget(self.create_vertical_line())
        toolbar_row2_layout.addWidget(QLabel("跳到:"))
        
        self.page_input = QSpinBox()
        self.page_input.setMinimum(1)
        self.page_input.setMaximum(9999)
        self.page_input.setValue(1)
        self.page_input.setMaximumWidth(70)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.setStyleSheet("""
            QSpinBox {
                padding: 4px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
        toolbar_row2_layout.addWidget(self.page_input)
        
        self.jump_btn = QToolButton()
        self.jump_btn.setText("跳转")
        self.jump_btn.clicked.connect(self.jump_to_page)
        self.jump_btn.setStyleSheet("""
            QToolButton {
                background-color: #0078d7;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #0056b3;
            }
        """)
        toolbar_row2_layout.addWidget(self.jump_btn)

        # 操作按钮组（居中）
        toolbar_row2_layout.addStretch()
        
        operation_container = QWidget()
        operation_layout = QHBoxLayout(operation_container)
        operation_layout.setContentsMargins(0, 0, 0, 0)
        operation_layout.setSpacing(5)
        
        # 添加JSON依赖复选框
        # self.json_deps_checkbox = QCheckBox("导出选中CSV时,从所有包的JSON寻找依赖。")
        self.json_deps_checkbox = QCheckBox("从JSON寻找依赖")
        self.json_deps_checkbox.setChecked(self.include_json_deps)
        self.json_deps_checkbox.setToolTip("导出选中CSV时,讲从所有包的JSON寻找依赖。")
        operation_layout.addWidget(self.json_deps_checkbox)

        self.export_select_btn = QToolButton()
        self.export_select_btn.setText("导出选中CSV")
        self.export_select_btn.setToolTip("导出选中的CSV并添加符号链接库")
        self.export_select_btn.setStyleSheet("""
            QToolButton {
                background-color: #ffc107;
                color: #212529;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e0a800;
            }
        """)
        self.export_select_btn.clicked.connect(self.export_select_csv)
        operation_layout.addWidget(self.export_select_btn)
        
        self.locate_btn = QToolButton()
        self.locate_btn.setText("定位包目录")
        self.locate_btn.setToolTip("一键定位选中的包目录")
        self.locate_btn.setStyleSheet("""
            QToolButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #138496;
            }
        """)
        self.locate_btn.clicked.connect(self.locate_selected_package)
        operation_layout.addWidget(self.locate_btn)
        
        self.view_selected_btn = QToolButton()
        self.view_selected_btn.setText("查看选中包")
        self.view_selected_btn.setStyleSheet("""
            QToolButton {
                background-color: #6610f2;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #590bd1;
            }
        """)
        self.view_selected_btn.clicked.connect(self.view_selected_packages)
        operation_layout.addWidget(self.view_selected_btn)
        
        self.view_all_btn = QToolButton()
        self.view_all_btn.setText("查看全部包")
        self.view_all_btn.setStyleSheet("""
            QToolButton {
                background-color: #6c757d;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #5a6268;
            }
        """)
        self.view_all_btn.clicked.connect(self.view_all_packages)
        operation_layout.addWidget(self.view_all_btn)
        
        self.extract_btn = QToolButton()
        self.extract_btn.setText("提取包信息")
        self.extract_btn.setToolTip("提取选中VAR包信息")
        self.extract_btn.setStyleSheet("""
            QToolButton {
                background-color: #fd7e14;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e66a1c;
            }
        """)
        self.extract_btn.clicked.connect(self.extract_selected_var_info)
        operation_layout.addWidget(self.extract_btn)
        
        toolbar_row2_layout.addWidget(operation_container)
        
        # 大小控制（右对齐）
        toolbar_row2_layout.addStretch()
        
        size_container = QWidget()
        size_layout = QHBoxLayout(size_container)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(5)
        
        size_layout.addWidget(QLabel("大小:"))
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(100, 3000)
        self.size_slider.setValue(self.current_thumbnail_size)
        self.size_slider.valueChanged.connect(self.change_thumbnail_size)
        self.size_slider.setMaximumWidth(150)
        size_layout.addWidget(self.size_slider)
        
        self.size_label = QLabel(f"{self.current_thumbnail_size}px")
        self.size_label.setMinimumWidth(50)
        size_layout.addWidget(self.size_label)
        
        toolbar_row2_layout.addWidget(size_container)
        toolbar_row2_layout.addWidget(self.create_vertical_line())
        
        # 选择操作按钮（最右侧）
        selection_container = QWidget()
        selection_layout = QHBoxLayout(selection_container)
        selection_layout.setContentsMargins(0, 0, 0, 0)
        selection_layout.setSpacing(5)
        
        
    
        








        # 测试按钮 - 修改为三个特定路径按钮        
        toolbar_row3_widget = QWidget()
        toolbar_row3_layout = QHBoxLayout(toolbar_row3_widget)
        toolbar_row3_layout.setContentsMargins(1, 1, 1, 1)
        toolbar_row3_layout.setSpacing(1)

        # 按钮1: 打开VAR扫描目录
        self.open_scan_btn = QToolButton()
        self.open_scan_btn.setText("打开VAR目录")
        self.open_scan_btn.setStyleSheet("""
            QToolButton {
                background-color: #0078d7;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #0056b3;
            }
        """)
        self.open_scan_btn.clicked.connect(lambda: self.open_specific_path(self.var_scan_dir))
        self.open_scan_btn.setToolTip(f"打开: {self.var_scan_dir}")
        toolbar_row3_layout.addWidget(self.open_scan_btn)
        
        # 按钮2: 打开解压目录
        self.open_unzip_btn = QToolButton()
        self.open_unzip_btn.setText("打开解压目录")
        self.open_unzip_btn.setStyleSheet("""
            QToolButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #218838;
            }
        """)
        self.open_unzip_btn.clicked.connect(lambda: self.open_specific_path(self.unzip_base_dir))
        self.open_unzip_btn.setToolTip(f"打开: {self.unzip_base_dir}")
        toolbar_row3_layout.addWidget(self.open_unzip_btn)
        
        # 按钮3: 打开输=exe目录
        self.open_output_btn = QToolButton()
        self.open_output_btn.setText("打开exe目录")
        self.open_output_btn.setStyleSheet("""
            QToolButton {
                background-color: #fd7e14;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e66a1c;
            }
        """)
        self.open_output_btn.clicked.connect(lambda: self.open_specific_path(self.output_base_dir))
        self.open_output_btn.setToolTip(f"打开: {self.output_base_dir}")
        toolbar_row3_layout.addWidget(self.open_output_btn)
        
        # 按钮4: 打开person目录
        self.open_person_btn = QToolButton()
        self.open_person_btn.setText("打开person目录")
        self.open_person_btn.setStyleSheet("""
            QToolButton {
                background-color: #fd7e14;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e66a1c;
            }
        """)
        self.open_person_btn.clicked.connect(lambda: self.open_specific_path( os.path.join(self.output_base_dir,"Custom","Atom","Person") ))
        toolbar_row3_layout.addWidget(self.open_person_btn)

        # 按钮5: 打开 scene 目录
        self.open_scene_btn = QToolButton()
        self.open_scene_btn.setText("打开scene目录")
        self.open_scene_btn.setStyleSheet("""
            QToolButton {
                background-color: #fd7e14;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #e66a1c;
            }
        """)
        self.open_scene_btn.clicked.connect(lambda: self.open_specific_path( os.path.join(self.output_base_dir,"Saves","scene") ))
        toolbar_row3_layout.addWidget(self.open_scene_btn)

        # 按钮6: 打开 pkg_tmp 目录
        self.open_pkg_tmp_btn = QToolButton()
        self.open_pkg_tmp_btn.setText("打开 pkg_tmp 目录")
        self.open_pkg_tmp_btn.clicked.connect(lambda: self.open_specific_path( os.path.join(self.output_base_dir,"pkg_tmp") ))
        toolbar_row3_layout.addWidget(self.open_pkg_tmp_btn)

        # +++ 新增：JSON宝贝提取按钮 +++
        self.extract_json_btn = QToolButton()
        self.extract_json_btn.setText("提取JSON中的人物")
        self.extract_json_btn.setToolTip("提取选中包中的JSON宝贝")
        self.extract_json_btn.setStyleSheet("""
            QToolButton {
                background-color: #e83e8c;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #d63384;
            }
        """)
        self.extract_json_btn.clicked.connect(self.extract_json_baby)
        toolbar_row3_layout.addWidget(self.extract_json_btn)
        
        # +++ 新增：依赖补全 +++
        self.json_extractor_btn = QToolButton()
        self.json_extractor_btn.setText("从json查看某个包的依赖,并从hub补全")
        self.json_extractor_btn.setStyleSheet("""
            QToolButton {
                background-color: #e83e8c;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #d63384;
            }
        """)
        self.json_extractor_btn.clicked.connect(self.extract_json)
        toolbar_row3_layout.addWidget(self.json_extractor_btn)





        # ====== 添加工具栏到容器 ======
        toolbar_row4_widget = QWidget()
        toolbar_row4_layout = QHBoxLayout(toolbar_row4_widget)
        toolbar_row4_layout.setContentsMargins(1, 1, 1, 1)
        toolbar_row4_layout.setSpacing(1)

        toolbar_container.addWidget(toolbar_row1_widget)
        toolbar_container.addWidget(toolbar_row2_widget)
        toolbar_container.addWidget(toolbar_row3_widget)
        toolbar_container.addWidget(toolbar_row4_widget)
        main_layout.addLayout(toolbar_container)
        
        # ====== 滚动区域（保持原有） ======
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.container_widget = QWidget()
        self.container_widget.setStyleSheet(f"* {{ background-color: {self.config.get_back_ground_color()}; }}")
        self.grid_layout = QGridLayout(self.container_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        
        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area)

        

        # +++ 新增：AI分析按钮 +++

        self.ai_analyze_btn = QToolButton()
        self.ai_analyze_btn.setText("AI包分析")
        self.ai_analyze_btn.setToolTip("使用AI分析选中的包")
        self.ai_analyze_btn.setStyleSheet("""
            QToolButton {
                background-color: #6f42c1;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #5a32a3;
            }
        """)
        self.ai_analyze_btn.clicked.connect(self.open_ai_analyzer)
        toolbar_row4_layout.addWidget(self.ai_analyze_btn)


        # +++ 新增：AI特征搜索框 +++
        self.ai_search_input = QLineEdit()
        self.ai_search_input.setPlaceholderText('搜索AI特征描述...')
        self.ai_search_input.textChanged.connect(self.filter_and_display)
        self.ai_search_input.setMaximumWidth(200)
        self.ai_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #f8f0ff;
                border: 2px solid #e0d0ff;
            }
            QLineEdit:focus {
                border: 2px solid #8a2be2;
            }
        """)
        toolbar_row4_layout.addWidget(self.ai_search_input)

        # +++ 新增：AI特征排除框 +++
        self.ai_exclude_input = QLineEdit()
        self.ai_exclude_input.setPlaceholderText('排除ai特征...')
        self.ai_exclude_input.textChanged.connect(self.filter_and_display)
        self.ai_exclude_input.setMaximumWidth(200)
        self.ai_exclude_input.setStyleSheet("""
            QLineEdit {
                background-color: #f8f0ff;
                border: 2px solid #e0d0ff;
            }
            QLineEdit:focus {
                border: 2px solid #8a2be2;
            }
        """)
        toolbar_row4_layout.addWidget(self.ai_exclude_input)

        self.File_info_input = QLineEdit()
        self.File_info_input.setPlaceholderText('File_info搜索')
        self.File_info_input.textChanged.connect(self.filter_and_display)
        self.File_info_input.setMaximumWidth(200)
        toolbar_row4_layout.addWidget(self.File_info_input)

        # 添加每页显示数量控件
        toolbar_row4_layout.addWidget(QLabel("每页显示:"))
        self.page_size_input = QSpinBox()
        self.page_size_input.setRange(1, 1000)  # 设置范围
        self.page_size_input.setValue(self.packages_per_page)
        self.page_size_input.setMaximumWidth(60)
        self.page_size_input.setAlignment(Qt.AlignCenter)
        self.page_size_input.valueChanged.connect(
            lambda value: (setattr(self, 'packages_per_page', value), self.filter_and_display())
        )
        toolbar_row4_layout.addWidget(self.page_size_input)

        print_selected_btn = QToolButton()
        print_selected_btn.setText("打印选中")
        print_selected_btn.clicked.connect(self.print_selected_packages)
        toolbar_row4_layout.addWidget(print_selected_btn)
        # +++ 新增：测试打印按钮 +++
        self.test_print_btn = QToolButton()
        self.test_print_btn.setText("extract_Animation_from_scenes")
        self.test_print_btn.setToolTip("点击打印 'a'")
        self.test_print_btn.setStyleSheet("""
            QToolButton {
                background-color: #ff69b4;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 4px;
                border: none;
            }
            QToolButton:hover {
                background-color: #ff1493;
            }
        """)
        self.test_print_btn.clicked.connect(self.extract_Animation_from_scenes)
        toolbar_row4_layout.addWidget(self.test_print_btn)

        # ====== 状态栏 ======
        self.statusBar().showMessage('就绪')
        self.selected_count_label = QLabel("选中: 0 个包")
        self.selected_count_label.setStyleSheet("""
            QLabel {
                background-color: #e8f4ff;
                color: #0078d7;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #0078d7;
            }
        """)
        self.statusBar().addPermanentWidget(self.selected_count_label)
        
        # 用于后台加载的线程
        self.loading_thread = None
        self.stop_loading = False
        self.view_mode = "all"
    
    def load_multi_package_data(self, packages_info):
        """加载多个包的数据"""
        self.tmp = set()
        for info in packages_info:
            # print(info)
            # 解析依赖项
            dependencies = []
            deps_str = info.get('dependencies_str', '')
            if deps_str and deps_str not in ["无依赖", "无meta.json", "meta.json解析错误"]:
                deps = [d.strip() for d in deps_str.split(",") if d.strip()]
                for dep in deps:
                    dependencies.append(dep)
            
            # 创建包数据
            package_data = info['author']+"."+info['package_name']+"."+info['version']            
            self.tmp.add(package_data)

        self.selected_packages = self.tmp
        print(f"已加载 {len(self.tmp)} 个包的数据")
        self.view_selected_packages()
    
def main():
    app = QApplication(sys.argv)
    manager = VARManager()
    manager.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

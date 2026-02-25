import sys
import os
import zipfile
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidget, QVBoxLayout, 
                             QHBoxLayout, QWidget, QLabel, QPushButton, QTreeWidget,
                             QTreeWidgetItem, QSplitter, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt
import shutil
from pathlib import Path
from PyQt5.QtWidgets import QFileDialog

class VarScanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_var_file = None
        self.file_path_map = {}
        self.all_clothing_data = {}
        
        # 初始化文字描述和配置
        self.init_text_descriptions()
        self.init_component_weights()
        self.initUI()
        self.scan_var_files()
    
    def init_text_descriptions(self):
        """初始化所有文字描述和配置"""
        # 路径模式描述
        self.path_descriptions = {
            'Custom/Clothing': '服装',
            'Custom/Assets': 'Unity资产文件',
            'Custom/Scripts': '插件',
            'Custom/Hair': '头发',
            'meta.json': '📄 meta文件',
            'Custom/Atom/Person/Clothing': '服装预设',
            'Custom/Atom/Person/Plugins': '插件预设',
            'Custom/Atom/Person/Appearance': '外观预设',
            'Custom/Atom/Person/Hair': '头发预设',
            'Custom/Atom/Person/Morphs':'变形',
            'Custom/Atom/Person/Textures':'纹理',
            'Custom/Atom/Person/Skin':'纹理预设(皮肤)',
            'Custom/Tex': '其他(customTexture-服装需要的贴图)',
            'Custom/Images':'其他(可能是服装需要的贴图)',
            'Custom/Atom/ISSphere':'其他(customTexture_BumpMap-服装需要的贴图)',
            'Saves/PluginData':"插件相关",
            'Custom/Atom/Person/Pose':'姿势',
            'Custom/Atom/CustomUnityAsset':'资产',
            'Saves/scene':'场景'
        }

        # 已知路径模式
        self.known_paths = [
            'Custom/Clothing',
            'Custom/Assets',
            'Custom/Scripts',
            'Custom/Hair',         
            'meta.json',
            'Custom/Atom/Person/Clothing',
            'Custom/Atom/Person/Plugins',
            'Custom/Atom/Person/Appearance',
            'Custom/Tex',
            'Custom/Images',
            'Custom/Atom/Person/Hair',
            'Custom/Atom/Person/Morphs',
            'Custom/Atom/Person/Textures',
            'Custom/Atom/ISSphere',
            'Saves/PluginData',
            'Custom/Atom/Person/Pose',
            'Custom/Atom/Person/Skin',
            'Custom/Atom/CustomUnityAsset',
            'Saves/scene'
        ]

        # 自动分类时需要排除的<其他>路径(<其他>不参与分类的计数和分类名称)
        self.others = [
            'Custom/Tex',
            'Custom/Images',
            'Custom/Atom/ISSphere',
            'Saves/PluginData',
            'Saves' #这个目录很烦
        ]

        # 服装类型描述
        self.clothing_type_descriptions = {
            'female': '👗 女性服装',
            'male': '👔 男性服装',
            'Assets': '资产',
            'Clothing_preset': '服装预设',
            'Plugins_preset':'插件预设',
            'Appearance_preset':'外观预设',
            'Hair':'头发',
            'Morphs':'变形',
            'pose':'姿势',
            'Skin':'皮肤',
            'CustomUnityAsset':"资产"
        }
        
        # 按钮配置
        self.button_configs = {
            'female': ('👗 查看女性服装图像', '#ff69b4'),
            'male': ('👔 查看男性服装图像', '#4169e1'),
            'Assets': ('查看资产图像', '#4169e1'),
            'Hair': ('查看头发图像', '#4169e1'),            
            'Clothing_preset': ('查看服装预设图像', '#4169e1'),
            'Plugins_preset': ('查看插件预设图像', '#4169e1'),
            'Appearance_preset': ('查看外观预设图像', '#4169e1'),
            'Hair_preset': ('查看头发预设图像', '#4169e1'),
            'Morphs_preset': ('查看变形预设图像', '#4169e1'),
            'pose': ('查看姿势', '#4169e1'),
            'Skin': ('查看皮肤', '#4169e1'),
            'CustomUnityAsset': ('查看皮肤', '#4169e1'),
            'Scene': ('查看场景', '#4169e1'),
        }
        # 定义要分析的路径类型 - 可轻松扩展
        self.clothing_types = {
            'female': 'Custom/Clothing/Female/',
            'male': 'Custom/Clothing/Male/',
            'Hair':'Custom/Hair',
            'Assets': 'Custom/Assets',
            'Clothing_preset': 'Custom/Atom/Person/Clothing',
            'Plugins_preset':'Custom/Atom/Person/Plugins',
            'Appearance_preset':'Custom/Atom/Person/Appearance',
            'Hair_preset':'Custom/Atom/Person/Hair',
            'Morphs_preset':'Custom/Atom/Person/Morphs',
            'pose':'Custom/Atom/Person/Pose',
            'Skin':'Custom/Atom/Person/Skin',
            'CustomUnityAsset':'Custom/Atom/CustomUnityAsset',
            'Scene':'Saves/scene'
        }
        
        # 图像文件扩展名
        self.image_extensions = ['.png', '.jpg', '.jpeg', '.tga', '.bmp', '.dds']
        
        # VAM文件扩展名
        self.vam_extensions = ['.vam', '.vab', '.vaj']
        self.vap_extensions = ['.vap']
        self.assetbundle_extensions = ['.assetbundle']
        self.scene_extensions = ['.json']

    def init_component_weights(self):
        """初始化组件权重"""
        self.component_weights = {
            # 最高优先级 - 完整体验
            'Saves/scene': {'weight': 11129, 'name': '场景', 'category': 'scene', 'priority': '最高'},
            'Custom/Atom/Person/Appearance': {'weight': 28, 'name': '外观预设', 'category': 'appearance', 'priority': '最高'},
            
            # 高优先级 - 核心内容
            'Custom/Scripts': {'weight': 22, 'name': '插件', 'category': 'scripts', 'priority': '高'},
            'Custom/Atom/Person/Plugins': {'weight': 23, 'name': '插件预设', 'category': 'plugins', 'priority': '高'},
            'Custom/Clothing': {'weight': 21, 'name': '服装', 'category': 'clothing', 'priority': '高'},
            'Custom/Atom/Person/Clothing': {'weight': 22, 'name': '服装预设', 'category': 'clothing_preset', 'priority': '高'},
            
            # 中高优先级 - 重要组件
            'Custom/Hair': {'weight': 14, 'name': '头发', 'category': 'hair', 'priority': '中高'},
            'Custom/Atom/Person/Hair': {'weight': 15, 'name': '头发预设', 'category': 'hair_preset', 'priority': '中高'},
            'Custom/Assets': {'weight': 13, 'name': '资产', 'category': 'assets', 'priority': '中高'},
            'Custom/Atom/CustomUnityAsset': {'weight': 13, 'name': 'Unity资产', 'category': 'unity_asset', 'priority': '中高'},
            
            # 中等优先级 - 常用内容
            'Custom/Atom/Person/Pose': {'weight': 8, 'name': '姿势', 'category': 'pose', 'priority': '中'},
            'Custom/Atom/Person/Skin': {'weight': 7, 'name': '皮肤', 'category': 'skin', 'priority': '中'},
            'Custom/Atom/Person/Morphs': {'weight': 6, 'name': '变形', 'category': 'morphs', 'priority': '中'},
            'Custom/Atom/Person/Textures': {'weight': 5, 'name': '纹理', 'category': 'textures', 'priority': '中'},
            
            # 低优先级 - 辅助内容
            'Custom/Images': {'weight': 2, 'name': '图片资源', 'category': 'images', 'priority': '低'},
            'Custom/Tex': {'weight': 1, 'name': '贴图', 'category': 'tex', 'priority': '低'},
            'Saves/PluginData': {'weight': 0, 'name': '插件数据', 'category': 'plugin_data', 'priority': '低'},
            'Custom/Atom/ISSphere': {'weight': 0, 'name': '环境球', 'category': 'environment', 'priority': '低'},
        }

    def initUI(self):
        self.setWindowTitle('VAR包扫描器 - 路径分析版')
        self.setGeometry(0, 0, 3600, 1900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # 左侧面板
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel('VAR包文件列表'))
        self.var_list = QListWidget()
        self.var_list.itemClicked.connect(self.on_var_selected)
        left_layout.addWidget(self.var_list)
        
        # 按钮区域
        button_layout = QVBoxLayout()
        
        self.extract_btn = QPushButton('解压到当前目录')
        self.extract_btn.clicked.connect(self.extract_var)
        self.extract_btn.setEnabled(False)
        self.extract_btn.setMinimumHeight(40)
        button_layout.addWidget(self.extract_btn)
        
        self.analyze_btn = QPushButton('分析路径结构')
        self.analyze_btn.clicked.connect(self.analyze_path_structure)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setMinimumHeight(40)
        button_layout.addWidget(self.analyze_btn)
        
        self.classify_btn = QPushButton('按分数分类所有VAR文件')
        self.classify_btn.clicked.connect(self.classify_all_var_files)
        self.classify_btn.setMinimumHeight(40)
        button_layout.addWidget(self.classify_btn)
        
        # 在按钮区域添加目录选择按钮
        self.select_dir_btn = QPushButton('选择扫描目录')
        self.select_dir_btn.clicked.connect(self.select_scan_directory)
        self.select_dir_btn.setMinimumHeight(40)
        button_layout.addWidget(self.select_dir_btn)
        
        # 显示当前扫描目录
        self.current_dir_label = QLabel(f'当前目录: {os.getcwd()}')
        self.current_dir_label.setStyleSheet("color: #666; padding: 5px;")
        button_layout.addWidget(self.current_dir_label)

        left_layout.addLayout(button_layout)
        
        # 右侧面板
        right_splitter = QSplitter(Qt.Vertical)
        
        # 右上部分 - 文件树形结构
        top_right_widget = QWidget()
        top_right_layout = QVBoxLayout(top_right_widget)
        top_right_layout.addWidget(QLabel('VAR包内容结构'))
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(['文件路径', '大小', '路径分析'])
        self.file_tree.setColumnWidth(0, 800)
        self.file_tree.setColumnWidth(1, 200)
        self.file_tree.setColumnWidth(2, 300)
        
        # 添加文件树的双击事件
        self.file_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        
        top_right_layout.addWidget(self.file_tree)

        # 右下部分 - 路径分析结果
        bottom_right_widget = QWidget()
        bottom_right_layout = QVBoxLayout(bottom_right_widget)
        bottom_right_layout.addWidget(QLabel('路径分析结果'))
        self.analysis_display = QTextEdit()
        self.analysis_display.setReadOnly(True)
        bottom_right_layout.addWidget(self.analysis_display)
        
        right_splitter.addWidget(top_right_widget)
        right_splitter.addWidget(bottom_right_widget)
        right_splitter.setSizes([500, 300])
        
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([250, 950])

    def select_scan_directory(self):
        """选择扫描目录"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            '选择VAR包扫描目录',
            # os.getcwd(),
            r"D:\Virt_A_Mate\VAM_Organizer\Temporary VAR Package Directory",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            os.chdir(directory)
            self.current_dir_label.setText(f'当前目录: {directory}')
            self.scan_var_files()

    def scan_var_files(self):
        """扫描当前目录下的所有.var文件"""
        current_dir = os.getcwd()
        self.var_list.clear()
        
        var_files = []
        for filename in os.listdir(current_dir):
            if filename.lower().endswith('.var'):
                var_files.append(filename)
        
        # 按文件名排序
        var_files.sort()
        
        for filename in var_files:
            self.var_list.addItem(filename)
        
        if self.var_list.count() == 0:
            self.var_list.addItem("未找到任何.var文件")
        
        # 更新状态
        self.current_dir_label.setText(f'当前目录: {current_dir} (找到 {len(var_files)} 个VAR文件)')
    
    def on_var_selected(self, item):
        """当选择VAR文件时显示其内容"""
        var_filename = item.text()
        if var_filename == "未找到任何.var文件":
            return
            
        self.current_var_file = var_filename
        self.extract_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.display_var_contents(var_filename)
        self.analyze_path_structure()
    
    def display_var_contents(self, var_filename):
        """显示VAR包内的文件结构"""
        self.file_tree.clear()
        self.analysis_display.clear()
        
        try:
            with zipfile.ZipFile(var_filename, 'r') as var_zip:
                file_list = var_zip.infolist()
                
                # 创建目录结构
                dir_structure = {}
                for file_info in file_list:
                    filename = file_info.filename
                    parts = filename.split('/')
                    current_dir = dir_structure
                    
                    for i, part in enumerate(parts):
                        if i == len(parts) - 1:  # 文件
                            current_dir[part] = {
                                'type': 'file',
                                'size': file_info.file_size,
                                'full_path': filename
                            }
                        else:  # 目录
                            if part not in current_dir:
                                current_dir[part] = {'type': 'dir', 'children': {}}
                            current_dir = current_dir[part]['children']
                
                # 构建树形显示
                root = QTreeWidgetItem(self.file_tree, [var_filename, '', ''])
                self.build_tree_view(root, dir_structure)
                self.file_tree.expandAll()
                
        except Exception as e:
            QMessageBox.warning(self, '错误', f'无法读取VAR文件: {str(e)}')
    
    def build_tree_view(self, parent_node, structure):
        """递归构建树形视图"""
        for name, info in structure.items():
            if info['type'] == 'dir':
                dir_node = QTreeWidgetItem(parent_node, [name, '文件夹', ''])
                self.build_tree_view(dir_node, info['children'])
            else:
                size_str = self.format_size(info['size'])
                QTreeWidgetItem(parent_node, [name, size_str, ''])

    def analyze_path_structure(self):
        """分析路径结构，识别已知和未知的路径模式"""
        if not self.current_var_file:
            return
            
        try:
            with zipfile.ZipFile(self.current_var_file, 'r') as var_zip:
                file_list = var_zip.infolist()
                
                known_patterns = {}
                unknown_files = []
                
                # 分析所有类型的数据
                self.all_clothing_data = {}
                self.analyze_all_clothing_types(var_zip, file_list)
                # 分析每个文件的路径
                for file_info in file_list:
                    filename = file_info.filename
                    # 跳过目录条目
                    if filename.endswith('/'):
                        continue
                    
                    # 检查是否包含已知的路径模式
                    path_analysis = self.analyze_file_path(filename)
                    
                    if path_analysis['known']:
                        pattern = path_analysis['pattern']
                        if pattern not in known_patterns:
                            known_patterns[pattern] = []
                        known_patterns[pattern].append(filename)
                    else:
                        unknown_files.append(filename)
                
                # 更新树形视图显示路径分析
                self.update_tree_with_analysis(known_patterns, unknown_files)
                
                # 显示分析结果
                self.display_path_analysis_results(known_patterns, unknown_files)
                
        except Exception as e:
            QMessageBox.warning(self, '错误', f'分析失败: {str(e)}')
            raise

    def on_tree_item_double_clicked(self, item, column):
        """处理文件树中项目的双击事件"""
        # 检查是否是文件（不是文件夹）
        if item.text(1) != '文件夹' and item.text(1) != '':
            # 获取完整文件路径
            full_path = self.get_full_tree_path(item)
            
            # 检查是否是图片文件
            if self.is_image_file(full_path):
                self.open_image_from_var(full_path, item.text(0))

    def open_image_from_var(self, image_path, filename):
        """从VAR包中打开指定图片"""
        if not self.current_var_file:
            QMessageBox.warning(self, '错误', '没有选择VAR文件')
            return
        
        try:
            with zipfile.ZipFile(self.current_var_file, 'r') as var_zip:
                # 检查文件是否存在
                if image_path not in [f.filename for f in var_zip.infolist()]:
                    QMessageBox.warning(self, '错误', f'文件不存在: {image_path}')
                    return
                
                # 读取图片数据
                with var_zip.open(image_path) as img_file:
                    image_data = img_file.read()
                    self.show_single_image_viewer(image_data, filename)
                    
        except Exception as e:
            QMessageBox.critical(self, '错误', f'无法打开图片: {str(e)}')

    def analyze_file_path(self, filepath):
        """分析文件路径，识别已知的路径模式"""
        # 检查图像文件扩展名
        is_image = self.is_image_file(filepath)
        
        for pattern in self.known_paths:
            if filepath.startswith(pattern + '/') or pattern in filepath:
                description = self.get_path_description(pattern)
                # 如果是图像文件，在描述中添加图像标识
                if is_image:
                    description = f"🖼️ {description}"
                return {
                    'known': True,
                    'pattern': pattern,
                    'description': description,
                    'is_image': is_image
                }
        
        return {'known': False, 'is_image': is_image}
    
    def get_path_description(self, pattern):
        """获取路径模式的描述"""
        return self.path_descriptions.get(pattern, pattern)

    def update_tree_with_analysis(self, known_patterns, unknown_files):
        """在树形视图中更新路径分析信息"""
        # 首先收集所有文件的完整路径映射
        self.file_path_map = {}
        self.collect_file_paths(self.file_tree.invisibleRootItem(), "")
        
        # 更新树形视图显示
        root = self.file_tree.invisibleRootItem()
        self.update_tree_items_analysis(root, known_patterns, unknown_files)

    def collect_file_paths(self, parent_item, current_path):
        """收集树形视图中所有文件的完整路径"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            item_text = child.text(0)
            
            # 构建完整路径
            if current_path:
                full_path = f"{current_path}/{item_text}"
            else:
                full_path = item_text
            
            # 如果是文件（不是文件夹），保存到映射
            if child.text(1) != '文件夹' and child.text(1) != '':
                self.file_path_map[item_text] = full_path
            
            # 递归处理子项
            if child.childCount() > 0:
                self.collect_file_paths(child, full_path)
    
    def show_single_image_viewer(self, image_data, filename, original_pixmap=None):
        """显示单张图片查看器 - 通用方法"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
        from PyQt5.QtCore import Qt, QPoint
        from PyQt5.QtGui import QPixmap, QImage
        
        class SingleImageViewer(QDialog):
            def __init__(self, image_data, title, original_pixmap=None, parent=None):
                super().__init__(parent)
                self.image_data = image_data
                self.original_pixmap = original_pixmap
                self.current_scale = 3.0
                self.dragging = False
                self.last_mouse_pos = QPoint()
                self.current_pos = QPoint(0, 0)
                self.initUI(title)
                if not self.original_pixmap:
                    self.load_image()
                else:
                    self.update_image()
                    self.update_status()
            
            def initUI(self, title):
                self.setWindowTitle(f'图片查看器 - {title}')
                self.setGeometry(0, 0, 3600, 1900)
                
                layout = QVBoxLayout()
                
                # 图片显示标签
                self.image_label = QLabel()
                self.image_label.setAlignment(Qt.AlignCenter)
                self.image_label.setStyleSheet("background-color: black;")
                self.image_label.setMinimumSize(1024, 1024)
                
                # 启用鼠标跟踪
                self.image_label.setMouseTracking(True)
                self.image_label.mousePressEvent = self.mousePressEvent
                self.image_label.mouseMoveEvent = self.mouseMoveEvent
                self.image_label.mouseReleaseEvent = self.mouseReleaseEvent
                self.image_label.wheelEvent = self.wheelEvent
                
                # 控制按钮
                control_layout = QHBoxLayout()
                zoom_in_btn = QPushButton('放大 (+)')
                zoom_out_btn = QPushButton('缩小 (-)')
                reset_btn = QPushButton('重置')
                fit_btn = QPushButton('适应窗口')
                close_btn = QPushButton('关闭')
                
                zoom_in_btn.clicked.connect(self.zoom_in)
                zoom_out_btn.clicked.connect(self.zoom_out)
                reset_btn.clicked.connect(self.reset_view)
                fit_btn.clicked.connect(self.fit_to_window)
                close_btn.clicked.connect(self.close)
                
                control_layout.addWidget(zoom_in_btn)
                control_layout.addWidget(zoom_out_btn)
                control_layout.addWidget(reset_btn)
                control_layout.addWidget(fit_btn)
                control_layout.addStretch()
                control_layout.addWidget(close_btn)
                
                # 状态栏
                self.status_label = QLabel('缩放: 100% | 使用鼠标滚轮缩放，拖拽移动')
                self.status_label.setStyleSheet("color: #666; padding: 5px;")
                
                layout.addWidget(self.image_label)
                layout.addLayout(control_layout)
                # layout.addWidget(self.status_label)
                
                self.setLayout(layout)
            
            def load_image(self):
                """加载图片"""
                try:
                    qimage = QImage()
                    qimage.loadFromData(self.image_data)
                    self.original_pixmap = QPixmap(qimage)
                    self.update_image()
                    self.update_status()
                except Exception as e:
                    self.image_label.setText(f"无法加载图片\n{str(e)}")
            
            def update_image(self):
                """更新显示的图片"""
                if self.original_pixmap:
                    # 计算缩放后的尺寸
                    new_width = int(self.original_pixmap.width() * self.current_scale)
                    new_height = int(self.original_pixmap.height() * self.current_scale)
                    
                    scaled_pixmap = self.original_pixmap.scaled(
                        new_width, new_height, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled_pixmap)
            
            def update_status(self):
                """更新状态栏"""
                if self.original_pixmap:
                    original_width = self.original_pixmap.width()
                    original_height = self.original_pixmap.height()
                    current_width = int(original_width * self.current_scale)
                    current_height = int(original_height * self.current_scale)
                    
                    self.status_label.setText(
                        f'缩放: {self.current_scale*100:.1f}% | '
                        f'原始尺寸: {original_width}×{original_height} | '
                        f'当前尺寸: {current_width}×{current_height} | '
                        f'使用鼠标滚轮缩放，拖拽移动'
                    )
            
            def zoom_in(self):
                """放大图片"""
                self.current_scale *= 1.2
                self.update_image()
                self.update_status()
            
            def zoom_out(self):
                """缩小图片"""
                self.current_scale /= 1.2
                if self.current_scale < 0.1:
                    self.current_scale = 0.1
                self.update_image()
                self.update_status()
            
            def reset_view(self):
                """重置视图"""
                self.current_scale = 1.0
                self.current_pos = QPoint(0, 0)
                self.update_image()
                self.update_status()
            
            def fit_to_window(self):
                """适应窗口大小"""
                if self.original_pixmap and self.image_label.width() > 0:
                    # 计算适合窗口的缩放比例
                    label_width = self.image_label.width() - 20
                    label_height = self.image_label.height() - 20
                    
                    scale_x = label_width / self.original_pixmap.width()
                    scale_y = label_height / self.original_pixmap.height()
                    
                    self.current_scale = min(scale_x, scale_y)
                    self.update_image()
                    self.update_status()
            
            def wheelEvent(self, event):
                """鼠标滚轮事件 - 缩放"""
                if event.angleDelta().y() > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
            
            def mousePressEvent(self, event):
                """鼠标按下事件 - 开始拖拽"""
                if event.button() == Qt.LeftButton:
                    self.dragging = True
                    self.last_mouse_pos = event.globalPos()
                    self.setCursor(Qt.ClosedHandCursor)
            
            def mouseMoveEvent(self, event):
                """鼠标移动事件 - 拖拽图片"""
                if self.dragging and hasattr(event, 'globalPos'):
                    delta = event.globalPos() - self.last_mouse_pos
                    self.last_mouse_pos = event.globalPos()
            
            def mouseReleaseEvent(self, event):
                """鼠标释放事件 - 结束拖拽"""
                if event.button() == Qt.LeftButton:
                    self.dragging = False
                    self.setCursor(Qt.ArrowCursor)
        
        # 创建并显示图片查看器
        viewer = SingleImageViewer(image_data, filename, original_pixmap, self)
        viewer.exec_()

    def update_tree_items_analysis(self, parent_item, known_patterns, unknown_files):
        """递归更新树形视图项的路径分析"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            item_text = child.text(0)
            
            # 获取完整文件路径
            full_path = self.get_full_tree_path(child)
            
            # 跳过根节点（VAR文件名）
            if full_path == self.current_var_file:
                continue
                
            # 如果是文件（不是文件夹）
            if child.text(1) != '文件夹' and child.text(1) != '':
                # 在已知模式中查找这个完整路径
                found_in_known = False
                for pattern, files in known_patterns.items():
                    if full_path in files:
                        analysis_result = self.analyze_file_path(full_path)
                        display_text = f"✅ {analysis_result['description']}"
                        
                        # 如果是图像文件，添加图像标识
                        if analysis_result.get('is_image', False):
                            display_text = f"🖼️ {analysis_result['description']}"
                        
                        child.setText(2, display_text)
                        found_in_known = True
                        break
                
                # 在未知文件中查找
                if not found_in_known:
                    if full_path in unknown_files:
                        analysis_result = self.analyze_file_path(full_path)
                        if analysis_result.get('is_image', False):
                            child.setText(2, "🖼️ ⚠️ 未知路径图像")
                        else:
                            child.setText(2, "⚠️ 路径模式未知")
                    else:
                        child.setText(2, "❓ 未分析")
            
            # 如果是文件夹，标记为文件夹
            elif child.text(1) == '文件夹':
                child.setText(2, "📁 文件夹")
            
            # 递归处理子项
            if child.childCount() > 0:
                self.update_tree_items_analysis(child, known_patterns, unknown_files)

    def get_full_tree_path(self, item):
        """从树形视图项构建完整文件路径"""
        path_parts = []
        current = item
        
        # 从当前项向上遍历到根节点
        while current is not None:
            text = current.text(0)
            # 跳过根节点的VAR文件名和空文本
            if text and text != self.current_var_file and text != "未找到任何.var文件":
                path_parts.insert(0, text)
            current = current.parent()
        
        return '/'.join(path_parts)

    def analyze_all_clothing_types(self, var_zip, file_list):
        """分析所有类型的服装数据"""
        
        for cloth_type, base_path in self.clothing_types.items():
            type_files = {}
            
            # 收集该类型下的所有文件
            for file_info in file_list:
                filename = file_info.filename
                if filename.startswith(base_path):
                    parts = filename.split('/')
                    subdir = parts[len(parts)-2]  # 子目录名称
                    if subdir not in type_files:
                        type_files[subdir] = []
                    type_files[subdir].append({
                        'name': parts[-1],
                        'full_path': filename,
                        'extension': os.path.splitext(filename)[1].lower()
                    })
                
            # 分析每个子目录
            for subdir, files in type_files.items():
                vam_files = [f for f in files if f['extension'] in self.vam_extensions]
                image_files = [f for f in files if f['extension'] in self.image_extensions]
                vap_files = [f for f in files if f['extension'] in self.vap_extensions]
                assetbundle_files = [f for f in files if f['extension'] in self.assetbundle_extensions]
                json_files = [f for f in files if f['extension'] in self.scene_extensions]

                # 按基础名分组
                clothing_items = {}
                for vam_file in vam_files:
                    base_name = os.path.splitext(vam_file['name'])[0]
                    if base_name not in clothing_items:
                        clothing_items[base_name] = {'vam_files': [], 'images': []}
                    clothing_items[base_name]['vam_files'].append(vam_file)
                
                # 匹配图片文件
                for image_file in image_files:
                    base_name = os.path.splitext(image_file['name'])[0]
                    if base_name in clothing_items:
                        clothing_items[base_name]['images'].append(image_file)

                if clothing_items:
                    if cloth_type not in self.all_clothing_data:
                        self.all_clothing_data[cloth_type] = {}
                    self.all_clothing_data[cloth_type][subdir] = {
                        'clothing_count': len(clothing_items),
                        'items': clothing_items
                    }
                

                # 2 匹配服装预设的vap文件
                # 按基础名分组
                clothing_vap_items = {}
                for vap_file in vap_files:
                    base_name = os.path.splitext(vap_file['name'])[0]
                    if base_name not in clothing_vap_items:
                        clothing_vap_items[base_name] = {'vam_files': [], 'images': []}
                    clothing_vap_items[base_name]['vam_files'].append(vap_file)
                # 匹配图片文件
                for image_file in image_files:
                    base_name = os.path.splitext(image_file['name'])[0]
                    if base_name in clothing_vap_items:
                        clothing_vap_items[base_name]['images'].append(image_file)
                if clothing_vap_items:
                    if cloth_type not in self.all_clothing_data:
                        self.all_clothing_data[cloth_type] = {}
                    self.all_clothing_data[cloth_type][subdir] = {
                        'clothing_count': len(clothing_vap_items),
                        'items': clothing_vap_items
                    }
                
                # 3 匹配资产的assetbundle文件
                # 按基础名分组
                clothing_assetbundle_file_items = {}
                for assetbundle_file in assetbundle_files:
                    base_name = os.path.splitext(assetbundle_file['name'])[0]
                    if base_name not in clothing_assetbundle_file_items:
                        clothing_assetbundle_file_items[base_name] = {'vam_files': [], 'images': []}
                    clothing_assetbundle_file_items[base_name]['vam_files'].append(assetbundle_file)
                # 匹配图片文件
                for image_file in image_files:
                    base_name = os.path.splitext(image_file['name'])[0]
                    if base_name in clothing_assetbundle_file_items:
                        clothing_assetbundle_file_items[base_name]['images'].append(image_file)
                if clothing_assetbundle_file_items:
                    if cloth_type not in self.all_clothing_data:
                        self.all_clothing_data[cloth_type] = {}
                    self.all_clothing_data[cloth_type][subdir] = {
                        'clothing_count': len(clothing_assetbundle_file_items),
                        'items': clothing_assetbundle_file_items
                    }
                
                # 3 匹配场景的json文件
                # 按基础名分组
                clothing_json_file_items = {}
                for json_file in json_files:
                    base_name = os.path.splitext(json_file['name'])[0]
                    if base_name not in clothing_json_file_items:
                        clothing_json_file_items[base_name] = {'vam_files': [], 'images': []}
                    clothing_json_file_items[base_name]['vam_files'].append(json_file)
                # 匹配图片文件
                for image_file in image_files:
                    base_name = os.path.splitext(image_file['name'])[0]
                    if base_name in clothing_json_file_items:
                        clothing_json_file_items[base_name]['images'].append(image_file)
                if clothing_json_file_items:
                    if cloth_type not in self.all_clothing_data:
                        self.all_clothing_data[cloth_type] = {}
                    self.all_clothing_data[cloth_type][subdir] = {
                        'clothing_count': len(clothing_json_file_items),
                        'items': clothing_json_file_items
                    }

    def display_path_analysis_results(self, known_patterns, unknown_files):
        """显示路径分析结果"""
        result_text = "=== 路径结构分析结果 ===\n\n"
        
        # 显示所有类型服装统计
        for cloth_type, data in self.all_clothing_data.items():
            if data:
                total_items = sum(subdata['clothing_count'] for subdata in data.values())
                description = self.clothing_type_descriptions.get(cloth_type, cloth_type)
                result_text += f"{description}统计: 共 {total_items} 个项目\n"
                
                for subdir, subdata in data.items():
                    result_text += f"  📁 {subdir}: {subdata['clothing_count']} 个项目\n"
                    for base_name, item_data in subdata['items'].items():
                        vam_count = len(item_data['vam_files'])
                        image_count = len(item_data['images'])
                        result_text += f"    📦 {base_name}: {vam_count}个文件, {image_count}张图片\n"
                
                result_text += "\n"
        
        # 添加查看图像按钮
        self.add_image_viewer_buttons()
        
        # 统计图像文件
        image_files = {}
        total_images = 0
        
        # 显示已知路径模式的文件
        result_text += "✅ 已知路径模式:\n"
        if known_patterns:
            for pattern, files in known_patterns.items():
                description = self.get_path_description(pattern)
                result_text += f"  📁 {description} : {len(files)} 个文件\n"
                
                # 统计该模式下的图像文件
                pattern_images = [f for f in files if self.is_image_file(f)]
                image_files[pattern] = pattern_images
                total_images += len(pattern_images)
                
                # 显示文件示例
                image_examples = pattern_images[:2]
                other_examples = [f for f in files if f not in image_examples][:1]
                examples = image_examples + other_examples
                
                for i, file in enumerate(examples[:3]):
                    filename = os.path.basename(file)
                    if self.is_image_file(file):
                        result_text += f"      {i+1}. 🖼️ {filename}\n"
                    else:
                        result_text += f"      {i+1}. {filename}\n"
                        
                if len(files) > 3:
                    result_text += f"      ... 还有 {len(files)-3} 个文件\n"
                result_text += "\n"
        else:
            result_text += "  无已知路径模式\n"
        
        result_text += "\n"
        
        # 显示图像文件统计
        if total_images > 0:
            result_text += f"🖼️ 图像文件统计: 共发现 {total_images} 个图像文件\n"
            for pattern, images in image_files.items():
                if images:
                    description = self.get_path_description(pattern)
                    result_text += f"  - {description}: {len(images)} 个图像\n"
            result_text += "\n"
        
        # 显示未知路径的文件
        result_text += "⚠️ 未知路径模式的文件:\n"
        unknown_images = [f for f in unknown_files if self.is_image_file(f)]
        
        if unknown_files:
            # 先显示未知的图像文件
            if unknown_images:
                result_text += "  🖼️ 未知路径图像文件:\n"
                for i, filename in enumerate(unknown_images, 1):
                    result_text += f"    {i}. {filename}\n"
                result_text += "\n"
            
            # 显示其他未知文件
            other_unknown = [f for f in unknown_files if not self.is_image_file(f)]
            if other_unknown:
                result_text += "  其他未知路径文件:\n"
                for i, filename in enumerate(other_unknown, 1):
                    result_text += f"    {i}. {filename}\n"
        else:
            result_text += "  无未知路径文件 - 所有文件都已识别路径模式！\n"
        
        # 统计信息
        total_files = sum(len(files) for files in known_patterns.values()) + len(unknown_files)
        if total_files > 0:
            known_percentage = (sum(len(files) for files in known_patterns.values()) / total_files) * 100
            result_text += f"\n📊 统计: {known_percentage:.1f}% 的文件路径已识别"
            if total_images > 0:
                result_text += f", 包含 {total_images} 个图像文件"
        
        self.analysis_display.setText(result_text)

    def add_image_viewer_buttons(self):
        """添加查看图像按钮 - 修复重复添加问题"""
        # 创建按钮容器
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        
        # 检查是否有任何类型的数据
        has_data = any(self.all_clothing_data.get(cloth_type) for cloth_type in self.button_configs.keys())
        
        if has_data:
            # 创建合并查看按钮
            merge_btn = QPushButton('👗👔 查看所有服装图像')
            merge_btn.clicked.connect(self.show_all_clothing_images)
            merge_btn.setMinimumHeight(40)
            merge_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9370db;
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 8px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #7b68ee;
                }
            """)
            button_layout.addWidget(merge_btn)
            
            # 为每种类型创建单独的查看按钮
            for cloth_type, (btn_text, color) in self.button_configs.items():
                if cloth_type in self.all_clothing_data and self.all_clothing_data[cloth_type]:
                    btn = QPushButton(btn_text)
                    btn.clicked.connect(lambda checked, t=cloth_type: self.show_clothing_images(t))
                    btn.setMinimumHeight(40)
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {color};
                            color: white;
                            font-size: 24px;
                            font-weight: bold;
                            border-radius: 8px;
                            padding: 8px;
                            margin: 2px;
                        }}
                        QPushButton:hover {{
                            background-color: {self.darken_color(color)};
                        }}
                    """)
                    button_layout.addWidget(btn)
        
        # 将按钮容器添加到左侧布局 - 修复重复添加问题
        left_widget = self.var_list.parent()
        left_layout = left_widget.layout()
        
        # 移除旧的按钮容器（如果存在）
        for i in reversed(range(left_layout.count())):
            item = left_layout.itemAt(i)
            if item and hasattr(item.widget(), 'layout'):
                # 检查是否是按钮容器（通过布局中的按钮数量判断）
                widget_layout = item.widget().layout()
                if widget_layout and widget_layout.count() > 0:
                    first_item = widget_layout.itemAt(0)
                    if first_item and hasattr(first_item.widget(), 'text'):
                        if '查看' in first_item.widget().text():
                            item.widget().deleteLater()
                            break
        
        left_layout.insertWidget(3, button_widget)

    def show_all_clothing_images(self):
        """显示所有类型的服装图像 - 增强版"""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                   QScrollArea, QPushButton, QSlider, QGridLayout)
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPixmap, QImage
        
        class AllClothingImageViewer(QDialog):
            def __init__(self, all_clothing_data, parent=None):
                super().__init__(parent)
                self.all_clothing_data = all_clothing_data
                self.current_scale = 1.0
                self.initUI()
                
            def initUI(self):
                self.setWindowTitle('所有服装图像查看器')
                self.setGeometry(0, 0, 3840, 2160)
                
                layout = QVBoxLayout()
                
                # 控制按钮
                control_layout = QHBoxLayout()
                self.zoom_in_btn = QPushButton('放大')
                self.zoom_out_btn = QPushButton('缩小')
                self.reset_btn = QPushButton('重置大小')
                
                self.zoom_in_btn.clicked.connect(self.zoom_in)
                self.zoom_out_btn.clicked.connect(self.zoom_out)
                self.reset_btn.clicked.connect(self.reset_zoom)
                
                control_layout.addWidget(self.zoom_in_btn)
                control_layout.addWidget(self.zoom_out_btn)
                control_layout.addWidget(self.reset_btn)
                control_layout.addStretch()
                
                # 缩放滑块
                self.zoom_slider = QSlider(Qt.Horizontal)
                self.zoom_slider.setMinimum(10)
                self.zoom_slider.setMaximum(500)
                self.zoom_slider.setValue(100)
                self.zoom_slider.valueChanged.connect(self.slider_zoom)
                control_layout.addWidget(QLabel('缩放:'))
                control_layout.addWidget(self.zoom_slider)
                
                layout.addLayout(control_layout)
                
                # 统计信息
                total_items = 0
                total_images = 0
                for cloth_type_data in self.all_clothing_data.values():
                    for subdir_data in cloth_type_data.values():
                        total_items += subdir_data['clothing_count']
                        for item_data in subdir_data['items'].values():
                            total_images += len(item_data['images'])
                
                stats_label = QLabel(f'共 {total_items} 个项目，{total_images} 张图片')
                stats_label.setStyleSheet("font-weight: bold; color: #333; padding: 5px;")
                layout.addWidget(stats_label)
                
                # 图片显示区域
                scroll_area = QScrollArea()
                self.scroll_content = QWidget()
                self.grid_layout = QGridLayout(self.scroll_content)
                
                self.display_images()
                
                scroll_area.setWidget(self.scroll_content)
                scroll_area.setWidgetResizable(True)
                layout.addWidget(scroll_area)
                
                self.setLayout(layout)
            
            def display_images(self):
                """显示所有图片"""
                # 清空现有内容
                for i in reversed(range(self.grid_layout.count())): 
                    self.grid_layout.itemAt(i).widget().setParent(None)
                
                row, col = 0, 0
                max_cols = 3
                
                type_colors = {
                    'female': '#ff69b4',
                    'male': '#4169e1'
                }
                
                for cloth_type, cloth_data in self.all_clothing_data.items():
                    for subdir, data in cloth_data.items():
                        for base_name, item_data in data['items'].items():
                            if item_data['images']:
                                # 使用第一张图片
                                image_info = item_data['images'][0]
                                
                                # 创建图片显示部件
                                image_widget = self.create_image_widget(image_info, base_name, subdir, cloth_type, type_colors.get(cloth_type, '#cccccc'))
                                self.grid_layout.addWidget(image_widget, row, col)
                                
                                col += 1
                                if col >= max_cols:
                                    col = 0
                                    row += 1
                
                # 如果没有图片显示提示
                if self.grid_layout.count() == 0:
                    no_images_label = QLabel('未找到可显示的图片')
                    no_images_label.setAlignment(Qt.AlignCenter)
                    self.grid_layout.addWidget(no_images_label, 0, 0)
            
            def create_image_widget(self, image_info, base_name, subdir, cloth_type, color):
                """创建单个图片显示部件 - 添加点击事件"""
                from PyQt5.QtWidgets import QFrame
                
                widget = QFrame()
                widget.setFrameStyle(QFrame.Box)
                widget.setStyleSheet(f"border: 2px solid {color}; margin: 5px; padding: 5px;")
                widget.setCursor(Qt.PointingHandCursor)  # 添加手型光标
                layout = QVBoxLayout(widget)
                
                # 图片标签
                image_label = QLabel()
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setStyleSheet("background-color: #f0f0f0;")
                
                # 存储图片信息用于点击事件
                image_label.image_info = image_info
                image_label.base_name = base_name
                image_label.subdir = subdir
                image_label.cloth_type = cloth_type
                
                # 设置点击事件
                image_label.mousePressEvent = lambda e: self.show_single_image(image_label)
                
                # 尝试从VAR包加载图片
                try:
                    with zipfile.ZipFile(self.parent().current_var_file, 'r') as var_zip:
                        with var_zip.open(image_info['full_path']) as img_file:
                            image_data = img_file.read()
                            qimage = QImage()
                            qimage.loadFromData(image_data)
                            pixmap = QPixmap(qimage)
                            
                            # 缩放图片以适应显示
                            scaled_pixmap = pixmap.scaled(1024, 1024, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            image_label.setPixmap(scaled_pixmap)
                            image_label.original_pixmap = pixmap
                except Exception as e:
                    image_label.setText(f"无法加载图片\n{str(e)}")
                
                # 信息标签
                if cloth_type == 'female':
                    type_name = "女性服装"
                elif cloth_type == 'male':
                    type_name = "男性服装"
                elif cloth_type == 'Clothing_preset':
                    type_name = "服装预设"
                elif cloth_type == 'Assets':
                    type_name = "资产"
                elif cloth_type == 'Plugins_preset':
                    type_name = "插件预设"
                elif cloth_type == 'Appearance_preset':
                    type_name = "外观预设"
                elif cloth_type == 'Hair':
                    type_name = "头发"
                elif cloth_type == 'Hair_preset':
                    type_name = "头发预设"
                elif cloth_type == 'Morphs_preset':
                    type_name = "变形预设"
                elif cloth_type == 'pose':
                    type_name = "姿势"
                elif cloth_type == 'Skin':
                    type_name = "皮肤"
                elif cloth_type == 'CustomUnityAsset':
                    type_name = "资产"
                elif cloth_type == 'Scene':
                    type_name = "场景"

                info_text = f"{type_name}\n{subdir}/\n{base_name}"
                info_label = QLabel(info_text)
                info_label.setAlignment(Qt.AlignCenter)
                info_label.setWordWrap(True)
                info_label.setStyleSheet("font-size: 24px; margin-top: 5px;")
                
                layout.addWidget(image_label)
                layout.addWidget(info_label)
                
                return widget
            
            def show_single_image(self, image_label):
                """显示单张图片大图 - 使用通用查看器"""
                if hasattr(image_label, 'original_pixmap'):
                    title = f"{image_label.base_name} - {image_label.subdir}"
                    # 使用通用的图片查看器，传入原始pixmap
                    self.parent().show_single_image_viewer(None, title, image_label.original_pixmap)
            
            # 缩放方法保持不变...
            def zoom_in(self):
                self.current_scale *= 1.2
                self.apply_zoom_to_all()
                self.zoom_slider.setValue(int(self.current_scale * 100))
            
            def zoom_out(self):
                self.current_scale /= 1.2
                self.apply_zoom_to_all()
                self.zoom_slider.setValue(int(self.current_scale * 100))
            
            def reset_zoom(self):
                self.current_scale = 1.0
                self.apply_zoom_to_all()
                self.zoom_slider.setValue(100)
            
            def slider_zoom(self, value):
                self.current_scale = value / 100.0
                self.apply_zoom_to_all()
            
            def apply_zoom_to_all(self):
                for i in range(self.grid_layout.count()):
                    item = self.grid_layout.itemAt(i)
                    if item:
                        widget = item.widget()
                        if widget:
                            image_label = widget.layout().itemAt(0).widget()
                            if hasattr(image_label, 'original_pixmap'):
                                original_pixmap = image_label.original_pixmap
                                new_width = int(600 * self.current_scale)
                                new_height = int(600 * self.current_scale)
                                scaled_pixmap = original_pixmap.scaled(
                                    new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
                                )
                                image_label.setPixmap(scaled_pixmap)
        
        # 创建并显示图片查看器
        if any(self.all_clothing_data.values()):
            viewer = AllClothingImageViewer(self.all_clothing_data, self)
            viewer.exec_()
        else:
            QMessageBox.information(self, '提示', '未找到任何服装图片')

    def show_clothing_images(self, clothing_type):
        """显示指定类型的服装图像"""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                   QScrollArea, QPushButton, QSlider, QGridLayout)
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPixmap, QImage
        
        class ClothingImageViewer(QDialog):
            def __init__(self, clothing_data, clothing_type, parent=None):
                super().__init__(parent)
                self.clothing_data = clothing_data
                self.clothing_type = clothing_type
                self.type_titles = {
                    'female': '女性服装',
                    'male': '男性服装', 
                }
                self.current_scale = 1.0
                self.initUI()
                
            def initUI(self):
                title = self.type_titles.get(self.clothing_type, self.clothing_type)
                self.setWindowTitle(f'{title}图像查看器')
                self.setGeometry(0, 0, 3840, 2160)
                
                layout = QVBoxLayout()
                
                # 控制按钮
                control_layout = QHBoxLayout()
                self.zoom_in_btn = QPushButton('放大')
                self.zoom_out_btn = QPushButton('缩小')
                self.reset_btn = QPushButton('重置大小')
                
                self.zoom_in_btn.clicked.connect(self.zoom_in)
                self.zoom_out_btn.clicked.connect(self.zoom_out)
                self.reset_btn.clicked.connect(self.reset_zoom)
                
                control_layout.addWidget(self.zoom_in_btn)
                control_layout.addWidget(self.zoom_out_btn)
                control_layout.addWidget(self.reset_btn)
                control_layout.addStretch()
                
                # 缩放滑块
                self.zoom_slider = QSlider(Qt.Horizontal)
                self.zoom_slider.setMinimum(10)
                self.zoom_slider.setMaximum(500)
                self.zoom_slider.setValue(100)
                self.zoom_slider.valueChanged.connect(self.slider_zoom)
                control_layout.addWidget(QLabel('缩放:'))
                control_layout.addWidget(self.zoom_slider)
                
                layout.addLayout(control_layout)
                
                # 图片显示区域
                scroll_area = QScrollArea()
                self.scroll_content = QWidget()
                self.grid_layout = QGridLayout(self.scroll_content)
                
                self.display_images()
                
                scroll_area.setWidget(self.scroll_content)
                scroll_area.setWidgetResizable(True)
                layout.addWidget(scroll_area)
                
                self.setLayout(layout)
            
            def display_images(self):
                """显示所有图片"""
                # 清空现有内容
                for i in reversed(range(self.grid_layout.count())): 
                    self.grid_layout.itemAt(i).widget().setParent(None)
                
                row, col = 0, 0
                max_cols = 3
                
                for subdir, data in self.clothing_data.items():
                    for base_name, item_data in data['items'].items():
                        if item_data['images']:
                            # 使用第一张图片
                            image_info = item_data['images'][0]
                            
                            # 创建图片显示部件
                            image_widget = self.create_image_widget(image_info, base_name, subdir)
                            self.grid_layout.addWidget(image_widget, row, col)
                            
                            col += 1
                            if col >= max_cols:
                                col = 0
                                row += 1
                
                # 如果没有图片显示提示
                if self.grid_layout.count() == 0:
                    no_images_label = QLabel('未找到可显示的图片')
                    no_images_label.setAlignment(Qt.AlignCenter)
                    self.grid_layout.addWidget(no_images_label, 0, 0)
            
            def create_image_widget(self, image_info, base_name, subdir):
                """创建单个图片显示部件 - 添加点击事件"""
                from PyQt5.QtWidgets import QFrame
                
                widget = QFrame()
                widget.setFrameStyle(QFrame.Box)
                widget.setStyleSheet("border: 1px solid gray; margin: 5px; padding: 5px;")
                widget.setCursor(Qt.PointingHandCursor)  # 添加手型光标
                layout = QVBoxLayout(widget)
                
                # 图片标签
                image_label = QLabel()
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setStyleSheet("background-color: #f0f0f0;")
                
                # 存储图片信息用于点击事件
                image_label.image_info = image_info
                image_label.base_name = base_name
                image_label.subdir = subdir
                
                # 设置点击事件
                image_label.mousePressEvent = lambda e: self.show_single_image(image_label)
                
                # 尝试从VAR包加载图片
                try:
                    with zipfile.ZipFile(self.parent().current_var_file, 'r') as var_zip:
                        with var_zip.open(image_info['full_path']) as img_file:
                            image_data = img_file.read()
                            qimage = QImage()
                            qimage.loadFromData(image_data)
                            pixmap = QPixmap(qimage)
                            
                            # 缩放图片以适应显示
                            scaled_pixmap = pixmap.scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            image_label.setPixmap(scaled_pixmap)
                            image_label.original_pixmap = pixmap
                except Exception as e:
                    image_label.setText(f"无法加载图片\n{str(e)}")
                
                # 信息标签
                info_text = f"{subdir}/\n{base_name}"
                info_label = QLabel(info_text)
                info_label.setAlignment(Qt.AlignCenter)
                info_label.setWordWrap(True)
                info_label.setStyleSheet("font-size:24px; margin-top: 5px;")
                
                layout.addWidget(image_label)
                layout.addWidget(info_label)
                
                return widget
            
            # 缩放方法
            def zoom_in(self):
                self.current_scale *= 1.2
                self.apply_zoom_to_all()
                self.zoom_slider.setValue(int(self.current_scale * 100))
            
            def zoom_out(self):
                self.current_scale /= 1.2
                self.apply_zoom_to_all()
                self.zoom_slider.setValue(int(self.current_scale * 100))
            
            def reset_zoom(self):
                self.current_scale = 1.0
                self.apply_zoom_to_all()
                self.zoom_slider.setValue(100)
            
            def slider_zoom(self, value):
                self.current_scale = value / 100.0
                self.apply_zoom_to_all()
            
            def apply_zoom_to_all(self):
                for i in range(self.grid_layout.count()):
                    item = self.grid_layout.itemAt(i)
                    if item:
                        widget = item.widget()
                        if widget:
                            image_label = widget.layout().itemAt(0).widget()
                            if hasattr(image_label, 'original_pixmap'):
                                original_pixmap = image_label.original_pixmap
                                new_width = int(600 * self.current_scale)
                                new_height = int(600 * self.current_scale)
                                scaled_pixmap = original_pixmap.scaled(
                                    new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
                                )
                                image_label.setPixmap(scaled_pixmap)
            def show_single_image(self, image_label):
                """显示单张图片大图 - 使用通用查看器"""
                if hasattr(image_label, 'original_pixmap'):
                    title = f"{image_label.base_name} - {image_label.subdir}"
                    # 使用通用的图片查看器，传入原始pixmap
                    self.parent().show_single_image_viewer(None, title, image_label.original_pixmap)

        # 创建并显示图片查看器
        if clothing_type in self.all_clothing_data and self.all_clothing_data[clothing_type]:
            viewer = ClothingImageViewer(self.all_clothing_data[clothing_type], clothing_type, self)
            viewer.exec_()
        else:
            type_name = self.clothing_type_descriptions.get(clothing_type, clothing_type)
            QMessageBox.information(self, '提示',  f'未找到{type_name}图片')

    def classify_all_var_files(self):
        QMessageBox.information(self, '提示', '安全性考虑,该功能以封锁! 请手动打开源代码 取消classify_all_var_files的注释')

        # """按分数分类所有VAR文件 - 简化版"""
        # current_dir = Path(os.getcwd())
        # var_files = [f for f in current_dir.iterdir() if f.suffix.lower() == '.var']
        
        # if not var_files:
        #     QMessageBox.information(self, '提示', '当前目录没有找到VAR文件')
        #     return
        
        # success_count = 0
        # failed_files = []
        
        # for var_file in var_files:
        #     try:
        #         # 计算VAR文件的总分数
        #         total_score = self.calculate_var_score(var_file)
                
        #         # 根据分数确定目标目录
        #         target_folder = self.get_target_folder_by_score(total_score)
                
        #         # 移动文件
        #         target_dir = Path(target_folder)
        #         target_dir.mkdir(parents=True, exist_ok=True)
        #         shutil.move(str(var_file), str(target_dir / var_file.name))
        #         success_count += 1
                
        #         print(f"已移动 {var_file.name} 到 {target_folder} (分数: {total_score})")
                
        #     except Exception as e:
        #         failed_files.append(f"{var_file.name}: {str(e)}")
        #         print(f"移动文件 {var_file.name} 失败: {str(e)}")
        
        # # 显示结果
        # result_message = f'成功分类 {success_count} 个文件'
        # if failed_files:
        #     result_message += f'\n\n失败文件:\n' + '\n'.join(failed_files)
        
        # QMessageBox.information(self, '分类完成', result_message)
        # self.scan_var_files()

    def calculate_var_score(self, var_file):
        """计算VAR文件的总分数"""
        total_score = 0
        
        try:
            with zipfile.ZipFile(var_file, 'r') as zip_ref:
                file_list = [f.filename for f in zip_ref.infolist() if not f.is_dir()]
                
                # 计算所有组件的分数
                for component_path, info in self.component_weights.items():
                    if any(component_path in filename for filename in file_list):
                        total_score += info['weight']
                        
        except Exception as e:
            print(f"计算 {var_file.name} 分数失败: {str(e)}")
        
        return total_score

    def get_target_folder_by_score(self, score):
        """根据分数获取目标目录"""
        if score >= 1480:
            return "其他包/1_顶级场景" # 齐全
        elif score >= 58:
            return "其他包/1_顶级资源" # 外观+插件+姿势
        elif score >= 42:
            return "其他包/2_豪华资源" # 外观+头发
        elif score >= 28:
            return "其他包/3_完整资源" # 外观
        elif score >= 21:
            return "其他包/4_最低资源" # 服装
        elif score >= 14:
            return "其他包/4_最低资源" # 头发
        elif score >= 6:
            return "其他包/5_最低资源" # 变形
        else:
            return "其他包/垃圾资源"

    def extract_var(self):
        """解压VAR包到当前目录"""
        if not self.current_var_file:
            return
            
        try:
            with zipfile.ZipFile(self.current_var_file, 'r') as var_zip:
                extract_path = os.getcwd()
                var_zip.extractall(extract_path)
                
            QMessageBox.information(self, '成功', 
                                  f'已成功解压 {self.current_var_file} 到当前目录')
                    
        except Exception as e:
            QMessageBox.critical(self, '错误', f'解压失败: {str(e)}')

    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def is_image_file(self, filename):
        """检查文件是否为图像文件"""
        return any(filename.lower().endswith(ext) for ext in self.image_extensions)

    def darken_color(self, color):
        """加深颜色用于悬停效果"""
        import re
        match = re.match(r'#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})', color.lower())
        if match:
            r, g, b = [int(x, 16) for x in match.groups()]
            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)
            return f'#{r:02x}{g:02x}{b:02x}'
        return color

if __name__ == '__main__':
    app = QApplication(sys.argv)
    scanner = VarScanner()
    scanner.show()
    sys.exit(app.exec_())
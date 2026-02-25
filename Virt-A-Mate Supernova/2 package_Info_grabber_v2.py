import os
import json
import csv
import re
import shutil
from datetime import datetime

class VAMProcessor:
    def __init__(self):
        # 直接使用你的匹配规则
        self.type_rules = {
            '场景': [
                (r'Saves.*scene.*\.json', '场景配置'),
                (r'Saves.*scene.*\.jpg', '场景预览图'),
                (r'Saves.*scene.*\.mp3', '场景音乐'),
                (r'Saves.*scene.*\.wav', '场景音乐'),
                (r'Saves.*scene.*\.ogg', '场景音乐'),
            ],
            '变形': [
                (r'Custom/Atom/Person/Morphs.*\.jpg', '人物变形预览图'),
                (r'Custom/Atom/Person/Morphs.*', '人物变形文件夹'),
            ],
            '衣服': [
                (r'Custom/Atom/Person/Clothing/.*\.vap', '衣服预设'),
                (r'Custom/Atom/Person/Clothing/.*\.jpg', '衣服预设预览图'),
                (r'Custom.*Clothing.*\.(vaj|vab|vam)', '衣服文件'),
                (r'Custom.*Clothing.*\.jpg', '衣服预览图'),
                (r'Custom.*Clothing.*\.(vap)', '衣服文件的变颜色样式'),
            ],
            '纹理': [
                (r'Custom/Textures/.*\.(png|jpg|jpeg)', '其他服装需要的贴图'),
                (r'Custom.*Atom.*Person.*Textures', '纹理目录'),
                (r'Saves/Textures.*', '纹理目录'),
            ],
            '姿势': [
                (r'Saves/pose/.*\.jpg', '姿势文件'),
                (r'Custom/Atom/Person/Pose.*\.vap', '姿势文件'),
                (r'Custom/Atom/Person/Pose.*\.jpg', '姿势预览图'),
            ],
            '头发': [
                (r'Custom/Atom/Person/Hair/.*\.vap', '发型预设'),
                (r'Custom/Atom/Person/Hair/.*\.jpg', '发型预览图'),
                (r'Custom.*Hair/.*\.jpg', '发型预览图'),
                (r'Custom.*Hair/.*\.(vaj|vam|vab)', '头发文件'),
                (r'Custom.*Hair.*\.(vap)', '头发文件的变颜色样式'),
            ],
            '插件': [
                (r'Custom.*Scripts.*', '插件目录'),
                (r'Saves/PluginData.*', '插件数据'),
                (r'Custom/PluginPresets.*vap', '插件预设'),
                (r'Custom/PluginPresets.*jpg', '插件预设预览图'),
            ],
            '资产': [
                (r'Custom/Assets.*\.assetbundle', '资产'),
                (r'Custom/Assets.*\.jpg', '资产预览图'),
                (r'.*assetbundle', '资产'),
            ],
            '皮肤': [
                (r'Custom/Atom/Person/Skin.*vap', '皮肤预设'),
                (r'Custom/Atom/Person/Skin.*jpg', '皮肤预设预览图'),
            ],
            '外观': [
                (r'Saves/Person/appearance.*\.jpg', 'appearance'),
                (r'Saves/Person/appearance.*\.json', 'appearance'),
                (r'Custom/Atom/Person/Appearance.*\.vap', '外观'),
                (r'Custom/Atom/Person/Appearance.*\.jpg', '外观预览图'),
            ],
            '声音': [
                (r'Custom/Sounds.*', 'Sounds'),
                (r'Custom/Audio.*', 'Sounds'),
                (r'Custom/Sound.*', 'Sounds'),
            ],
            '其他-SubScene': [
                (r'Custom/SubScene/.*json', 'SubScene'),
                (r'Custom/SubScene/.*jpg', 'SubScene'),
            ],
            '其他-图片': [
                (r'Custom/Images.*', '随机图片'),
                (r'Custom/Atom/Wall.*', '随机壁画'),
                (r'Custom/Atom/ImagePanel.*', '其他'),
            ],
            'General': [
                (r'Custom/Atom/Person/General.*.jpg', 'General'),
                (r'Custom/Atom/Person/General.*.json', 'General'),
            ],
            '其他': []
        }
        
        # 图片复制目标目录映射
        self.copy_map = {
            '场景预览图': 'scene',
            '人物变形预览图': 'Morphs',
            '衣服预设预览图': 'Clothing_Preset',
            '衣服预览图': 'Clothing',
            '姿势预览图': 'Pose',
            '发型预览图': 'Hair_Preset',  # 优先Hair_Preset
            '发型预览图': 'Hair',         # 次选Hair
            '插件预设预览图': 'PluginPresets',
            '资产预览图': 'Assets',
            '皮肤预设预览图': 'Skin',
            'appearance': 'Appearance_json',
            '外观预览图': 'Appearance',
            'SubScene': 'SubScene',
            'General': 'General',
            '随机图片': 'Images',
            '随机壁画': 'Images',
            '其他': 'Images',
        }
        
        # 标签映射
        self.tag_map = {
            '场景配置': '场景',
            '场景音乐': '声音',
            '人物变形文件夹': '变形',
            '衣服预设': '衣服预设',
            '衣服文件': '衣服',
            '衣服文件的变颜色样式': '衣服',
            '其他服装需要的贴图': '纹理',
            '纹理目录': '纹理',
            '姿势文件': '姿势',
            '发型预设': '头发预设',
            '头发文件': '头发',
            '头发文件的变颜色样式': '头发',
            '插件目录': '插件',
            '插件数据': '插件',
            '插件预设': '插件预设',
            '资产': '资产',
            '皮肤预设': '皮肤预设',
            'appearance': '外观json',
            '外观': '外观预设',
            'Sounds': '声音',
            'SubScene': 'SubScene',
            'General': 'General',
        }
    
    def get_all_dependencies(self, dep_dict):
        """递归获取所有依赖项"""
        all_deps = []
        
        def _recursive_search(deps):
            for dep_name, dep_info in deps.items():
                all_deps.append(dep_name)
                if "dependencies" in dep_info and dep_info["dependencies"]:
                    _recursive_search(dep_info["dependencies"])
        
        if dep_dict:
            _recursive_search(dep_dict)
        return all_deps
    
    def get_all_dependencies_on_json(self,saves_directory):
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


    def process_package(self, var_file, unpack_dir, data_output_dir):
        """处理单个VAR包"""
        # 提取包信息
        parts = var_file[:-4].split(".")

        if len(parts) < 3:
            return None, 0, 0
        
        author = parts[0]
        package_name = parts[1]
        version = parts[2]
        
        # 查找meta.json获取依赖
        dependencies = []
        meta_path = os.path.join(unpack_dir, var_file[:-4], "meta.json")
        if os.path.exists(meta_path):
            print(meta_path)
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "dependencies" in data and data["dependencies"]:
                        deps = self.get_all_dependencies(data["dependencies"])
                        dependencies = list(set(deps))
                    else:
                        dependencies = ["无依赖"]

            except:
                try:
                    # 换编码试试
                    with open(meta_path, 'r', encoding='gb18030') as f:
                        data = json.load(f)
                        if "dependencies" in data and data["dependencies"]:
                            deps = self.get_all_dependencies(data["dependencies"])
                            dependencies = list(set(deps))
                        else:
                            dependencies = ["无依赖"]
                except:
                    try:
                        # 使用 utf-8-sig 自动处理 BOM
                        with open(meta_path, 'r', encoding='utf-8-sig') as f:
                            data = json.load(f)
                            if "dependencies" in data and data["dependencies"]:
                                deps = self.get_all_dependencies(data["dependencies"])
                                dependencies = list(set(deps))
                            else:
                                dependencies = ["无依赖"]
                    except:
                        dependencies = ["meta.json解析错误"] # 编码错误
        else:
            dependencies = ["无meta.json"] # 无文件，可能解压缩包是空的
        # # 查找saves下的json 获取额外的依赖,避免json加载失败，其他的如vap则无所谓。
        # try:
        #     resfff = self.get_all_dependencies_on_json(os.path.join(unpack_dir, var_file[:-4]))
        #     dependencies.extend(resfff)
        #     dependencies = list(set(dependencies))
        # except Exception as e:
        #     print(parts,"该文件出错了，请删除后复盘")
        #     print(str(e))

        # 处理包内容（图片复制和标签添加）
        tags = set()
        images_copied = 0
        package_dir = os.path.join(unpack_dir, var_file[:-4])
        
        if os.path.exists(package_dir):
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, package_dir)
                    norm_path = rel_path.replace('\\', '/')

                    # # 添加调试输出
                    # if file.lower().endswith('.jpg'):
                    #     print(f"\nDEBUG: 检查文件: {norm_path}")

                    # 匹配规则
                    matched = False
                    for category, rules in self.type_rules.items():
                        for pattern, label in rules:
                            if re.search(pattern, norm_path, re.IGNORECASE):
                                matched = True
                                
                                # 添加标签
                                if label in self.tag_map:
                                    tags.add(self.tag_map[label])

                                size_bytes = os.path.getsize(file_path)/(1024*1024)
                                if size_bytes>1:
                                    # print(size_bytes,"这张图片不用拷了,512x512的预览图，不可能尺寸超出1MB.唯一的可能性是:该图片不是预览图，而是皮肤纹理图等。漏网之鱼还有，后面还有别的清洗方式")
                                    # 某些可能会超出尺寸
                                    continue

                                # print(file_path)
                                # print(label)
                                if file_path.endswith('.jpg') and (label in ["衣服预览图","头发预览图"]): # 只匹配对应的文件,不要把服装纹理复制过来
                                    O = file_path.replace(".jpg",".vam")
                                    Of = file_path.replace(".jpg",".vap")
                                    if os.path.exists(O) or os.path.exists(Of):
                                        if file.lower().endswith(('.jpg', '.jpeg', '.png')) and label in self.copy_map:
                                            target_dir = os.path.join(
                                                os.getcwd(),
                                                data_output_dir, 
                                                author+"_"+package_name+"_", # windowd系统文件夹不能以空格结尾
                                                self.copy_map[label]
                                            )
                                            try:
                                                # print(target_dir)
                                                os.makedirs(target_dir, exist_ok=True)
                                                
                                                shutil.copy2(file_path, os.path.join(target_dir, file))
                                                images_copied += 1
                                            except Exception as e:
                                                print(str(e),1)
                                                os._exit(0)
                                else:
                                    if label not in ["衣服预览图","头发预览图","场景预览图"] :
                                        # 复制图片
                                        if file.lower().endswith(('.jpg', '.jpeg', '.png')) and label in self.copy_map:
                                            target_dir = os.path.join(
                                                os.getcwd(),
                                                data_output_dir, 
                                                author+"_"+package_name+"_", # windowd系统文件夹不能以空格结尾
                                                self.copy_map[label]
                                            )
                                            try:
                                                os.makedirs(target_dir, exist_ok=True)
                                            
                                                shutil.copy2(file_path, os.path.join(target_dir, file))
                                                images_copied += 1
                                            except Exception as e:
                                                print(str(e),2)
                                if label=="场景预览图":
                                    # 复制图片
                                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                                        O = file_path.replace(".jpg",".json")
                                        if os.path.exists(O):
                                            target_dir = os.path.join(
                                                os.getcwd(),
                                                data_output_dir, 
                                                author+"_"+package_name+"_", # windowd系统文件夹不能以空格结尾
                                                self.copy_map[label]
                                            )
                                            try:
                                                # print(target_dir)
                                                os.makedirs(target_dir, exist_ok=True)
                                                
                                                shutil.copy2(file_path, os.path.join(target_dir, file))
                                                images_copied += 1
                                            except Exception as e:
                                                print(str(e),3)
                                                os._exit(0)
                                break
                                
                        if matched:
                            break
            
            # # 更新meta.json标签
            # if tags and os.path.exists(meta_path):
            #     try:
            #         with open(meta_path, 'r', encoding='utf-8') as f:
            #             meta = json.load(f)
                    
            #         if 'tags' not in meta:
            #             meta['tags'] = []
                    
            #         existing_tags = set(meta['tags'])
            #         new_tags = set(tags)
            #         meta['tags'] = list(existing_tags.union(new_tags))
                    
            #         with open(meta_path, 'w', encoding='utf-8') as f:
            #             json.dump(meta, f, ensure_ascii=False, indent=2)
            #     except:
            #         pass
        tags.add("SD_未分类")
        # 返回结果
        return {
            'filename': var_file,
            'author': author,
            'package_name': package_name,
            'version': version,
            'dependencies': ",".join(dependencies),
            'tags': ",".join(tags) if tags else "无",
            'images_copied': str(images_copied),
            'processed_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, len(tags), images_copied

def main():
    with open("config.json", 'r', encoding='utf-8') as f:
        DATA = json.load(f)
    # 配置路径
    scan_dir = DATA["paths"]["var_scan_dir"]
    unpack_dir = DATA["paths"]["unzip_base_dir"]   
    output_csv = "var_packages.csv"
    data_output_dir = r"data"
    
    # 创建处理器
    processor = VAMProcessor()
    
    # 确保输出目录存在
    os.makedirs(data_output_dir, exist_ok=True)
    
    if not os.path.exists(scan_dir):
        print(f"目录不存在: {scan_dir}")
        return
    
    # 读取已存在的记录（用于去重）
    existing_files = set()
    if os.path.exists(output_csv):
        try:
            with open(output_csv, 'r', encoding='gb18030') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'filename' in row:
                        existing_files.add(row['filename'])
        except:
            pass
    files = os.listdir(scan_dir)
    total = len(files)
    results = []
    new_count = 0
    total_tags = 0
    total_images = 0
    
    print(f"开始处理{total}个VAR包...")
    # 添加计数器，控制进度条刷新频率
    last_update = 0
    update_interval = max(1, total // 1000)  # 每0.1%更新一次，或至少每处理1个文件

    for i, file in enumerate(files, 1):
        # # 调试
        # new_count += 1
        # if new_count <=1000:
        #     continue

        if file.endswith(".var"):
            # 检查是否已处理
            if file in existing_files:#  and ("KittyMocap.KM307_Slow_sensual_blowjob_.1.var"  not in file):
                # print(f"\r跳过已处理文件: {file[:30]}...", end="")
                continue
            
            # 处理包
            result, tags_count, images_count = processor.process_package(
                file, unpack_dir, data_output_dir
            )
            
            if result:
                results.append(result)
                new_count += 1
                total_tags += tags_count
                total_images += images_count
            # 控制进度条刷新频率
            if i - last_update >= update_interval or i == total:
                progress = i * 1000 // total
                bar_length = 50
                filled_length = int(bar_length * i // total)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                # print(f"\r进度: |{bar}| {i}/{total} [{progress}‰] 新增: {new_count} 图片: {total_images}", end="", flush=True)
                # last_update = i
                # print(f"\r[{i}/{total}] 处理: {file} 标签:{tags_count} 图片:{images_count}", end="")
    
    print()  # 换行
    
    # 保存到CSV
    if results:
        # 检查是否需要写入表头
        write_header = not os.path.exists(output_csv) or os.path.getsize(output_csv) == 0
        
        with open(output_csv, "a", newline="", encoding="gb18030") as f:
            fieldnames = ['filename', 'author', 'package_name', 'version', 
                         'dependencies', 'tags', 'images_copied', 'processed_time']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if write_header:
                writer.writeheader()
            
            writer.writerows(results)
        
        print(f"\n处理完成！")
        print(f"新增包数量: {new_count}")
        print(f"添加标签总数: {total_tags}")
        print(f"复制图片总数: {total_images}")
        print(f"已保存到: {output_csv}")
        print(f"总计记录: {len(existing_files) + new_count} 条")
    else:
        print("未找到新的.var文件")

if __name__ == "__main__":
    main()
input("按任意键退出")

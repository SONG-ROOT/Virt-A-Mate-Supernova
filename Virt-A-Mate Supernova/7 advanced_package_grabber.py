# "id" : "rHandControl"
import os
import zipfile
from tqdm import tqdm
import json
import shutil
from datetime import datetime
import re
import csv  # 添加csv模块

def get_json_contents(scene_dir):
    # pattern = '"id" : "rHandControl"'
    pattern = 'rHandControl' # 不知道这两种匹配方式会不会有漏网之鱼,先试试
    pattern1 = 'lHandAnimation'
    total_count = 0
    if_has_Animation = False
    for root, _, files in os.walk(scene_dir):
        for file in files:
            if file.lower().endswith('.json'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        total_count += content.count(pattern)
                        t = content.count(pattern1)
                        if t:
                            if_has_Animation = True
                        break  # 只处理第一个json文件
                except:
                    pass
        if total_count > 0:
            break
    # print(scene_dir,total_count)
    return total_count,if_has_Animation

# 检查文件是否已存在于CSV中
def is_file_already_processed(csv_filename, filename):
    if not os.path.exists(csv_filename):
        return False
    
    try:
        with open(csv_filename, 'r', encoding='gb18030', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['filename'] == filename:
                    return True
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")
    return False

# 读取已处理的文件名
def get_processed_filenames(csv_filename):
    processed_files = set()
    if not os.path.exists(csv_filename):
        return processed_files
    
    try:
        with open(csv_filename, 'r', encoding='gb18030', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                processed_files.add(row['filename'])
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")
    return processed_files

with open("config.json", 'r', encoding='utf-8') as f:
    DATA = json.load(f)

input_dir = DATA["paths"]["var_scan_dir"]
output_dir = DATA["paths"]["unzip_base_dir"]

# CSV文件名
csv_filename = "var_analysis_results.csv"

# 获取已处理的文件名
processed_files = get_processed_filenames(csv_filename)
print(f"已处理文件数: {len(processed_files)}")

# 获取input_dir目录下的所有文件
all_files = os.listdir(input_dir)

# 只取前100个文件，过滤掉已处理的
selected_files = [f for f in all_files[:] if f not in processed_files]

print(f"待处理文件数: {len(selected_files)}")

if not selected_files:
    print("没有需要处理的文件")

# 使用最简进度条处理这10个文件
c = 0
results = []  # 用于存储所有文件的分析结果

for filename in tqdm(selected_files, desc="处理文件"):
    tmp_new_tag = [] # 标签
    Creation_date = {} # 日期

    # 1 获取日期（从压缩包的meta.json中）
    var_file_path = os.path.join(input_dir, filename)
    creation_date = None
    try:
        with zipfile.ZipFile(var_file_path, 'r') as zip_ref:
            # 检查是否存在meta.json文件
            if 'meta.json' in zip_ref.namelist():
                # 获取meta.json的修改日期信息
                file_info = zip_ref.getinfo('meta.json')
                creation_date = datetime(*file_info.date_time)
                # print(filename,creation_date)
            else:
                file_list = zip_ref.namelist()
                if file_list:  # 确保压缩包不为空
                    first_file = file_list[0]
                    file_info = zip_ref.getinfo(first_file)
                    creation_date = datetime(*file_info.date_time)
    except Exception as e:
        print(f"读取{var_file_path}时发生错误: {e}")
    Creation_date['filename'] = creation_date

    # 2 扫描目录获取标签
    try:
        #  path_level_1可包含如下目录
        path_level_1_base_path = os.path.join(output_dir, filename.replace(".var",""))
        path_level_1 = os.listdir(path_level_1_base_path)
        # path_level_1_extra = ['Custom', 'meta.json', 'Saves',"__ID__.txt","AddonPackages","My Texture","LUT","TextureG","lut","tietu","Assets","LICENSE.md","updated.txt","My TEXTURE","Music"]
        path_level_1_extra = ['Custom', 'meta.json', 'Saves']
        # print(path_level_1)
        for i in path_level_1:
            if i not in path_level_1_extra:
                # print(filename,i)
                tmp_new_tag.append("一级宝箱")
                results.append({
                    'filename': filename,
                    'creation_date': creation_date.strftime('%Y-%m-%d %H:%M:%S') if creation_date else 'N/A',
                    'tags': ':::'.join(tmp_new_tag) if tmp_new_tag else '无标签',
                })
                continue
        # 只看Custom和Saves
        # 看Saves
        if 'Saves' in path_level_1:
            path_level_2 = os.listdir(os.path.join(path_level_1_base_path,"Saves"))
            if path_level_2!=['scene']:
                if "scene" not in path_level_2:
                    if "Person" not in path_level_2:
                        tmp_new_tag.append("二级Saves非人物宝箱")
                    else:
                        # 这是旧版本的人物资源,包含了pose,look和preset
                        path_level_3 = os.listdir(os.path.join(path_level_1_base_path,"Saves","Person"))
                        if path_level_3 == ['pose']:
                            tmp_new_tag.append("姿势旧包")
                        elif path_level_3 == ['appearance']:
                            tmp_new_tag.append("look旧包")
                        elif path_level_3 == ['full']:
                            tmp_new_tag.append("full旧包")
                        else:
                            tmp_new_tag.append("二级Saves人物宝箱")
                            # print(filename,path_level_3)
                else:
                    scene_dir = os.path.join(path_level_1_base_path, "Saves", "scene")
                    animatiom_numbers = get_json_contents(scene_dir)
                    if animatiom_numbers[0]==0:
                        tmp_new_tag.append("空环境包")
                    elif animatiom_numbers[0]==1:
                        tmp_new_tag.append("人物卡")
                    else:
                        tmp_new_tag.append("动作场景")
            else:
                scene_dir = os.path.join(path_level_1_base_path, "Saves", "scene")
                animatiom_numbers,if_has_Animation = get_json_contents(scene_dir)
                if not if_has_Animation:
                    if animatiom_numbers==0:
                        tmp_new_tag.append("空环境包")
                    elif animatiom_numbers==1:
                        tmp_new_tag.append("人物卡")
                    else:
                        tmp_new_tag.append("动作场景")
                else:
                    tmp_new_tag.append("动作场景")
                # print(filename,tmp_new_tag)
            results.append({
                'filename': filename,
                'creation_date': creation_date.strftime('%Y-%m-%d %H:%M:%S') if creation_date else 'N/A',
                'tags': ':::'.join(tmp_new_tag) if tmp_new_tag else '无标签',
            })
            continue
        # 看Custom
        if 'Custom' in path_level_1:
            path_level_2_base_path = os.path.join(path_level_1_base_path,"Custom")
            path_level_2 = os.listdir(path_level_2_base_path)
            if path_level_2 == ['Scripts']:
                tmp_new_tag.append("插件包")
            elif path_level_2 == ['Assets']:
                tmp_new_tag.append("资产包")
            elif path_level_2 == ['Clothing']:
                tmp_new_tag.append("服装包")
            elif path_level_2 == ['Hair']:
                tmp_new_tag.append("头发包")
            elif path_level_2 == ['SubScene']:
                tmp_new_tag.append("SubScene包")
            elif (path_level_2 == ['Sounds']) or (path_level_2 == ['Audio']):
                tmp_new_tag.append("声音包")
            elif path_level_2 == ['Clothing', 'Hair']:
                tmp_new_tag.append("头发衣服包")
            else:
                if "Atom" not in path_level_2:
                    if len(path_level_2) == 1:
                        tmp_new_tag.append("二级Custom非人物宝箱")
                    elif "Clothing" in path_level_2:
                        tmp_new_tag.append("衣服混合包")
                    else:
                        tmp_new_tag.append("二级Custom非人物宝箱")
                else:
                    # 可能和人相关的包
                    path_level_3_base_path = os.path.join(path_level_2_base_path,"Atom")
                    path_level_3 = os.listdir(path_level_3_base_path)
                    if "Person" not in path_level_3:
                        tmp_new_tag.append("三级Custom非人物宝箱")
                    elif "Person" in path_level_3:
                        path_level_4_base_path = os.path.join(path_level_3_base_path,"Person")
                        path_level_4 = os.listdir(path_level_4_base_path)
                        if path_level_2 == ['Atom', 'Clothing'] and path_level_4 == ['Clothing']:
                            tmp_new_tag.append("服装包")
                        elif path_level_2 == ['Atom', 'Hair'] and path_level_4 == ['Hair']:
                            tmp_new_tag.append("头发包")
                        elif path_level_2 == ['Atom', 'Scripts'] and path_level_4 == ['Morphs']:
                            tmp_new_tag.append("变形包")
                        elif path_level_2 == ['Atom'] and path_level_4 == ['Morphs']:
                            tmp_new_tag.append("变形包")
                        elif path_level_2 == ['Atom'] and path_level_4 == ['Pose']:
                            tmp_new_tag.append("姿势包")
                        elif path_level_2 == ['Atom'] and path_level_4 == ['Clothing']:
                            tmp_new_tag.append("服装包")
                        elif path_level_2 == ['Atom'] and path_level_4 == ['Textures']:
                            tmp_new_tag.append("纹理包")
                        elif path_level_2 == ['Atom'] and path_level_4 == ['Skin', 'Textures']:
                            tmp_new_tag.append("纹理包")
                        elif path_level_2 == ['Atom'] and path_level_4 == ['Hair']:
                            tmp_new_tag.append("头发包")
                        elif path_level_2 == ['Atom', 'Scripts'] and path_level_4 == ['Textures']:
                            tmp_new_tag.append("纹理包")
                        elif path_level_2 == ['Atom', 'Clothing', 'Hair'] and path_level_4 == ['Clothing', 'Hair']:
                            tmp_new_tag.append("头发衣服包")
                        elif path_level_2 == ['Atom'] and path_level_4 == ['Clothing', 'Hair']:
                            tmp_new_tag.append("头发衣服包")
                        elif path_level_2 == ['Atom', 'Scripts'] and path_level_4 == ['Plugins']:
                            tmp_new_tag.append("插件包")
                        elif path_level_2 == ['Atom'] and path_level_4 == ['Plugins']:
                            tmp_new_tag.append("插件包")

                        elif "Appearance" in path_level_4:
                            tmp_new_tag.append("look包")
                        elif path_level_2== ['Atom', 'Hair']:
                            tmp_new_tag.append("头发混合包")
                        elif path_level_2== ['Atom', 'Clothing', 'Hair']:
                            tmp_new_tag.append("头发衣服包")
                        elif "Clothing" in path_level_2:
                            tmp_new_tag.append("衣服混合包")
                        elif "Textures" in path_level_4:
                            tmp_new_tag.append("纹理混合包")
                        elif "Morphs" in path_level_4:
                            tmp_new_tag.append("变形混合包")
                        elif "Pose" in path_level_4:
                            tmp_new_tag.append("姿势混合包")
                        else:
                            tmp_new_tag.append("四级Custom人物宝箱")
                            # c+=1
                            # print(filename,path_level_2,path_level_4)
    except Exception as e:
        print(f"读取{filename}时发生错误: {e}")
    
    # 将结果保存到列表中
    results.append({
        'filename': filename,
        'creation_date': creation_date.strftime('%Y-%m-%d %H:%M:%S') if creation_date else 'N/A',
        'tags': ':::'.join(tmp_new_tag) if tmp_new_tag else '无标签',
    })

print(f"新处理文件数: {c}")

# 将结果追加保存到CSV文件
try:
    file_exists = os.path.exists(csv_filename)
    
    with open(csv_filename, 'a', newline='', encoding='gb18030') as csvfile:
        fieldnames = ['filename', 'creation_date', 'tags']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # 如果文件不存在，写入表头
        if not file_exists:
            writer.writeheader()
        
        # 写入新数据
        for result in results:
            writer.writerow(result)
    
    print(f"\n分析结果已保存到: {csv_filename}")
    print(f"本次处理 {len(results)} 个文件")
    print(f"总计已处理 {len(processed_files) + len(results)} 个文件")
except Exception as e:
    print(f"保存CSV文件时发生错误: {e}")

input("按任意键退出")

import os
import zipfile
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

with open("config.json", 'r', encoding='utf-8') as f:
    DATA = json.load(f)

input_dir = DATA["paths"]["var_scan_dir"]
output_dir = os.path.join(DATA["paths"]["output_base_dir"], "AddonPackages","Fake_packages")
extracted_dir = DATA["paths"]["unzip_base_dir"]

os.makedirs(output_dir, exist_ok=True)

var_files = [f for f in os.listdir(input_dir) if f.endswith('.var')]

def process_var(var):
    try:
        # 检查输出文件是否已存在
        output_file = os.path.join(output_dir, var)
        if os.path.exists(output_file):
            # 可选：也可以检查文件是否完整（比如验证zip文件）
            try:
                with zipfile.ZipFile(output_file, 'r') as test_z:
                    if 'meta.json' in test_z.namelist():
                        return True  # 文件已存在且包含meta.json，跳过
            except:
                # 文件可能损坏，重新处理
                pass
        
        # 检查meta.json是否存在
        meta = os.path.join(extracted_dir, var.replace('.var', ''), 'meta.json')
        if os.path.exists(meta):
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_STORED) as z:
                z.write(meta, 'meta.json')
            return True
        else:
            # 记录meta.json不存在的文件
            print(f"警告: {var} 对应的meta.json不存在")
            return False
    except Exception as e:
        print(f"处理 {var} 时出错: {str(e)}")
        return False

with ThreadPoolExecutor(max_workers=32) as executor:
    futures = [executor.submit(process_var, var) for var in var_files]
    results = list(tqdm(as_completed(futures), total=len(var_files), desc="处理VAR文件"))

success_count = sum(r.result() for r in results if r.result() is True)
print(f"完成 {success_count}/{len(var_files)} (已跳过已存在的文件)")
input("按任意键退出")

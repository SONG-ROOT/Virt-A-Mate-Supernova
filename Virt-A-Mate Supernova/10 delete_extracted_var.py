import os
import shutil
from tqdm import tqdm
import json

with open("config.json", 'r', encoding='utf-8') as f:
    DATA = json.load(f)

output_dir = os.path.join(DATA["paths"]["output_base_dir"], "AddonPackages", "Fake_packages")
keep = {"link-packages"}

for name in tqdm(os.listdir(output_dir)):
    if name not in keep:
        path = os.path.join(output_dir, name)
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        except:
            pass

input("按任意键退出")
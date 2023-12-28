import argparse
import os
from typing import List
from pydub import AudioSegment
from tqdm import tqdm
import shutil

def sync_list(mapping_path, folder_name):
    """根据文件夹中的文件同步mapping.list（移除不存在文件对应的行）"""
    mapping_dir = os.path.dirname(mapping_path)
    with open(mapping_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    new_lines:List[str] = []
    for line in tqdm(lines, desc=f"Processing {folder_name}", unit="line"):
        filename, text = line.strip().split("|")

        if os.path.exists(os.path.join(mapping_dir, filename)):
            new_lines.append(line)

    with open(mapping_path, 'w', encoding='utf-8') as file: # 原地修改 mapping 文件
        for line in new_lines:
            file.write(line.strip() + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="remove invalid lines from mapping.list which does not match the audio file")
    parser.add_argument("--target_dir", default="output", help="Path to dir to filter")
    args = parser.parse_args()

    for root, dirs, files in os.walk(args.target_dir):
        for folder in tqdm(dirs, desc="Merging folders", unit="folder"):
            sync_list(f"./{args.target_dir}/{folder}/new_mapping.list", folder)

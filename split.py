import os
import argparse
import shutil
import subprocess
from typing import List

from pydub import AudioSegment
from tqdm import tqdm


def time_to_milliseconds(time_str):
    h, m, s = map(float, time_str.split(":"))
    return int(h * 3600000 + m * 60000 + s * 1000)


def sanitize_filename(filename):
    # 过滤掉Windows上不允许的字符，并限制文件名的长度
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    return filename[:247]  # 247是为了保证后续可以添加后缀和索引

def split_wav_by_srt(srt_path:str, wav_path:str, output_folder:str, sample_rate:int, mono:bool, use_subtitle_as_name:bool, subtitle_offset:float=0):
    """根据srt文件切割wav文件"""
    mapping:List[str] = []

    def write_wav_file_from_seg():
        """把一个seg片段写入wav文件"""
        segment = audio[seg_start:seg_end]

        if mono:
            segment = segment.set_channels(1)

        if sample_rate:
            segment = segment.set_frame_rate(sample_rate)

        if use_subtitle_as_name:
            filename = sanitize_filename(seg_subtitle) + ".wav"
            idx = 1
            while os.path.exists(os.path.join(output_folder, prj_name, filename)):
                filename = sanitize_filename(seg_subtitle) + f"_{idx}.wav"
                idx += 1
        else:
            filename = f"{seg_start}_{seg_end}.wav"
            mapping.append(f"{filename}|{seg_subtitle}")

        if not os.path.exists(os.path.join(output_folder, prj_name)):
            os.makedirs(os.path.join(output_folder, prj_name))
        segment.export(os.path.join(output_folder, prj_name, filename), format="wav", parameters=["-sample_fmt", "s16"])


    with open(srt_path, 'r', encoding='utf-8') as file:
        content = file.read()
        blocks = content.strip().split("\n\n")
        audio = AudioSegment.from_wav(wav_path)
        prj_name = os.path.basename(wav_path)[:-4]

        seg_start:int = 0
        seg_end:int = 0
        seg_subtitle:str = ""
        for block in tqdm(blocks, desc=f"Processing {prj_name}"):
            lines = block.split("\n")
            times = lines[1].split("-->")
            start_time, end_time = [time_to_milliseconds(t.strip().replace(",", ".")) for t in times]
            start_time += int(subtitle_offset * 1000)
            end_time += int(subtitle_offset * 1000)
            subtitle = " ".join(lines[2:])

            # 剪映有把一句话拆成多条字幕的特性，因此必须考虑多条字幕对应一条语音的情况
            should_cut = False
            if seg_start == 0: # 第一条字幕
                seg_start = start_time
                seg_end = end_time
                seg_subtitle = subtitle
            else:
                if start_time == seg_end: # 两条字幕连续
                    seg_end = end_time
                    seg_subtitle += ',' + subtitle
                else:
                    should_cut = True

            if block == blocks[-1]: # 最后一条字幕，强制切割
                write_wav_file_from_seg()
            else:
                if not should_cut: # 不需要切割时，继续处理下一条字幕
                    continue
                
                # 先把上一条字幕对应的语音片段写入wav文件
                write_wav_file_from_seg()

                # 重置seg_start, seg_end, seg_subtitle
                seg_start = start_time
                seg_end = end_time
                seg_subtitle = subtitle

    if not use_subtitle_as_name:
        with open(os.path.join(output_folder, prj_name, "mapping.list"), "a", encoding="utf-8") as f:
            for line in mapping:
                f.write(line + "\n")


if __name__ == "__main__":
    print(os.getcwd())
    parser = argparse.ArgumentParser(description="Split WAVs based on SRT timings in a folder")
    parser.add_argument("--input_folder", type=str, default="input", help="Path to the input folder containing SRT and WAV files")
    parser.add_argument("--output_folder", type=str, default="output", help="Output folder path")
    parser.add_argument("--sample_rate", type=int, default=44100, help="Sample rate for output WAVs")
    parser.add_argument("--mono", action="store_true", help="Convert to mono")
    parser.add_argument("--use_subtitle_as_name", action="store_true", help="Use subtitle as filename")
    parser.add_argument("--subtitle_offset", type=float, default=0, help="subtitle offset in seconds")

    args = parser.parse_args()

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
    else:
        print(f'检测到"{args.output_folder}" 已存在，执行删除')
        shutil.rmtree(args.output_folder)
        os.makedirs(args.output_folder)
        
    for root, dirs, files in os.walk(args.input_folder):
        for file in files:
            if file.endswith(".srt"):
                wav_file = file.replace(".srt", ".wav")
                flac_file = file.replace(".srt", ".flac")
                wav_created = False
                
                if wav_file in files or flac_file in files:
                    if not wav_file in files: # 存在flac文件, 但不存在wav文件，先转成wav文件
                        subprocess.check_call(f'ffmpeg -i "{os.path.join(root, flac_file)}" "{os.path.join(root, wav_file)}"')
                        wav_created = True

                    split_wav_by_srt(os.path.join(root, file), os.path.join(root, wav_file), args.output_folder,
                                      args.sample_rate, args.mono, args.use_subtitle_as_name,
                                      args.subtitle_offset)
                    
                if wav_created:
                    os.remove(os.path.join(root, wav_file))

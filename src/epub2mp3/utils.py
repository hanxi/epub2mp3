import re
import os
import tempfile
import subprocess
from typing import Tuple, List
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT, Encoding
from imageio_ffmpeg import get_ffmpeg_exe


def clean_html(raw_html: str) -> str:
    """清理 HTML 标签，只保留文本内容"""
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext.strip()


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', "", filename)


def get_chapters(epub_path: str) -> List[Tuple[str, str]]:
    """从 EPUB 文件中提取章节内容"""
    book = epub.read_epub(epub_path)
    chapters = []

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")

            title = soup.find(["h1", "h2", "h3"])
            if title:
                title = clean_html(str(title))
            else:
                title = f"Chapter_{len(chapters) + 1}"

            content = clean_html(str(soup.body))

            if content.strip():
                chapters.append((title, content))

    return chapters


def ensure_output_dir(output_dir: str) -> None:
    """确保输出目录存在"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)


def make_lrc_lines_by_duration(text: str, duration_sec: int):
    """
    生成LRC歌词，将所有歌词放在第一秒到最后一秒之间显示，去除换行符

    参数:
    text: str - 包含歌词的文本
    duration_sec: int - 音频总时长（秒）

    返回:
    str - 格式化的LRC歌词文本（只有开始和结束两行）
    """
    # 清理文本：去除多余空白，将换行替换为空格
    cleaned_text = " ".join(text.split())

    if not cleaned_text:
        return ""

    # 创建开始时间戳 (第1秒)
    start_tag = "[00:01.00]"

    # 创建结束时间戳 (最后1秒)
    mm = (duration_sec - 1) // 60
    ss = (duration_sec - 1) % 60
    end_tag = f"[{mm:02d}:{ss:02d}.00]"

    # 返回包含开始和结束时间戳的歌词
    return f"{start_tag}{cleaned_text}\n{end_tag}"


def write_lyrics_to_mp3(mp3_path: str, lyrics_text: str):
    """将文本作为带均匀时间标签的歌词写入mp3的歌词标签"""
    try:
        audio = MP3(mp3_path, ID3=ID3)
        duration = int(audio.info.length)
        # 增加一个健壮性检查，防止时长过短导致除零等错误
        if duration < 1:
            print(f"[{mp3_path}] 写入歌词标签失败: 音频时长过短 (小于1秒)。")
            return
        lrc_text = make_lrc_lines_by_duration(lyrics_text, duration)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall("USLT")
        audio.tags.add(
            USLT(encoding=Encoding.UTF8, lang="chi", desc="epub2mp3", text=lrc_text)
        )
        audio.save()
        print(f"[{mp3_path}] 歌词标签写入成功")
    except Exception as e:
        print(f"[{mp3_path}] 写入歌词标签失败: {e}")


def convert_mp3_high_quality(input_mp3, bitrate="320k", samplerate="48000"):
    """
    用ffmpeg把mp3转为最高比特率和采样率（如320kbps/48kHz）
    直接修改原始文件
    """
    try:
        # 获取ffmpeg可执行文件路径
        ffmpeg_path = get_ffmpeg_exe()

        # 在临时目录创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            temp_output = tmp_file.name

        cmd = [
            ffmpeg_path,
            "-y",
            "-i",
            input_mp3,
            "-ar",
            samplerate,
            "-b:a",
            bitrate,
            "-map_metadata",
            "0",
            temp_output,
        ]

        # 执行命令
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # 用临时文件替换原文件
        os.replace(temp_output, input_mp3)

        print(f"[{input_mp3}] 已提升到 {bitrate}, {samplerate}Hz")

    except Exception as e:
        # 确保清理临时文件
        if "temp_output" in locals():
            try:
                os.remove(temp_output)
            except:
                pass
        print(f"[{input_mp3}] 码率/采样率提升失败: {e}")


def add_bgm(
    main_audio: str,
    bgm_audio: str,
    main_volume: float = 1.0,
    bgm_volume: float = 0.25,
    loop_bgm: bool = True,
):
    """
    使用 FFMPEG 为主音频文件添加背景音乐，并直接覆盖原文件。

    警告: 此操作会修改 `main_audio` 文件，建议在操作前进行备份。

    Args:
        main_audio (str): 主音频文件路径 (将被覆盖)。
        bgm_audio (str): 背景音乐文件路径。
        main_volume (float, optional): 主音频的音量 (1.0 代表原始音量)。默认为 1.0。
        bgm_volume (float, optional): 背景音乐的音量。默认为 0.25。
        loop_bgm (bool, optional): 如果背景音乐比主音频短，是否循环。默认为 True。

    Returns:
        bool: 如果成功返回 True，否则返回 False。
    """
    # 1. 检查输入文件是否存在
    if not os.path.exists(main_audio):
        print(f"错误: 主音频文件未找到 -> {main_audio}")
        return False
    if not os.path.exists(bgm_audio):
        print(f"错误: 背景音乐文件未找到 -> {bgm_audio}")
        return False

    # 2. 创建一个安全的临时文件来存放混合后的输出
    # 使用 tempfile 模块可以保证文件名唯一，避免冲突
    # delete=False 让我们能控制何时删除它
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_output_path = temp_file.name
    temp_file.close()  # 关闭文件句柄，以便 FFMPEG 可以写入

    # 获取ffmpeg可执行文件路径
    ffmpeg_path = get_ffmpeg_exe()

    try:
        # 3. 构建 FFMPEG 命令，输出到临时文件
        command = [ffmpeg_path]
        command.extend(["-i", main_audio])

        if loop_bgm:
            command.extend(["-stream_loop", "-1"])

        command.extend(["-i", bgm_audio])

        filter_complex = (
            f"[0:a]volume={main_volume}[main];"
            f"[1:a]volume={bgm_volume}[bg];"
            f"[main][bg]amix=inputs=2:duration=shortest[out]"
        )

        command.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[out]",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "-y",
                temp_output_path,  # 输出到临时文件
            ]
        )

        # 4. 执行命令
        print("正在混合音频到临时文件...")
        print(" ".join(command))

        result = subprocess.run(command, check=True, capture_output=True, text=True)

        # 5. 如果 FFMPEG 成功，用临时文件替换原始文件
        print("混合成功。正在替换原始文件...")
        # os.replace() 是一个原子操作，比先删除后重命名更安全
        os.replace(temp_output_path, main_audio)
        print(f"成功！文件 '{main_audio}' 已被添加背景音乐并覆盖。")
        return True

    except FileNotFoundError:
        print("错误: 'ffmpeg' 命令未找到。请确保 FFMPEG 已安装并已添加到系统 PATH。")
        return False
    except subprocess.CalledProcessError as e:
        print("FFMPEG 执行出错。原始文件未被修改。")
        print("返回码:", e.returncode)
        print("错误输出 (stderr):\n", e.stderr)
        return False
    except Exception as e:
        print(f"发生未知错误: {e}。原始文件未被修改。")
        return False
    finally:
        # 6. 无论成功与否，都清理临时文件
        if os.path.exists(temp_output_path):
            # print(f"清理临时文件: {temp_output_path}")
            os.remove(temp_output_path)

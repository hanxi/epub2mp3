import asyncio
import os
import random
from typing import Optional
import edge_tts
import argparse
from .utils import (
    get_chapters,
    sanitize_filename,
    ensure_output_dir,
    write_lyrics_to_mp3,
    convert_mp3_high_quality,
    add_bgm,
)
import time


class EpubToMP3Converter:
    def __init__(
        self,
        voice: str,
        output_dir: str,
        max_retries: int = 3,
        bg_dir=None,
    ):
        self.voice = voice
        self.output_dir = output_dir
        self.max_retries = max_retries
        self.bg_files = None
        if bg_dir and os.path.isdir(bg_dir):
            self.bg_files = [
                os.path.join(bg_dir, f)
                for f in os.listdir(bg_dir)
                if os.path.isfile(os.path.join(bg_dir, f))
                and f.lower().endswith(".mp3")
            ]
        ensure_output_dir(output_dir)

    async def text_to_speech_with_retry(self, text: str, output_file: str) -> None:
        """将文本转换为语音，带重试机制"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                print(f"[{output_file}] Attempt {attempt + 1}/{self.max_retries}")
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(output_file)
                print(f"[{output_file}] Conversion successful")
                return

            except Exception as e:
                last_exception = e
                print(f"[{output_file}] Attempt {attempt + 1} failed: {str(e)}")

            # 如果失败了,等待后重试
            if attempt < self.max_retries - 1:  # 如果不是最后一次尝试
                wait_time = 2**attempt
                print(f"[{output_file}] Waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)

        print(f"[{output_file}] All attempts failed")
        raise last_exception

    async def convert_epub(self, epub_path: str) -> None:
        """转换 EPUB 文件为 MP3"""
        if not os.path.exists(epub_path):
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")

        chapters = get_chapters(epub_path)
        tasks = []
        failed_chapters = []

        for i, (title, content) in enumerate(chapters, 1):
            safe_title = sanitize_filename(title)
            filename = f"{i:03d}_{safe_title}.mp3"
            output_path = os.path.join(self.output_dir, filename)

            print(f"Processing chapter {i}: {title}")

            # 如果文件已存在且大小正常，跳过处理
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"Chapter {i} already exists, skipping...")
                continue

            task = asyncio.create_task(
                self.process_chapter(i, title, content, output_path, failed_chapters)
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        # 报告失败的章节
        if failed_chapters:
            print("\nThe following chapters failed to convert:")
            for chapter in failed_chapters:
                print(f"- Chapter {chapter}")

    async def process_chapter(
        self,
        index: int,
        title: str,
        content: str,
        output_path: str,
        failed_chapters: list,
    ) -> None:
        """处理单个章节的转换，包含错误处理"""
        try:
            await self.text_to_speech_with_retry(content, output_path)
            if self.bg_files and len(self.bg_files) > 0:
                bg_path = random.choice(self.bg_files)
                add_bgm(output_path, bg_path)
            convert_mp3_high_quality(output_path)
            write_lyrics_to_mp3(output_path, content)
            print(f"Successfully converted chapter {index}: {title}")
        except Exception as e:
            print(f"Failed to convert chapter {index}: {title}")
            print(f"Error: {str(e)}")
            failed_chapters.append(index)


def main():
    parser = argparse.ArgumentParser(
        description="将 EPUB 电子书转换为 MP3 音频文件，每章一个文件。",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("epub_path", type=str, help="要转换的 EPUB 文件的路径。")

    parser.add_argument(
        "-v",
        "--voice",
        type=str,
        default="zh-CN-YunxiaNeural",
        help=(
            "用于文本转语音的 Edge TTS 声音。\n"
            "例如: zh-CN-YunxiNeural, en-US-AriaNeural\n"
            "使用 'edge-tts --list-voices' 命令查看所有可用声音。\n"
            "默认值: zh-CN-YunxiaNeural"
        ),
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="output_audio",
        help="保存生成的 MP3 文件的目录。\n默认值: output_audio",
    )

    parser.add_argument(
        "-r",
        "--retries",
        type=int,
        default=3,
        help="转换失败时的最大重试次数。\n默认值: 3",
    )

    parser.add_argument(
        "-b",
        "--bg-dir",
        type=str,
        help="背景音乐文件所在目录，如果指定，程序会随机选择一个背景音乐添加到每个章节的音频中。\n默认不添加背景音乐。",
    )

    args = parser.parse_args()

    converter = EpubToMP3Converter(
        voice=args.voice,
        output_dir=args.output_dir,
        max_retries=args.retries,
        bg_dir=args.bg_dir if "bg_dir" in args else None,
    )

    try:
        asyncio.run(converter.convert_epub(args.epub_path))
        print("\n转换完成！")
        print(f"所有音频文件已保存到目录: {os.path.abspath(args.output_dir)}")
    except FileNotFoundError as e:
        print(f"\n错误: {e}")
    except ValueError as e:
        print(f"\n错误: {e}")
    except Exception as e:
        print(f"\n转换过程中出现未知错误: {e}")


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()

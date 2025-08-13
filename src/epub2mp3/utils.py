import re
import os
from typing import Tuple, List
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub


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

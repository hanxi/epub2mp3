# epub2mp3

这是一个使用 Microsoft Edge TTS 服务将 EPUB 电子书转换为 MP3 音频文件的工具。它支持多种语音选项，具有并发处理、自动重试等特性，可以高效地将电子书转换为有声读物。

## 特性

- 支持多种微软 Edge TTS 语音选项
- 并发处理章节，提高转换效率
- 智能限流和重试机制
- 可自定义的输出目录和文件命名
- 支持断点续传（失败章节记录）

## 帮助

```
pdm start -h
usage: main.py [-h] [-v VOICE] [-o OUTPUT_DIR] [-c CONCURRENT] [-r RETRIES] epub_path

将 EPUB 电子书转换为 MP3 音频文件，每章一个文件。

positional arguments:
  epub_path             要转换的 EPUB 文件的路径。

options:
  -h, --help            show this help message and exit
  -v VOICE, --voice VOICE
                        用于文本转语音的 Edge TTS 声音。
                        例如: zh-CN-YunxiNeural, en-US-AriaNeural
                        使用 'edge-tts --list-voices' 命令查看所有可用声音。
                        默认值: zh-CN-YunxiaNeural
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        保存生成的 MP3 文件的目录。
                        默认值: output_audio
  -c CONCURRENT, --concurrent CONCURRENT
                        最大并发转换数量。
                        默认值: 3
  -r RETRIES, --retries RETRIES
                        转换失败时的最大重试次数。
                        默认值: 3
```

运行测试：

```shell
pdm start example/mc.epub
```

可以使用这个命令查看支持哪些语音：

```shell
pdm run edge-tts --list-voices
```

## 其他

可以配合 <https://github.com/freeok/so-novel> 下载小说，然后用本工具转换为有声读物。

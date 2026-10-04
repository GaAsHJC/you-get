# coding=utf-8

import json
import re

from ..common import (
    get_content,
    fake_headers,
    download_urls,
    playlist_not_supported,
    match1,
    get_location,
    url_size,
    print_info,
)

__all__ = ['xiaohongshu_download_by_url']


def xiaohongshu_download_by_url(url, **kwargs):
    # 1. 处理短链接，跳转到真实地址
    if 'xhslink.com' in url:
        url = get_location(url)

    print("✨ 小红书解析器启动！")
    print("📎 笔记地址:", url)

    # 2. 请求页面内容
    headers = fake_headers.copy()
    headers['Referer'] = 'https://www.xiaohongshu.com/'
    page_content = get_content(url, headers=headers)

    # 3. 调试：先看看整个页面 HTML 长什么样
    print("🔍 页面 HTML 长度:", len(page_content))
    print("🔍 页面前 1000 字符:", page_content[:1000])
    print("---")

    # 从页面里提取 __INITIAL_STATE__ JSON 数据
    match = re.search(r'window.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>', page_content, re.DOTALL)
    if not match:
        match = re.search(r'window.__INITIAL_SSR_STATE__\s*=\s*(\{.*?\})\s*</script>', page_content, re.DOTALL)

    # 额外找找：直接从 HTML 里搜视频 URL
    # 小红书的视频 CDN 地址通常是 xhscdn.com 域名下的
    video_urls = re.findall(r'https?://[^\s"\'<>]+?\.mp4[^\s"\'<>]*', page_content)
    if video_urls:
        print("✅ 直接在页面里找到了视频地址！")
        for i, url in enumerate(video_urls[:5]):
            print(f"  视频 {i+1}: {url[:100]}...")

    # 也找找图片地址
    image_urls = re.findall(r'https?://sns-[^\s"\'<>]+?xhscdn\.com[^\s"\'<>]+?\.(?:jpg|webp|png)[^\s"\'<>]*', page_content)
    if image_urls:
        print(f"✅ 找到了 {len(image_urls)} 张图片地址")
        for i, url in enumerate(image_urls[:3]):
            print(f"  图片 {i+1}: {url[:100]}...")

    if not match:
        print("❌ 没找到笔记数据，可能需要登录 cookie 或者小红书改了页面结构")
        return

    # 注意：小红书的 JSON 里可能有 undefined，不是合法 JSON，要先处理一下
    json_str = match.group(1).replace('undefined', 'null')
    data = json.loads(json_str)

    # 4. 调试：看看整个 JSON 的顶层有哪些 key
    print("🔍 页面数据顶层 keys:", list(data.keys()))

    # 试试 feed 里面
    feed_data = data.get('feed', {})
    print("🔍 feed 里的 keys:", list(feed_data.keys()))
    print("🔍 feed 内容预览:", json.dumps(feed_data, ensure_ascii=False)[:800])

    # 试试 board 里面
    board_data = data.get('board', {})
    print("🔍 board 里的 keys:", list(board_data.keys()))

    # 试试各种可能的路径
    note_data = data.get('note', {}).get('noteDetailMap', {})
    if not note_data:
        note_data = data.get('noteDetailMap', {})
    if not note_data:
        note_data = feed_data.get('noteDetailMap', {})

    if not note_data:
        print("❌ 笔记数据为空，我们刚才打印了上面的调试信息，看看数据藏哪儿了")
        return

    # 取第一个笔记
    first_note = list(note_data.values())[0]
    note = first_note.get('note', {})

    title = note.get('title', '小红书笔记')
    note_type = note.get('type', 'normal')  # normal=图文, video=视频

    print("📝 标题:", title)
    print("🎬 类型:", "视频" if note_type == 'video' else "图文")

    # 5. 如果是视频笔记，提取视频地址
    if note_type == 'video':
        video_info = note.get('video', {})
        media_stream = video_info.get('media', {}).get('stream', {})

        # 找最高清晰度的视频
        best_quality = None
        best_url = None
        for quality_name, quality_data in media_stream.items():
            if quality_data and len(quality_data) > 0:
                best_quality = quality_name
                best_url = quality_data[0].get('masterUrl')
                break

        if not best_url:
            print("❌ 没找到视频地址")
            return

        # 补全 URL（小红书的地址可能是相对路径）
        if best_url.startswith('//'):
            best_url = 'https:' + best_url

        size = url_size(best_url, faker=True)
        video_format = 'mp4'

        print_info(
            site_info='xiaohongshu.com',
            title=title,
            type=video_format,
            size=size
        )

        if not kwargs.get('info_only', False):
            download_urls(
                urls=[best_url],
                title=title,
                ext=video_format,
                total_size=size,
                headers=headers,
                **kwargs
            )

    else:
        # 图文笔记：下载所有图片
        image_list = note.get('imageList', [])
        print(f"🖼️  共 {len(image_list)} 张图片")

        for i, img in enumerate(image_list):
            img_url = img.get('urlDefault') or img.get('url')
            if img_url:
                print(f"  图片 {i+1}: {img_url}")

        print("💡 图文笔记下载功能待实现，先告诉你图片地址在这里")


download = xiaohongshu_download_by_url
download_playlist = playlist_not_supported('xiaohongshu')

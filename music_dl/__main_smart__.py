#!/usr/bin/env python
# -*- coding:utf-8 _*-
"""
@author: YeXiaoRain
@file: main_smart.py
@time: 2023-05-01
"""

import sys
import os
import gettext
import time
from typing import List, Tuple
import click
import logging
import prettytable as pt
import csv

from music_dl.song import BasicSong
from . import config
from .utils import colorize
from .source import MusicSource

gettext.install("music-dl", "locale")


@click.group()
@click.option("-v", "--verbose", default=False, is_flag=True, help=_("详细模式"))
@click.pass_context
def main_smart(ctx, verbose):
    config.init()
    config.set("lyrics", True)
    config.set("cover", True)

    ctx.obj = {"ms": MusicSource()}

    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)-8s | %(name)s: %(msg)s ",
        datefmt="%H:%M:%S",
    )


# @main_smart.command("url")
# @click.argument("url", type=str)
# @click.pass_context
# def smart_url(ctx, url: str):
#     """
#     Search and download music by url
#
#     Example:
#
#         playlist(kugou,163):
#
#         ./music-dl-smart url 'https://music.163.com/#/playlist?id=8366993012'
#
#         single song(163):
#
#         ./music-dl-smart url 'https://music.163.com/#/song?id=1878891006'
#     """
#     ms: MusicSource = ctx.obj["ms"]
#
#     # [TODO] other platform, and is single inner detect
#     SINGLE_163_PREFIX = "https://music.163.com/#/song?id="
#     if url.startswith(SINGLE_163_PREFIX):
#         song = ms.single(url)
#         song.download()
#     else:  # playlist
#         songs_list = ms.playlist(url)
#         print(songs_list)


def smart_down_fn(ms: MusicSource,
                  singer: str,
                  title: str,
                  source: str = "",
                  dry=False) -> Tuple[List[BasicSong], List[BasicSong]]:
    """
        返回 成功下载列表，完美匹配列表 
    """
    # 多于 4 个精确匹配则 放弃
    MAX_MATCH = 4

    songs_list: List[BasicSong] = ms.search(f"{title} {singer}",
                                            (source
                                             or config.get("source")).split())

    def is_match(o: BasicSong) -> bool:
        return o.title == title and o.singer == singer

    matched_list = [o for o in songs_list if is_match(o)]

    if dry:
        tb = pt.PrettyTable()
        tb.field_names = ["序号", "歌名", "歌手", "大小", "时长", "专辑", "来源", "是否完全匹配"]
        # 遍历输出搜索列表
        for index, song in enumerate(songs_list):
            song.idx = index
            tb.add_row(song.row + [is_match(song)])
            # click.echo(song.info)
        tb.align = "l"
        click.echo(tb)
        click.echo("")

        return [], matched_list
    else:
        if len(matched_list) > MAX_MATCH:
            return [], matched_list

        success_list: List[BasicSong] = []
        for item in matched_list:
            try:
                if item.download():
                    success_list.append(item)
            except Exception as e:
                # don't end program
                print(e, file=sys.stderr)

        return success_list, matched_list


@main_smart.command("down")
@click.argument("singer", type=str)
@click.argument("title", type=str)
@click.option("--dry", default=False, is_flag=True, help=_("不下载只查看"))
@click.option("-o", "--outdir", default=".", help=_("指定输出目录"))
@click.option(
    "-s",
    "--source",
    # default="qq netease kugou baidu",
    help=_("支持的数据源: ") + "qq netease kugou baidu",
)
@click.pass_context
def smart_down(ctx,
               singer: str,
               title: str,
               dry: bool,
               outdir: str,
               source: str = ""):
    """
    Search and download music by singer + title

    Example:

        ./music-dl-smart down 'G.E.M. 邓紫棋' 一路逆风 --dry

        ./music-dl-smart down 'G.E.M. 邓紫棋' 一路逆风

        ./music-dl-smart down 'G.E.M. 邓紫棋' 一路逆风 -s 'netease qq'
    """
    config.set("outdir", outdir)
    if not os.path.exists(outdir): os.makedirs(outdir)
    ms: MusicSource = ctx.obj["ms"]
    try:
        success_list = smart_down_fn(ms,
                                     singer=singer,
                                     title=title,
                                     source=source,
                                     dry=dry)
        print(success_list)
    except (EOFError, KeyboardInterrupt):
        sys.exit(1)


@main_smart.command("csvdown")
@click.argument("csvpath", type=str)
@click.option("--dry", default=False, is_flag=True, help=_("不下载只查看"))
@click.option("-o", "--outdir", default=".", help=_("指定输出目录"))
@click.option(
    "-s",
    "--source",
    # default="qq netease kugou baidu",
    help=_("支持的数据源(csv文件中的source优先级高于命令行): ") + "qq netease kugou baidu",
)
@click.pass_context
def smart_csvdown(ctx, csvpath: str, dry: bool, outdir: str, source: str = ""):
    """
    Search and download music by singer + title

    Example:

        ./music-dl-smart csvdown csvdemo.csv --dry

        ./music-dl-smart csvdown csvdemo.csv --dry -s 'netease qq'
    """
    config.set("outdir", outdir)
    if not os.path.exists(outdir): os.makedirs(outdir)
    ms: MusicSource = ctx.obj["ms"]
    l = []

    CSVHEADLINE = ["singer", "title", "source"]
    # read csv list
    with open(csvpath) as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        # skip first line which is title
        assert next(reader) == CSVHEADLINE
        for row in reader:
            if len(row) == len(CSVHEADLINE):
                l.append(row)
            else:
                print("BAD LINE: ", row)

    try:
        ok_list = [CSVHEADLINE]
        skip_list = [CSVHEADLINE]
        failed_list = [CSVHEADLINE]
        for singer, title, o_source in l:  # 文件中的source优先级 大于 命令行中source
            if os.path.exists(os.path.join(outdir, f'{singer} - {title}.mp3')):
                skip_list.append([singer, title, o_source])
                print(f"Skip {singer} - {title}")
                continue
            success_list, matched_list = smart_down_fn(ms,
                                                       singer=singer,
                                                       title=title,
                                                       source=o_source
                                                       or source,
                                                       dry=dry)
            for item in success_list:
                ok_list.append([singer, title, o_source or item.source])
            if len(success_list) == 0:
                failed_list.append([singer, title, o_source])
            time.sleep(0.5)
        if not dry:
            if len(ok_list) > 1:
                print("OK list:")
                writer = csv.writer(sys.stdout)  # 逗号分隔, 双引号包裹
                writer.writerows(ok_list)

            if len(skip_list) > 1:
                print("SKIP list:")
                writer = csv.writer(sys.stdout)  # 逗号分隔, 双引号包裹
                writer.writerows(skip_list)
            if len(failed_list) > 1:
                print("Failed list:")
                writer = csv.writer(sys.stdout)  # 逗号分隔, 双引号包裹
                writer.writerows(failed_list)
    except (EOFError, KeyboardInterrupt):
        sys.exit(1)


if __name__ == "__main__":
    main_smart()

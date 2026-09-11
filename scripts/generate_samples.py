#!/usr/bin/env python3
"""Create tiny, synthetic HWPX fixtures without publisher content."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"
 xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" secCnt="1">
 <hh:refList>
  <hh:fontfaces itemCnt="1"><hh:fontface lang="HANGUL" fontCnt="1"><hh:font id="0" face="Arial" type="TTF" isEmbedded="0"/></hh:fontface></hh:fontfaces>
  <hh:borderFills itemCnt="1"><hh:borderFill id="0" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0"/></hh:borderFills>
  <hh:charProperties itemCnt="1"><hh:charPr id="0" height="1000" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="0"><hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/></hh:charPr></hh:charProperties>
  <hh:tabProperties itemCnt="1"><hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/></hh:tabProperties>
  <hh:numberings itemCnt="0"/><hh:bullets itemCnt="0"/>
  <hh:paraProperties itemCnt="1"><hh:paraPr id="0" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="1"><hh:align horizontal="LEFT" vertical="BASELINE"/></hh:paraPr></hh:paraProperties>
  <hh:styles itemCnt="1"><hh:style id="0" type="PARA" name="바탕글" engName="Normal" paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0" langID="1042" lockForm="0"/></hh:styles>
 </hh:refList>
</hh:head>
"""

VERSION = """<?xml version="1.0" encoding="UTF-8"?>
<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" targetApplication="WORDPROCESSOR" major="5" minor="1" micro="0" buildNumber="1" os="1" xmlVersion="1.4" application="hwp-manage sample" appVersion="1.0"/>
"""

SETTINGS = """<?xml version="1.0" encoding="UTF-8"?>
<ha:HWPApplicationSetting xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"><ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/></ha:HWPApplicationSetting>
"""

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"><odf:file-entry odf:media-type="application/hwp+zip" odf:full-path="/"/><odf:file-entry odf:media-type="application/xml" odf:full-path="Contents/content.hpf"/></odf:manifest>
"""

# Public-domain 1x1 transparent PNG generated from raw bytes.
PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def section(text: str, with_image: bool) -> str:
    picture = ""
    if with_image:
        picture = """
 <hp:p id="2" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0"><hp:pic id="10" zOrder="0"><hp:img binaryItemIDRef="img1"/></hp:pic></hp:run>
 </hp:p>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
 <hp:p id="1" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0">
   <hp:secPr id="0" textDirection="HORIZONTAL" spaceColumns="0" tabStop="8000" outlineShapeIDRef="0" memoShapeIDRef="0" textVerticalWidthHead="0"><hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/><hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/><hp:pagePr landscape="WIDELY" width="59528" height="84186" gutterType="LEFT_ONLY"><hp:margin header="4252" footer="4252" gutter="0" left="8504" right="8504" top="5668" bottom="4252"/></hp:pagePr></hp:secPr>
   <hp:ctrl><hp:colPr id="0" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/></hp:ctrl>
   <hp:t>{escape(text)}</hp:t>
  </hp:run>
 </hp:p>{picture}
</hs:sec>
"""


def content(title: str, with_image: bool) -> str:
    image = (
        '    <opf:item id="img1" href="BinData/img1.png" media-type="image/png" isEmbeded="1"/>\n'
        if with_image
        else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<opf:package xmlns:opf="http://www.idpf.org/2007/opf/" version="" id="">
 <opf:metadata><opf:title>{escape(title)}</opf:title><opf:language>ko</opf:language></opf:metadata>
 <opf:manifest>
    <opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>
{image}    <opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>
    <opf:item id="settings" href="settings.xml" media-type="application/xml"/>
 </opf:manifest>
 <opf:spine><opf:itemref idref="header"/><opf:itemref idref="section0"/></opf:spine>
</opf:package>
"""


def create(path: Path, title: str, text: str, with_image: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", b"application/hwp+zip", compress_type=ZIP_STORED)
        archive.writestr("version.xml", VERSION)
        archive.writestr("settings.xml", SETTINGS)
        archive.writestr("META-INF/manifest.xml", MANIFEST)
        archive.writestr("Contents/header.xml", HEADER)
        archive.writestr("Contents/content.hpf", content(title, with_image))
        archive.writestr("Contents/section0.xml", section(text, with_image))
        archive.writestr("Preview/PrvText.txt", text + "\n")
        if with_image:
            archive.writestr("BinData/img1.png", PIXEL)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path("examples/sample_workspace")
    )
    args = parser.parse_args()
    base = (
        args.root
        / "목표2"
        / "국어 자료 변형 중간모음터"
        / "샘플 교과서"
    )
    create(base / "1단원" / "1.1_도입.hwpx", "도입", "합성 샘플 도입")
    create(
        base / "1단원" / "1.2_그림.hwpx",
        "그림",
        "합성 샘플 그림",
        with_image=True,
    )
    create(base / "2단원" / "2.1_정리.hwpx", "정리", "합성 샘플 정리")
    print(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

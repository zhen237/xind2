# -*- coding: utf-8 -*-
"""纯标准库将 Markdown 报告导出为 .docx（无需 python-docx 依赖）。

该模块仅依赖 Python 标准库（zipfile / re / xml.sax.saxutils），可在 QGIS 自带的
Python 环境中直接运行，避免对第三方包 python-docx 的依赖。

支持的 Markdown 语法（覆盖设计报告实际产出）：
  # / ## / ###           标题（-> Word Heading1/2/3）
  | a | b | / |---|---|  表格（首行为表头，带边框 + 表头底纹）
  > 引用                  引用段落（斜体）
  - 文本 / * 文本         列表项
  ---                     水平分隔线
  **粗体**               行内加粗
"""

import os
import re
import zipfile
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _esc(text):
    """转义 XML 文本中的特殊字符。"""
    return escape(str(text))


def _runs(text, bold=False):
    """将一段文本转为 Word <w:r> 序列，支持 **加粗** 标记。"""
    parts = re.split(r"\*\*(.+?)\*\*", text)
    out = []
    for i, part in enumerate(parts):
        if not part:
            continue
        is_bold = bold or (i % 2 == 1)
        rpr = "<w:rPr><w:b/></w:rPr>" if is_bold else ""
        out.append(
            "<w:r>%s<w:t xml:space=\"preserve\">%s</w:t></w:r>"
            % (rpr, _esc(part))
        )
    return "".join(out)


def _cell(text, bold=False, fill=None):
    shd = ('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % fill) if fill else ""
    tcpr = "<w:tcPr>%s</w:tcPr>" % shd
    return "<w:tc>%s<w:p>%s</w:p></w:tc>" % (tcpr, _runs(text, bold=bold))


def _table(rows):
    """将二维列表渲染为带边框的 Word 表格，首行为表头。"""
    ncols = max((len(r) for r in rows), default=1)
    borders = (
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        "</w:tblBorders>"
    )
    tblpr = (
        '<w:tblPr><w:tblW w:w="5000" w:type="pct"/>%s</w:tblPr>' % borders
    )
    grid = "<w:tblGrid>%s</w:tblGrid>" % "".join(
        '<w:gridCol w:w="%d"/>' % (9000 // ncols) for _ in range(ncols)
    )
    body = []
    for ri, row in enumerate(rows):
        is_header = ri == 0
        cells = [
            _cell(c, bold=is_header, fill=("D9E2F3" if is_header else None))
            for c in row
        ]
        while len(cells) < ncols:
            cells.append(_cell(""))
        body.append("<w:tr>%s</w:tr>" % "".join(cells))
    return "<w:tbl>%s%s%s</w:tbl>" % (tblpr, grid, "".join(body))


def _parse(md):
    """逐行解析 Markdown，返回 block 列表。

    每个 block 为 (kind, payload)：
      ('h1'|'h2'|'h3', text)
      ('p', text)  普通段落
      ('quote', text)
      ('list', text)
      ('hr', '')
      ('table', [[cell, ...], ...])
    """
    lines = md.split("\n")
    blocks = []
    i = 0
    n = len(lines)
    table_rows = None
    list_items = None

    def flush_table():
        nonlocal table_rows
        if table_rows:
            blocks.append(("table", table_rows))
            table_rows = None

    def flush_list():
        nonlocal list_items
        if list_items:
            for it in list_items:
                blocks.append(("list", it))
            list_items = None

    while i < n:
        raw = lines[i].rstrip()
        stripped = raw.strip()
        if not stripped:
            flush_table()
            flush_list()
            i += 1
            continue

        # 表格行（以 | 起止）
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # 分隔行（|---|---|）
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c != ""):
                i += 1
                continue
            if table_rows is None:
                table_rows = []
            table_rows.append(cells)
            i += 1
            continue
        else:
            flush_table()

        # 标题
        m = re.match(r"^(#{1,3})\s+(.*)$", raw)
        if m:
            level = len(m.group(1))
            blocks.append(("h%d" % level, m.group(2).strip()))
            i += 1
            continue

        # 引用
        if stripped.startswith(">"):
            flush_list()
            blocks.append(("quote", stripped.lstrip(">").strip()))
            i += 1
            continue

        # 水平线
        if re.fullmatch(r"-{3,}", stripped):
            flush_list()
            blocks.append(("hr", ""))
            i += 1
            continue

        # 列表项
        if re.match(r"^[\*\-]\s+", stripped):
            if list_items is None:
                list_items = []
            list_items.append(re.sub(r"^[\*\-]\s+", "", stripped))
            i += 1
            continue

        # 普通段落
        flush_list()
        blocks.append(("p", stripped))
        i += 1

    flush_table()
    flush_list()
    return blocks


def _render_block(block):
    kind = block[0]
    if kind in ("h1", "h2", "h3"):
        style = {"h1": "Heading1", "h2": "Heading2", "h3": "Heading3"}[kind]
        return (
            '<w:p><w:pPr><w:pStyle w:val="%s"/></w:pPr>%s</w:p>'
            % (style, _runs(block[1]))
        )
    if kind == "p":
        return "<w:p>%s</w:p>" % _runs(block[1])
    if kind == "quote":
        return (
            "<w:p><w:pPr><w:spacing w:before=\"120\" w:after=\"120\"/>"
            '<w:ind w:left="420"/></w:pPr>%s</w:p>'
            % _runs(block[1], bold=False)
        )
    if kind == "hr":
        return (
            "<w:p><w:pPr><w:pBdr><w:bottom w:val=\"single\" w:sz=\"6\" "
            'w:space="1" w:color="999999"/></w:pBdr></w:pPr></w:p>'
        )
    if kind == "list":
        return "<w:p><w:pPr><w:ind w:left=\"420\" w:hanging=\"240\"/></w:pPr>%s</w:p>" % _runs(
            "\u2022 " + block[1]
        )
    if kind == "table":
        return _table(block[1])
    return ""


_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="\u5b8b\u4f53" w:hAnsi="Calibri"/><w:sz w:val="21"/></w:rPr></w:rPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="200" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="23"/></w:rPr></w:style>
</w:styles>"""

_SECTPR = (
    '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
    'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
)


def markdown_to_docx(markdown_text, output_path):
    """将 Markdown 文本导出为 .docx 文件。

    :param markdown_text: 设计报告 Markdown 字符串
    :param output_path:   目标 .docx 路径（不存在父目录会自动创建）
    :return: output_path
    """
    blocks = _parse(markdown_text)
    body = "".join(_render_block(b) for b in blocks)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="%s"><w:body>%s%s</w:body></w:document>'
        % (W, body, _SECTPR)
    )

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/styles.xml", _STYLES)
        zf.writestr("word/_rels/document.xml.rels", _DOC_RELS)

    return output_path


if __name__ == "__main__":
    # 自测：生成一份示例 docx 验证结构合法性
    sample = (
        "# 通信设施智能设计方案报告\n\n"
        "> 生成时间：2026-08-14 | 数据来源：QGIS 插件本地汇总\n\n"
        "## 一、项目概况\n\n"
        "| 项目 | 内容 |\n|------|------|\n"
        "| 基站数量 | **12** 个 |\n| 机房数量 | 3 个 |\n\n"
        "## 二、建议\n\n"
        "- **覆盖连续性**：部署合理。\n"
        "- 建议后续路测验证。\n\n"
        "---\n\n"
        "*本报告由插件自动生成。*\n"
    )
    out = markdown_to_docx(sample, "sample_report.docx")
    print("written:", out)

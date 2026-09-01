package com.comm.s3.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.comm.s3.entity.S3ReviewResult;
import com.comm.s3.entity.S3ReviewTask;
import com.lowagie.text.Chunk;
import com.lowagie.text.Document;
import com.lowagie.text.Element;
import com.lowagie.text.Font;
import com.lowagie.text.PageSize;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Phrase;
import com.lowagie.text.pdf.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * B-3 PDF 导出：基于 OpenPDF 将审查报告渲染为符合工程归档规范的 PDF（A4，含规范页眉/页脚页码）。
 * 数据直接取自 MySQL（任务 / 结果 / 设计元数据），无需回源 Python。
 * 中文通过内嵌 CJK 字体解决（classpath 字体优先 → 配置路径 → 系统字体回退）。
 */
@Service
@Slf4j
public class PdfExportService {

    @Autowired
    private S3ReviewTaskService s3ReviewTaskService;
    @Autowired
    private S3ReviewResultService s3ReviewResultService;
    @Autowired
    private ReviewService reviewService;

    @Value("${pdf.font-path:C:/Windows/Fonts/msyh.ttc}")
    private String configuredFontPath;

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static final Color HEADER_BG = new Color(0x1f, 0x3a, 0x5f);
    private static final Color LABEL_BG = new Color(0xee, 0xf4, 0xfb);
    private static final Color BORDER = new Color(0xd3, 0xdc, 0xe6);
    private static final Color MUTED = new Color(0x5a, 0x6b, 0x7b);

    public byte[] exportTaskReport(Long taskId) {
        S3ReviewTask task = s3ReviewTaskService.getById(taskId);
        if (task == null) {
            throw new IllegalArgumentException("审查任务不存在: " + taskId);
        }

        // 结果按风险等级降序（critical > error > warning > pending），过滤掉 SYSTEM 伪行
        List<S3ReviewResult> raw = s3ReviewResultService.list(
                new LambdaQueryWrapper<S3ReviewResult>()
                        .eq(S3ReviewResult::getTaskId, taskId)
                        .orderByDesc(S3ReviewResult::getRiskLevel)
        );
        List<S3ReviewResult> results = new ArrayList<>();
        int critical = 0, error = 0, warning = 0, pending = 0;
        for (S3ReviewResult r : raw) {
            if ("SYSTEM".equals(r.getRuleCode())) continue;
            results.add(r);
            if ("critical".equals(r.getRiskLevel())) critical++;
            else if ("error".equals(r.getRiskLevel())) error++;
            else if ("warning".equals(r.getRiskLevel())) warning++;
            else if ("pending".equals(r.getRiskLevel())) pending++;
        }

        Map<String, Object> designMeta = reviewService.getDesignMeta(taskId);
        if (designMeta == null) designMeta = Collections.emptyMap();

        BaseFont cjk = loadCjkBaseFont();

        try {
            Document document = new Document(PageSize.A4, 36, 36, 42, 42);
            ByteArrayOutputStream os = new ByteArrayOutputStream();
            PdfWriter writer = PdfWriter.getInstance(document, os);
            document.open();

            final Font footerFont = f(cjk, 8, Font.NORMAL, new Color(0x7a, 0x87, 0x94));
            final PdfTemplate totalTpl = writer.getDirectContent().createTemplate(24, 14);
            writer.setPageEvent(new PdfPageEventHelper() {
                @Override
                public void onEndPage(PdfWriter w, Document d) {
                    PdfContentByte cb = w.getDirectContent();
                    float midX = (d.left() + d.right()) / 2;
                    // 页眉
                    ColumnText.showTextAligned(cb, Element.ALIGN_CENTER,
                            new Phrase("通信基础设施设计智能审查报告", footerFont), midX, d.top() + 14, 0);
                    // 页脚左：系统名
                    ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                            new Phrase("S3 设计智能审查系统 · 自动生成", footerFont), d.left(), d.bottom() - 14, 0);
                    // 页脚中：页码
                    String pg = "第 " + w.getPageNumber() + " 页 / 共 ";
                    float pgW = cjk != null ? cjk.getWidthPoint(pg, 8) : pg.length() * 4f;
                    ColumnText.showTextAligned(cb, Element.ALIGN_CENTER, new Phrase(pg, footerFont), midX, d.bottom() - 14, 0);
                    cb.addTemplate(totalTpl, midX + pgW, d.bottom() - 14);
                }

                @Override
                public void onCloseDocument(PdfWriter w, Document d) {
                    ColumnText.showTextAligned(totalTpl, Element.ALIGN_LEFT,
                            new Phrase(String.valueOf(w.getPageNumber()), footerFont), 0, 0, 0);
                }
            });

            // 标题
            Paragraph title = new Paragraph("通信基础设施设计智能审查报告", f(cjk, 18, Font.BOLD, HEADER_BG));
            title.setAlignment(Element.ALIGN_CENTER);
            document.add(title);
            Paragraph sub = new Paragraph("（依据 GB 50217 / GB 50169 / GB 51158 / GB 50373 等通信工程规范自动生成）",
                    f(cjk, 9, Font.NORMAL, MUTED));
            sub.setAlignment(Element.ALIGN_CENTER);
            sub.setSpacingAfter(12);
            document.add(sub);

            document.add(buildInfoTable(task, designMeta, cjk));
            document.add(buildStats(critical, error, warning, pending, cjk));

            Paragraph sec = new Paragraph("审查结果明细", f(cjk, 12, Font.BOLD, HEADER_BG));
            sec.setSpacingBefore(10);
            sec.setSpacingAfter(4);
            document.add(sec);
            document.add(buildResultTable(results, cjk));

            Paragraph note = new Paragraph(
                    "本审查报告由 S3 设计智能审查系统自动生成，结论基于设计数据与行业规范条款比对，仅供工程归档与人工复核参考。",
                    f(cjk, 8.5f, Font.NORMAL, MUTED));
            note.setSpacingBefore(14);
            document.add(note);

            document.close();
            return os.toByteArray();
        } catch (Exception e) {
            log.error("PDF 渲染失败 taskId={}: {}", taskId, e.getMessage(), e);
            throw new RuntimeException("PDF 渲染失败: " + e.getMessage(), e);
        }
    }

    private PdfPTable buildInfoTable(S3ReviewTask task, Map<String, Object> meta, BaseFont cjk) {
        PdfPTable table = new PdfPTable(4);
        table.setWidthPercentage(100);
        table.setWidths(new float[]{0.22f, 0.28f, 0.22f, 0.28f});
        table.setSpacingAfter(10);

        String projName = str(meta.get("projectName"));
        if ("-".equals(projName)) projName = str(meta.get("designTaskName"));
        if ("-".equals(projName)) projName = str(task.getTaskName());

        infoRow(table, "工程名称", projName, cjk);
        infoRow(table, "工程编号(S1)", str(coalesce(meta.get("designTaskId"), task.getDesignTaskId())), cjk);
        infoRow(table, "工程类型", str(meta.get("designType")), cjk);
        infoRow(table, "工程区域", str(meta.get("region")), cjk);
        infoRow(table, "审查任务ID", str(task.getId()), cjk);
        infoRow(table, "审查任务名称", str(task.getTaskName()), cjk);
        infoRow(table, "规则覆盖率", task.getCoverageRate() == null ? "-" : String.format("%.2f%%", task.getCoverageRate()), cjk);
        infoRow(table, "审查规则总数", str(task.getTotalCount()), cjk);

        Object lc = meta.get("layerCounts");
        String layerStr = "-";
        if (lc instanceof Map) {
            StringBuilder b = new StringBuilder();
            for (Map.Entry<?, ?> e : ((Map<?, ?>) lc).entrySet()) {
                if (b.length() > 0) b.append("，");
                b.append(str(e.getKey())).append(": ").append(str(e.getValue()));
            }
            if (b.length() > 0) layerStr = b.toString();
        }
        infoRow(table, "图层分布", layerStr, cjk);
        infoRow(table, "数据来源", str(meta.get("dataSource")), cjk);
        infoRow(table, "报告生成时间", LocalDateTime.now().format(FMT), cjk);
        return table;
    }

    private void infoRow(PdfPTable t, String label, String value, BaseFont cjk) {
        PdfPCell lc = new PdfPCell(new Phrase(label, f(cjk, 9.5f, Font.BOLD, new Color(0x2b, 0x3a, 0x4d))));
        lc.setBackgroundColor(LABEL_BG);
        lc.setPadding(5);
        PdfPCell vc = new PdfPCell(new Phrase(value, f(cjk, 9.5f, Font.NORMAL, Color.BLACK)));
        vc.setPadding(5);
        t.addCell(lc);
        t.addCell(vc);
    }

    private PdfPTable buildStats(int critical, int error, int warning, int pending, BaseFont cjk) {
        PdfPTable t = new PdfPTable(5);
        t.setWidthPercentage(100);
        t.setWidths(new float[]{0.2f, 0.2f, 0.2f, 0.2f, 0.2f});
        t.setSpacingAfter(10);
        statCell(t, String.valueOf(critical + error + warning), "违规总数", new Color(0x2c, 0x3e, 0x50), cjk);
        statCell(t, String.valueOf(critical), "严重(critical)", new Color(0xc0, 0x39, 0x2b), cjk);
        statCell(t, String.valueOf(error), "错误(error)", new Color(0xe6, 0x7e, 0x22), cjk);
        statCell(t, String.valueOf(warning), "警告(warning)", new Color(0xb8, 0x86, 0x0b), cjk);
        statCell(t, String.valueOf(pending), "待核查(pending)", new Color(0x7f, 0x8c, 0x8d), cjk);
        return t;
    }

    private void statCell(PdfPTable t, String num, String label, Color color, BaseFont cjk) {
        PdfPCell cell = new PdfPCell();
        cell.setPadding(8);
        cell.setBorderColor(BORDER);
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);
        Paragraph p = new Paragraph();
        p.add(new Chunk(num, f(cjk, 18, Font.BOLD, color)));
        p.add(Chunk.NEWLINE);
        p.add(new Chunk(label, f(cjk, 9, Font.NORMAL, MUTED)));
        cell.addElement(p);
        t.addCell(cell);
    }

    private PdfPTable buildResultTable(List<S3ReviewResult> results, BaseFont cjk) {
        PdfPTable table = new PdfPTable(7);
        table.setWidthPercentage(100);
        table.setWidths(new float[]{0.06f, 0.10f, 0.18f, 0.10f, 0.14f, 0.10f, 0.32f});
        table.setHeaderRows(1);
        table.setSpacingBefore(2);

        String[] headers = {"序号", "规则编号", "规则名称", "实际值", "标准值", "风险等级", "整改建议"};
        for (String h : headers) {
            PdfPCell c = new PdfPCell(new Phrase(h, f(cjk, 9.5f, Font.BOLD, Color.WHITE)));
            c.setBackgroundColor(HEADER_BG);
            c.setPadding(5);
            table.addCell(c);
        }

        if (results.isEmpty()) {
            PdfPCell c = new PdfPCell(new Phrase("无审查结果记录", f(cjk, 9.5f, Font.NORMAL, Color.BLACK)));
            c.setColspan(7);
            c.setPadding(12);
            table.addCell(c);
        } else {
            int idx = 1;
            for (S3ReviewResult r : results) {
                table.addCell(cell(String.valueOf(idx++), cjk, Element.ALIGN_CENTER));
                table.addCell(cell(str(r.getRuleCode()), cjk, Element.ALIGN_LEFT));
                table.addCell(cell(str(r.getRuleName()), cjk, Element.ALIGN_LEFT));
                table.addCell(cell(str(r.getActualValue()), cjk, Element.ALIGN_LEFT));
                table.addCell(cell(str(r.getStandardValue()), cjk, Element.ALIGN_LEFT));
                PdfPCell rc = new PdfPCell(new Phrase(riskText(r.getRiskLevel()), f(cjk, 9, Font.BOLD, riskColor(r.getRiskLevel()))));
                rc.setPadding(5);
                rc.setHorizontalAlignment(Element.ALIGN_CENTER);
                table.addCell(rc);
                table.addCell(cell(str(r.getRemark()), cjk, Element.ALIGN_LEFT));
            }
        }
        return table;
    }

    private PdfPCell cell(String text, BaseFont cjk, int align) {
        PdfPCell c = new PdfPCell(new Phrase(text, f(cjk, 9, Font.NORMAL, Color.BLACK)));
        c.setPadding(5);
        c.setHorizontalAlignment(align);
        return c;
    }

    /** 字体工厂：优先用内嵌 CJK 字体，缺失时回退 Helvetica（中文可能显示为空白/方块） */
    private Font f(BaseFont cjk, float size, int style, Color color) {
        if (cjk != null) return new Font(cjk, size, style, color);
        return new Font(Font.HELVETICA, size, style, color);
    }

    private BaseFont loadCjkBaseFont() {
        String fontFile = resolveFontFile();
        if (fontFile == null) {
            log.warn("未找到可用的 CJK 字体，PDF 中文可能显示为空白。请配置 pdf.font-path 或在 classpath:/fonts 放置 NotoSansSC 字体。");
            return null;
        }
        try {
            String ref = fontFile.toLowerCase().endsWith(".ttc") ? fontFile + ",0" : fontFile;
            BaseFont bf = BaseFont.createFont(ref, BaseFont.IDENTITY_H, BaseFont.EMBEDDED);
            log.info("PDF 渲染使用 CJK 字体: {}", fontFile);
            return bf;
        } catch (Exception e) {
            log.error("注册 CJK 字体失败 {}: {}", fontFile, e.getMessage(), e);
            return null;
        }
    }

    /** 字体解析优先级：classpath 字体 → 配置路径 → 常见系统字体 */
    private String resolveFontFile() {
        for (String name : new String[]{"NotoSansSC-Regular.ttf", "NotoSansSC-Regular.otf", "NotoSansCJKsc-Regular.otf"}) {
            try {
                ClassPathResource r = new ClassPathResource("/fonts/" + name);
                if (r.exists()) {
                    try {
                        return r.getFile().getAbsolutePath();
                    } catch (Exception ex) {
                        try {
                            File tmp = File.createTempFile("cjkfont", name.substring(name.lastIndexOf('.')));
                            Files.copy(r.getInputStream(), tmp.toPath(), StandardCopyOption.REPLACE_EXISTING);
                            return tmp.getAbsolutePath();
                        } catch (Exception ignore) {
                            // 继续
                        }
                    }
                }
            } catch (Exception ignore) {
                // 继续尝试下一个
            }
        }
        if (configuredFontPath != null && !configuredFontPath.isBlank() && Files.exists(Paths.get(configuredFontPath))) {
            return configuredFontPath;
        }
        String[] sys = {
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
                "C:/Windows/Fonts/simhei.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/System/Library/Fonts/PingFang.ttc"
        };
        for (String p : sys) {
            if (Files.exists(Paths.get(p))) return p;
        }
        return null;
    }

    private Object coalesce(Object a, Object b) {
        return (a != null && !a.toString().isBlank()) ? a : b;
    }

    private String str(Object o) {
        if (o == null) return "-";
        String s = o.toString().trim();
        return s.isEmpty() ? "-" : s;
    }

    private Color riskColor(String level) {
        if ("critical".equals(level)) return new Color(0xc0, 0x39, 0x2b);
        if ("error".equals(level)) return new Color(0xe6, 0x7e, 0x22);
        if ("warning".equals(level)) return new Color(0xb8, 0x86, 0x0b);
        if ("pending".equals(level)) return new Color(0x7f, 0x8c, 0x8d);
        return Color.BLACK;
    }

    private String riskText(String level) {
        if ("critical".equals(level)) return "严重";
        if ("error".equals(level)) return "错误";
        if ("warning".equals(level)) return "警告";
        if ("pending".equals(level)) return "待核查";
        return str(level);
    }
}

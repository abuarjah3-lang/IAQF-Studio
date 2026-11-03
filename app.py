import json
import os
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd

from iaqf_engine import evaluate_text, DIMENSIONS, INDICATORS

APP_VERSION = "2.6.4"

st.set_page_config(
    page_title="IAQF Studio",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], button, input, textarea, select, label,
[data-testid="stMarkdownContainer"], [data-testid="stMetric"] {
  font-family: 'Cairo', 'Noto Sans Arabic', Tahoma, sans-serif !important;
}
html, body, [data-testid="stAppViewContainer"] {
  font-size: 16px !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stWidgetLabel"] p,
[data-testid="stRadio"] label,
[data-testid="stCaptionContainer"] {
  font-size: 1rem !important;
  line-height: 1.8 !important;
}
.block-container {max-width: 1500px; padding-top: 1.4rem; padding-bottom: 3rem;}
.hero {
  background: linear-gradient(115deg,#082b50 0%,#104b78 58%,#17669b 100%);
  padding: 1.35rem 1.8rem; border-radius: 20px; color: white;
  margin-bottom: 1.35rem; box-shadow: 0 10px 30px rgba(20,55,85,.16);
  border: 1px solid rgba(255,255,255,.10);
}
.hero h1 {color:white; margin:0; font-size:2.35rem; font-weight:800; letter-spacing:.2px;}
.hero p {color:#e5f2fb; margin:.32rem 0 0 0; font-size:1.02rem;}
.hero .en {font-size:.9rem; opacity:.9; letter-spacing:.45px;}
.hero-inner {display:flex; align-items:center; justify-content:flex-end; width:100%;}
.section-kicker {color:#2878B9; font-weight:800; font-size:.92rem; margin-bottom:.2rem;}
.section-title {font-size:1.55rem; font-weight:800; color:#163653; margin:.12rem 0 .65rem;}
.helper {color:#64748b; font-size:1rem; line-height:1.85;}
div[data-testid="stMetric"] {background:#f5f9fc; border:1px solid #dce9f2;
  padding:14px 16px; border-radius:14px;}
div[data-testid="stMetricLabel"] {font-weight:700; font-size:.95rem;}
div.stButton > button[kind="primary"] {background:linear-gradient(100deg,#2878B9,#1c5c8a);
  border:0; border-radius:11px; font-weight:700; min-height:3.1rem; font-size:1rem;}
div.stButton > button {border-radius:11px; min-height:2.9rem; font-size:1rem;}
div[data-testid="stDownloadButton"] button {border-radius:11px; font-weight:700; min-height:3rem; font-size:1rem;}
div[data-testid="stTextArea"] textarea {
  border-radius:13px; border:1px solid #cbd9e5;
  font-family:'Cairo','Noto Sans Arabic',Tahoma,sans-serif !important;
  direction:rtl; text-align:right; line-height:2; font-size:1.08rem !important;
  padding:1rem 1.1rem;
}
div[data-testid="stRadio"] label,
div[data-testid="stCaptionContainer"],
div[data-testid="stTextArea"] label,
div[data-testid="stSelectbox"] label {
  font-family:'Cairo','Noto Sans Arabic',Tahoma,sans-serif !important;
  font-size:1rem !important;
}
div[data-testid="stDataFrame"] {border:1px solid #e1eaf1; border-radius:12px;}
.status-note {background:#f3f8fc; border-right:4px solid #2878B9; padding:12px 15px;
  border-radius:9px; color:#29445b; margin:.6rem 0 1rem;}
.footer {text-align:center; color:#8091a2; font-size:.86rem; padding-top:1.5rem;}
@media (max-width:700px) {
 .hero {padding:1rem;}.hero h1 {font-size:1.7rem;}
 .hero-inner {gap:0;}
 .block-container {padding-left:1rem;padding-right:1rem;}
}
/* Global Arabic RTL: text, labels, controls, cards and feedback */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] .main,
[data-testid="stAppViewContainer"] .block-container,
[data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"],
[data-testid="column"], [data-testid="stMarkdownContainer"],
[data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"],
[data-testid="stAlert"], [data-testid="stExpander"],
[data-testid="stForm"], [data-testid="stMetric"],
[data-testid="stTable"], [data-testid="stDataFrame"] {
  direction:rtl !important;
}
[data-testid="stMarkdownContainer"],
[data-testid="stWidgetLabel"],
[data-testid="stCaptionContainer"],
[data-testid="stAlert"],
[data-testid="stExpander"],
[data-testid="stMetric"],
[data-testid="stTable"] {
  text-align:right !important;
}
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
  direction:rtl !important; text-align:right !important;
  unicode-bidi:plaintext;
}
[data-testid="stRadio"] > div,
[data-testid="stCheckbox"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stWidgetLabel"] {direction:rtl !important;}
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
  flex-direction:row-reverse; justify-content:flex-start;
}
button, [data-testid="stButton"] button,
[data-testid="stDownloadButton"] button {
  direction:rtl; font-family:'Cairo','Noto Sans Arabic',Tahoma,sans-serif !important;
}
.hero-inner {direction:rtl !important; justify-content:flex-end; width:100%;}
.hero-inner > div {direction:rtl !important; text-align:right !important;}
.hero h1, .hero p {text-align:right !important; direction:rtl !important;}
.hero .en, .english, code, pre {
  direction:ltr !important; text-align:left !important; unicode-bidi:plaintext;
}

.nav-brand {direction:rtl;text-align:right;padding:12px 10px 16px;border-bottom:1px solid #dce7f0;margin-bottom:12px;}
.nav-brand-title {font-size:1.2rem;font-weight:800;color:#123d62;}
.nav-brand-subtitle {font-size:.86rem;color:#647b8e;margin-top:3px;}
.nav-rule {height:1px;background:#dce7f0;margin:12px 0 16px;}
.nav-footer {direction:rtl;text-align:center;color:#8293a2;font-size:.78rem;margin-top:20px;padding-top:12px;border-top:1px solid #e4edf3;}
[data-testid="stRadio"] > div {gap:.35rem;}
[data-testid="stRadio"] label {font-size:.96rem !important;line-height:1.65 !important;}
[data-testid="stRadio"] label p {direction:ltr; unicode-bidi:plaintext;}
[data-testid="stTextArea"] textarea {font-size:1.08rem !important;line-height:1.9 !important;}
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="hero">
 <div class="hero-inner">
  <div>
   <h1>IAQF Studio</h1>
   <p>منصة التقييم الذكي لجودة المحتوى العربي</p>
   <p class="en">INTEGRATED ARABIC CONTENT QUALITY FRAMEWORK</p>
  <p class="en">RESEARCH PREVIEW · VERSION {APP_VERSION}</p>
  </div>
 </div>
</div>
""", unsafe_allow_html=True)

# Main workspace on the left; navigation panel on the right.
main_col, nav_col = st.columns([3.25, 1.05], gap="large")

with main_col:
    st.markdown('<div class="section-kicker">WORKSPACE</div><div class="section-title">مساحة التقييم</div>', unsafe_allow_html=True)
    st.markdown('<div class="helper">أدخل النص العربي المراد تقييمه. يتولى النظام تحليل المؤشرات السبعة والعشرين واستخراج الشواهد وتقديم النتائج الأولية.</div>', unsafe_allow_html=True)

    provider = st.radio(
        "مزود الذكاء الاصطناعي",
        options=["Gemini", "Groq"],
        horizontal=True,
        help="اختر المزود الذي سينفذ هذا التقييم. لا ينتقل التطبيق تلقائيًا بين مزودين مختلفين حتى تبقى هوية النموذج موثقة.",
    )

    content = st.text_area(
        "النص المراد تقييمه",
        height=280,
        placeholder="الصق النص العربي المراد تقييمه هنا...",
        help="لا تحتاج إلى إدخال درجات أو شواهد أو بيانات إضافية.",
    )
    st.caption(f"خصوصية الإدخال: يُرسل النص إلى مزود {provider} المختار لإجراء التقييم؛ لا تلصق بيانات شخصية أو سرية.")

    if "evaluation_result" not in st.session_state:
        st.session_state.evaluation_result = None
    if "evaluated_text" not in st.session_state:
        st.session_state.evaluated_text = ""
    if "api_failure_diagnostics" not in st.session_state:
        st.session_state.api_failure_diagnostics = []

    cached_result = st.session_state.evaluation_result
    if cached_result and cached_result.get("version") != APP_VERSION:
        st.session_state.evaluation_result = None
        st.session_state.evaluated_text = ""
        st.session_state.api_failure_diagnostics = []
        st.info("تم تحديث المنصة إلى إصدار جديد؛ أُخفي التقرير السابق لتجنب عرض نتائج بصيغة قديمة. أعد التقييم.")

    run_col, reset_col = st.columns([2, 1])
    with run_col:
        run_eval = st.button("🔍 ابدأ التقييم الشامل", type="primary", use_container_width=True)
    with reset_col:
        reset_eval = st.button("↺ مسح النتائج", use_container_width=True)

    if reset_eval:
        st.session_state.evaluation_result = None
        st.session_state.evaluated_text = ""
        st.session_state.api_failure_diagnostics = []
        st.rerun()

    if run_eval:
        if not content.strip():
            st.warning("يرجى لصق النص أولًا.")
        else:
            st.session_state.evaluation_result = None
            st.session_state.evaluated_text = ""
            st.session_state.api_failure_diagnostics = []
            try:
                with st.spinner("يجري تحليل النص وتقييم مؤشرات IAQF الـ27 ومراجعة جودة الشواهد..."):
                    st.session_state.evaluation_result = evaluate_text(content.strip(), provider=provider)
                    st.session_state.evaluation_result["version"] = APP_VERSION
                    st.session_state.evaluated_text = content.strip()
            except Exception as exc:
                error_text = str(exc)
                st.session_state.api_failure_diagnostics = getattr(exc, "diagnostics", []) or []
                st.error(f"تعذر إكمال التقييم: {error_text}")
                if st.session_state.api_failure_diagnostics:
                    with st.expander(f"تشخيص اتصال {provider} — تفاصيل المحاولات", expanded=True):
                        st.dataframe(
                            pd.DataFrame(st.session_state.api_failure_diagnostics),
                            use_container_width=True,
                            hide_index=True,
                        )
                        st.caption(
                            "يعرض هذا السجل المرحلة والنموذج ورقم المحاولة والنتيجة ورمز HTTP فقط؛ "
                            "ولا يعرض مفتاح API أو النص المرسل إلى مزود الخدمة."
                        )
                if "503" in error_text or "ازدحام" in error_text:
                    st.warning("الخدمة أعادت خطأ 503؛ قد يكون عطلًا مؤقتًا من مزود النموذج. أُعيدت المحاولة تلقائيًا ضمن حدود محددة.")
                elif "429" in error_text:
                    st.warning("يبدو أن الطلب تجاوز حد الاستخدام أو معدل الطلبات. تحقق من حدود الاستخدام لدى مزود النموذج المختار.")
                else:
                    st.info(f"تحقق من إعدادات {provider} في Streamlit Secrets، ومن صلاحية النموذج المحدد.")

    def build_report(result, source_text):
        return {
            "framework": "IAQF",
            "version": result.get("version", APP_VERSION),
            "provider_used": result.get("provider_used", ""),
            "model_used": result.get("model_used", ""),
            "api_diagnostics": result.get("api_diagnostics", []),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_text": source_text,
            "overall_score": result.get("overall_score"),
            "overall_note": result.get("overall_note", ""),
            "dimensions": result.get("dimensions", {}),
            "coverage": result.get("coverage", {}),
            "indicators": result.get("indicators", {}),
            "strengths": result.get("strengths", []),
            "issues": result.get("issues", []),
            "recommendations": result.get("recommendations", []),
            "limitations": result.get("limitations", []),
            "evidence_repair_attempted": result.get("evidence_repair_attempted", []),
            "evidence_repair": result.get("evidence_repair", {}),
            "evidence_audit": result.get("evidence_audit", {}),
            "score_calibration": result.get("score_calibration", {}),
            "evidence_validation_note": result.get("evidence_validation_note", ""),
            "external_verification_performed": result.get("external_verification_performed", False),
            "verification_scope": result.get("verification_scope", ""),
        }

    def set_rtl(paragraph):
        paragraph.alignment = 2
        p_pr = paragraph._p.get_or_add_pPr()
        bidi = p_pr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}bidi")
        if bidi is None:
            from docx.oxml import OxmlElement
            bidi = OxmlElement("w:bidi")
            p_pr.append(bidi)

    def set_cell_rtl(cell):
        from docx.oxml import OxmlElement
        tc_pr = cell._tc.get_or_add_tcPr()
        bidi = OxmlElement("w:bidi")
        tc_pr.append(bidi)
        for paragraph in cell.paragraphs:
            set_rtl(paragraph)

    def shade_cell(cell, fill):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), fill)
        cell._tc.get_or_add_tcPr().append(shd)

    def build_word_report(report):
        from docx import Document
        from docx.shared import Cm, Pt, RGBColor
        from docx.enum.section import WD_ORIENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

        doc = Document()
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = section.page_height, section.page_width
        section.left_margin = Cm(1.35)
        section.right_margin = Cm(1.35)
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)

        styles = doc.styles
        styles["Normal"].font.name = "Arial"
        styles["Normal"].font.size = Pt(9)
        styles["Title"].font.name = "Arial"
        styles["Title"].font.size = Pt(23)
        styles["Title"].font.bold = True
        styles["Title"].font.color.rgb = RGBColor(25, 75, 112)

        if os.path.exists("iaqf_logo.png"):
            logo_p = doc.add_paragraph()
            logo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            logo_p.add_run().add_picture("iaqf_logo.png", width=Cm(2.1))

        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title.add_run("IAQF Studio")
        title_run.bold = True
        title_run.font.size = Pt(23)
        title_run.font.color.rgb = RGBColor(40, 120, 185)
        set_rtl(title)

        subtitle = doc.add_paragraph("التقرير النهائي لتقييم جودة المحتوى العربي")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.runs[0].bold = True
        subtitle.runs[0].font.size = Pt(15)
        set_rtl(subtitle)

        p = doc.add_paragraph(f"إصدار المنصة: {report.get('version')}    |    تاريخ إنشاء التقرير: {report.get('generated_at')}")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_rtl(p)

        doc.add_heading("الملخص التنفيذي", level=1)
        overall = report.get("overall_score")
        p = doc.add_paragraph()
        p.add_run("النتيجة الإجمالية: ").bold = True
        p.add_run(f"{overall} / 5" if isinstance(overall, (int, float)) else "غير متاحة")
        p.add_run("    |    ")
        coverage = report.get("coverage", {})
        p.add_run(f"المؤشرات القابلة للتقييم: {coverage.get('assessable', 0)} / 27")
        p.add_run(f"    |    مؤشرات NA: {coverage.get('not_applicable', 0)}")
        p.add_run(f"    |    درجات أولية غير معايرة: {coverage.get('uncalibrated', 0)}")
        p.add_run(f"    |    مؤشرات لم يكتمل تقييمها: {coverage.get('incomplete', 0)}")
        set_rtl(p)
        if report.get("overall_note"):
            p = doc.add_paragraph(report["overall_note"])
            set_rtl(p)

        doc.add_heading("نتائج الأبعاد الأربعة", level=1)
        dims = doc.add_table(rows=1, cols=3)
        dims.alignment = WD_TABLE_ALIGNMENT.CENTER
        dims.style = "Light Shading Accent 1"
        for cell, text in zip(dims.rows[0].cells, ["البعد", "النتيجة من 5", "التغطية"]):
            cell.text = text
            shade_cell(cell, "DCEEFF")
            set_cell_rtl(cell)
        for key, label in DIMENSIONS.items():
            d = report.get("dimensions", {}).get(key, {})
            cells = dims.add_row().cells
            cells[0].text = label
            cells[1].text = str(d.get("score") if d.get("score") is not None else "غير متاح")
            cells[2].text = str(d.get("coverage", "—"))
            for cell in cells:
                set_cell_rtl(cell)

        doc.add_heading("تفصيل المؤشرات السبعة والعشرين", level=1)
        table = doc.add_table(rows=1, cols=7)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"
        headers = ["الرمز", "المؤشر", "الدرجة الأصلية", "الدرجة المعايرة", "الشاهد النصي", "التبرير", "حكم جودة الدليل"]
        for cell, text in zip(table.rows[0].cells, headers):
            cell.text = text
            shade_cell(cell, "DCEEFF")
            set_cell_rtl(cell)
        for code, meta in INDICATORS.items():
            item = report.get("indicators", {}).get(code, {})
            calibrated = item.get("calibrated_score")
            if calibrated is None and item.get("original_score") is not None:
                calibrated = "لم تُعتمد (التدقيق غير مكتمل)"
            elif calibrated is None:
                calibrated = "NA"
            cells = table.add_row().cells
            values = [
                code, meta["name"],
                str(item.get("original_score") if item.get("original_score") is not None else "NA"),
                str(calibrated),
                str(item.get("evidence", "—")),
                str(item.get("rationale", "—")),
                str(item.get("evidence_quality_verdict", "—")),
            ]
            for cell, value in zip(cells, values):
                cell.text = value
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                set_cell_rtl(cell)

        doc.add_heading("تفاصيل تدقيق الأدلة لكل مؤشر", level=1)
        audit_table = doc.add_table(rows=1, cols=6)
        audit_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        audit_table.style = "Table Grid"
        audit_headers = ["الرمز", "الثقة", "سبب NA", "صلة وكفاية الشاهد", "اتساق الدرجة", "سبب المعايرة وملاحظة التحقق"]
        for cell, text in zip(audit_table.rows[0].cells, audit_headers):
            cell.text = text
            shade_cell(cell, "E8F2F8")
            set_cell_rtl(cell)
        for code, meta in INDICATORS.items():
            item = report.get("indicators", {}).get(code, {})
            relevance = str(item.get("evidence_relevance", "—"))
            sufficiency = str(item.get("evidence_sufficiency", "—"))
            reason = str(item.get("calibration_reason", "—"))
            verification = str(item.get("verification_note", "لم يُجرَ تحقق خارجي مستقل."))
            values = [
                code,
                str(item.get("confidence", "—")),
                str(item.get("na_reason") or "—"),
                "الصلة: " + relevance + "\nالكفاية: " + sufficiency,
                str(item.get("score_consistency", "—")),
                "المعايرة: " + reason + "\nالتحقق: " + verification,
            ]
            cells = audit_table.add_row().cells
            for cell, value in zip(cells, values):
                cell.text = value
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                set_cell_rtl(cell)

        doc.add_heading("مراجعة المعايرة وجودة الأدلة", level=1)
        audit = report.get("evidence_audit", {})
        calibration = report.get("score_calibration", {})
        for line in [
            f"حالة مراجعة الأدلة: {audit.get('status', 'غير محددة')}",
            f"حالة المعايرة: {calibration.get('status', 'غير محددة')}",
            f"المؤشرات التي تمت معايرتها: {calibration.get('audited', 0)}",
            f"المؤشرات التي خُفّضت درجاتها: {calibration.get('reduced', 0)}",
            f"المؤشرات التي حُوّلت إلى NA: {calibration.get('converted_to_NA', 0)}",
            "التحقق الخارجي المستقل: لم يُجرَ",
        ]:
            p = doc.add_paragraph(line)
            set_rtl(p)
        if report.get("evidence_validation_note"):
            p = doc.add_paragraph(report["evidence_validation_note"])
            set_rtl(p)

        for heading, key in [
            ("نقاط القوة", "strengths"),
            ("المشكلات والمخاطر", "issues"),
            ("التوصيات", "recommendations"),
            ("ملاحظات وحدود التقييم", "limitations"),
        ]:
            doc.add_heading(heading, level=1)
            values = report.get(key, []) or ["لا توجد ملاحظات مسجلة."]
            for value in values:
                p = doc.add_paragraph(str(value), style="List Bullet")
                set_rtl(p)

        doc.add_heading("النص محل التقييم", level=1)
        source = report.get("source_text", "")
        p = doc.add_paragraph(source if source else "لم يُرفق النص الأصلي.")
        set_rtl(p)

        note = doc.add_paragraph(
            "تنبيه منهجي: هذا تقرير تقييم آلي استرشادي. مراجعة الشواهد ومعايرة الدرجات آليتان وليستا تحكيمًا بشريًا مستقلًا، "
            "ولا يتضمن هذا الإصدار تحققًا خارجيًا من الوقائع أو المراجع أو الأصالة. ينبغي مراجعة النتائج بشريًا قبل اعتمادها."
        )
        set_rtl(note)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    result = st.session_state.evaluation_result

    if result:
        report = build_report(result, st.session_state.evaluated_text)
        st.divider()
        st.markdown('<div class="section-kicker">RESULTS</div><div class="section-title">تقرير التقييم</div>', unsafe_allow_html=True)
        st.caption(
            f"إصدار المحرك: {result.get('version', 'غير محدد')} | إصدار الواجهة: {APP_VERSION} "
            f"| المزود: {result.get('provider_used', 'غير محدد')} | النموذج: {result.get('model_used', 'غير محدد')}"
        )
        api_diagnostics = result.get("api_diagnostics", [])
        if api_diagnostics:
            with st.expander(f"تفاصيل اتصال {result.get('provider_used', 'المزود')} ومحاولات الاستعادة"):
                st.dataframe(pd.DataFrame(api_diagnostics), use_container_width=True, hide_index=True)
                st.caption("السجل يوضح المرحلة والنموذج وعدد المحاولات وحالة كل طلب، دون عرض مفتاح API أو النص المرسل.")
        st.info("النتائج آلية استرشادية؛ ينبغي مراجعتها بشريًا قبل استخدامها في قرارات بحثية أو نشرية.")
        st.warning("حدود التحقق: مراجعة صلة الأدلة وكفايتها واتساقها آلية وليست مراجعة بشرية مستقلة؛ ولا يجري التطبيق تحققًا خارجيًا من المراجع أو الوقائع أو الأصالة أو بيانات سياق الإنتاج.")
        st.caption("تمييز منهجي: المؤشر NA يختلف عن الدرجة الأولية غير المعايرة؛ تعذّر التدقيق لا يُعد مخالفة ولا يُحتسب ضمن مؤشرات NA.")

        overall = result.get("overall_score")
        coverage = result.get("coverage", {})
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("النتيجة الإجمالية", f"{overall:.2f} / 5" if isinstance(overall, (int, float)) else "غير متاحة")
        m2.metric("المؤشرات القابلة للتقييم", f'{coverage.get("assessable", 0)} / 27')
        m3.metric("المؤشرات NA", str(coverage.get("not_applicable", 0)))
        m4.metric("درجات أولية غير معايرة", str(coverage.get("uncalibrated", 0)))
        m5.metric("تقييم أولي غير مكتمل", str(coverage.get("incomplete", 0)))
        if not isinstance(overall, (int, float)):
            st.warning(result.get("overall_note", "لم تُحسب نتيجة إجمالية؛ راجع تغطية الأبعاد الأربعة."))

        st.subheader("نتائج الأبعاد الأربعة")
        dim_cols = st.columns(4)
        for col, (key, label) in zip(dim_cols, DIMENSIONS.items()):
            dim = result.get("dimensions", {}).get(key, {})
            score = dim.get("score")
            col.metric(label, f"{score:.2f} / 5" if isinstance(score, (int, float)) else "غير متاح")
            col.caption(f"التغطية المعايرة: {dim.get('coverage', '—')}")
            if dim.get("uncalibrated", 0):
                col.caption(f"درجات أولية غير معايرة: {dim.get('uncalibrated')}")
            if dim.get("incomplete", 0):
                col.caption(f"تقييم أولي غير مكتمل: {dim.get('incomplete')}")

        st.subheader("تفصيل المؤشرات الـ27")
        rows = []
        for key, meta in INDICATORS.items():
            item = result.get("indicators", {}).get(key, {})
            rows.append({
                "الرمز": key,
                "المؤشر": meta["name"],
                "الدرجة الأصلية": item.get("original_score", item.get("score", "NA")),
                "الدرجة المعايرة": item.get("calibrated_score") if item.get("calibrated_score") is not None else ("لم تتم المعايرة" if item.get("original_score") is not None else "NA"),
                "حالة التعديل": item.get("result_status", "غير محددة"),
                "سبب المعايرة": item.get("calibration_reason", "—"),
                "الشاهد من النص": item.get("evidence", ""),
                "التبرير": item.get("rationale", ""),
                "الثقة": item.get("confidence", "—"),
                "سبب NA": item.get("na_reason") or "—",
                "مطابقة الشاهد": item.get("evidence_status", "—"),
                "أساس الحكم": item.get("evidence_basis", "—"),
                "التحقق الخارجي": "لم يُجرَ",
                "صلة الشاهد": item.get("evidence_relevance", "—"),
                "كفاية الشاهد": item.get("evidence_sufficiency", "—"),
                "اتساق الدرجة": item.get("score_consistency", "—"),
                "حكم جودة الدليل": item.get("evidence_quality_verdict", "—"),
                "ملاحظة التحقق": item.get("verification_note", "—"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        repair = result.get("evidence_repair", {})
        if repair.get("attempted"):
            st.info("محاولات إصلاح الشواهد: " + ", ".join(repair.get("attempted", [])))
            st.caption("نجح الإصلاح: " + (", ".join(repair.get("succeeded", [])) or "لا يوجد")
                       + " | لم ينجح: " + (", ".join(repair.get("failed", [])) or "لا يوجد"))
        audit_meta = result.get("evidence_audit", {})
        calibration_meta = result.get("score_calibration", {})
        if audit_meta:
            st.caption("حالة مراجعة جودة الأدلة: " + audit_meta.get("status", "غير محددة"))
            retry_items = audit_meta.get("retry_attempts", [])
            if retry_items:
                recovered = audit_meta.get("retry_recovered", [])
                unresolved = audit_meta.get("und_audited", [])
                st.caption(
                    "إعادة تدقيق المؤشرات الناقصة مرة واحدة: "
                    + str(audit_meta.get("retry_count", len(retry_items)))
                    + " | استُعيد حكمها: " + (", ".join(recovered) or "لا يوجد")
                    + " | بقي دون تدقيق: " + (", ".join(unresolved) or "لا يوجد")
                )
        calibration_status = calibration_meta.get("status", "لم تُسجّل حالة المعايرة")
        if calibration_status == "اكتملت المعايرة":
            st.success("حالة المعايرة: اكتملت المراجعة الآلية الثانية للمؤشرات التي أمكن تدقيقها.")
        else:
            st.error("حالة المعايرة: لم تكتمل. الدرجات الأصلية ظاهرة للشفافية، لكنها ليست درجات معايرة ولا ينبغي اعتمادها بوصفها كذلك.")
            if audit_meta.get("error"):
                st.caption("تفاصيل تعذّر التدقيق: " + str(audit_meta.get("error"))[:300])
        st.caption(
            "ملخص المعايرة — خُفّضت: " + str(calibration_meta.get("reduced", 0))
            + " | حُوّلت إلى NA: " + str(calibration_meta.get("converted_to_NA", 0))
        )
        if result.get("evidence_validation_note"):
            st.caption(result["evidence_validation_note"])

        for heading, key in [
            ("نقاط القوة", "strengths"),
            ("المشكلات والمخاطر", "issues"),
            ("التوصيات", "recommendations"),
            ("ملاحظات وحدود التقييم", "limitations"),
        ]:
            with st.expander(heading, expanded=(heading == "نقاط القوة")):
                values = result.get(key, []) or ["لا توجد ملاحظات مسجلة."]
                for value in values:
                    st.write(f"• {value}")

        st.subheader("تنزيل التقرير النهائي")
        st.caption("يتضمن التقرير الملخص التنفيذي، نتائج الأبعاد، المؤشرات الـ27، الشواهد، التبريرات، المعايرة، والتوصيات.")
        json_data = json.dumps(report, ensure_ascii=False, indent=2)
        try:
            word_data = build_word_report(report)
            word_error = None
        except Exception as exc:
            word_data = None
            word_error = str(exc)

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "⬇️ تنزيل التقرير بصيغة Word",
                data=word_data if word_data else b"",
                file_name="IAQF_Final_Evaluation_Report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                disabled=word_data is None,
            )
        with dl2:
            st.download_button(
                "⬇️ تنزيل التقرير بصيغة JSON",
                data=json_data,
                file_name="IAQF_Final_Evaluation_Report.json",
                mime="application/json",
                use_container_width=True,
            )
        if word_error:
            st.error(f"تعذر تجهيز ملف Word: {word_error}. تحقق من تثبيت python-docx.")
        else:
            st.caption("تم تجهيز ملف Word من بيانات التقييم الحالية. راجع النتائج والشواهد قبل اعتماد التقرير.")

    with st.expander("عن المنصة وحدود التقييم"):
        st.write(
            "IAQF Studio أداة بحثية تجريبية لتحليل جودة المحتوى العربي وفق أربعة أبعاد و27 مؤشرًا. "
            "تعرض المنصة الشواهد والدرجات الأولية والمعايرة الآلية، لكنها لا تستبدل التحكيم البشري "
            "ولا تجري تحققًا خارجيًا من المراجع أو الوقائع أو الأصالة."
        )
        st.write("إصدار الواجهة: " + APP_VERSION)

    st.markdown('<div class="footer">IAQF Studio · Integrated Arabic Content Quality Framework · نسخة تجريبية بحثية</div>', unsafe_allow_html=True)


with nav_col:
    st.markdown("""
    <div class="nav-brand" dir="rtl">
      <div class="nav-brand-title">IAQF Studio</div>
      <div class="nav-brand-subtitle">دليل المنصة البحثية</div>
    </div>
    """, unsafe_allow_html=True)

    nav_section = st.radio(
        "القائمة الرئيسية",
        [
            "نبذة عن المنصة",
            "أبعاد التقييم",
            "منهجية التقييم",
            "دليل الاستخدام",
            "الخصوصية والحدود",
            "معلومات الإصدار",
        ],
        label_visibility="collapsed",
        key="guide_navigation",
    )

    st.markdown('<div class="nav-rule"></div>', unsafe_allow_html=True)

    if nav_section == "نبذة عن المنصة":
        st.markdown("""
        ### نبذة عن IAQF
        منصة بحثية تجريبية لتحليل جودة المحتوى العربي بمساعدة الذكاء الاصطناعي، وفق إطار يضم أربعة أبعاد و27 مؤشرًا.

        تقدم قراءة منظمة مدعومة بالشواهد والتبريرات والتوصيات لمساندة المراجعة البشرية.
        """)
    elif nav_section == "أبعاد التقييم":
        st.markdown("""
        ### أبعاد التقييم الأربعة
        **L — الجودة اللغوية**  
        سلامة اللغة ووضوحها واتساقها.

        **E — الجودة المعرفية**  
        جودة المحتوى المعرفي واتساقه ومدى دعم أحكامه بالشواهد المتاحة.

        **C — الجودة الثقافية**  
        مراعاة السياق الثقافي والتمثيل والحساسية الثقافية.

        **H — الجودة الأخلاقية**  
        المسؤولية والإنصاف والخصوصية والشفافية واحترام الحقوق.

        **المجموع: 27 مؤشرًا.**
        """)
    elif nav_section == "منهجية التقييم":
        st.markdown("""
        ### منهجية التقييم
        - مقياس تقدير من **1 إلى 5**.
        - إسناد الأحكام إلى شواهد وتبريرات.
        - مراجعة آلية لجودة الأدلة واتساق الدرجات.
        - استخدام **NA** عند عدم الانطباق أو تعذر الحكم.
        - الدرجة الأولية غير المعايرة ليست درجة نهائية.

        المراجعة والمعايرة آليتان وليستا تحكيمًا بشريًا مستقلًا.
        """)
    elif nav_section == "دليل الاستخدام":
        st.markdown("""
        ### دليل الاستخدام
        1. اختر مزود الذكاء الاصطناعي.
        2. الصق النص المراد تقييمه.
        3. اضغط **ابدأ التقييم الشامل**.
        4. راجع النتائج والأبعاد والمؤشرات والشواهد.
        5. نزّل التقرير بصيغة Word أو JSON.

        استخدم نصًا تملك حق مشاركته وخاليًا من البيانات الشخصية أو السرية.
        """)
    elif nav_section == "الخصوصية والحدود":
        st.markdown("""
        ### الخصوصية وحدود التقييم
        - يُرسل النص إلى مزود الذكاء الاصطناعي المختار لتنفيذ التقييم.
        - لا تُدخل بيانات شخصية أو سرية.
        - لا ينفذ التطبيق تحققًا خارجيًا مستقلًا من الوقائع أو المراجع أو الأصالة.
        - النتائج استرشادية وتحتاج إلى مراجعة بشرية.

        **الحالة العلمية:** نموذج بحثي تجريبي، وليس أداة مقننة.
        """)
    else:
        st.markdown(f"""
        ### معلومات الإصدار
        **اسم المنصة:** IAQF Studio  
        **الإصدار:** {APP_VERSION}  
        **الإطار:** Integrated Arabic Content Quality Framework  
        **النطاق:** 4 أبعاد · 27 مؤشرًا  
        **الحالة:** Research Preview
        """)

    st.markdown('<div class="nav-footer">IAQF Studio · Research Preview</div>', unsafe_allow_html=True)

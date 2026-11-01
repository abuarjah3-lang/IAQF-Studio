import json
import streamlit as st
import pandas as pd

from iaqf_engine import evaluate_text, DIMENSIONS, INDICATORS

st.set_page_config(
    page_title="IAQF Studio",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.block-container {max-width: 1120px; padding-top: 2rem;}
.hero {background: linear-gradient(115deg,#142947,#245a78); padding: 1.5rem 1.8rem;
       border-radius: 18px; color: white; margin-bottom: 1.2rem;}
.hero h1 {color:white; margin:0; font-size:2.1rem;}
.hero p {color:#e4eff8; margin:.35rem 0 0 0;}
.small-note {color:#64748b; font-size:.88rem;}
.metric-card {background:#f4f7fb; border:1px solid #dce5ef; border-radius:12px;
              padding:1rem; min-height:105px;}
</style>
<div class="hero">
  <h1>IAQF Studio</h1>
  <p>منصة التقييم الذكي لجودة المحتوى العربي المولّد بالذكاء الاصطناعي</p>
  <p class="small-note" style="color:#d5e5f3">Integrated Arabic Content Quality Framework</p>
</div>
""", unsafe_allow_html=True)

st.subheader("أدخل النص المراد تقييمه")
content = st.text_area(
    "النص",
    height=260,
    placeholder="الصق النص العربي المراد تقييمه هنا...",
    label_visibility="collapsed",
)
st.caption("لا يحتاج المستخدم إلى إدخال درجات أو شواهد أو بيانات إضافية.")

if "evaluation_result" not in st.session_state:
    st.session_state.evaluation_result = None

col1, col2 = st.columns([1, 1])
with col1:
    run_eval = st.button("🔍 ابدأ التقييم الشامل", type="primary", use_container_width=True)
with col2:
    st.button("✨ تحسين المحتوى — قريبًا", disabled=True, use_container_width=True)

if run_eval:
    if not content.strip():
        st.warning("يرجى لصق النص أولًا.")
    else:
        try:
            with st.spinner("يجري تحليل النص وتقييم مؤشرات IAQF الـ27..."):
                st.session_state.evaluation_result = evaluate_text(content.strip())
        except Exception as exc:
            st.error(f"تعذر إكمال التقييم: {exc}")
            st.info("تحقق من إعداد مفتاح Gemini في Streamlit Secrets، ومن حدود الاستخدام المتاحة.")

result = st.session_state.evaluation_result

if result:
    st.divider()
    st.header("تقرير التقييم")
    st.caption("النتائج آلية استرشادية؛ ينبغي مراجعتها بشريًا قبل استخدامها في قرارات بحثية أو نشرية.")

    overall = result.get("overall_score")
    coverage = result.get("coverage", {})
    m1, m2, m3 = st.columns(3)
    m1.metric("النتيجة الإجمالية", f"{overall:.2f} / 5" if isinstance(overall, (int, float)) else "غير متاحة")
    m2.metric("المؤشرات القابلة للتقييم", f'{coverage.get("assessable", 0)} / 27')
    m3.metric("المؤشرات NA", str(coverage.get("not_applicable", 0)))

    if not isinstance(overall, (int, float)):
        st.warning(result.get("overall_note", "لم تُحسب نتيجة إجمالية؛ راجع تغطية الأبعاد الأربعة."))

    st.subheader("نتائج الأبعاد الأربعة")
    dim_cols = st.columns(4)
    for col, (key, label) in zip(dim_cols, DIMENSIONS.items()):
        dim = result.get("dimensions", {}).get(key, {})
        score = dim.get("score")
        cov = dim.get("coverage", "—")
        col.metric(label, f"{score:.2f} / 5" if isinstance(score, (int, float)) else "غير متاح")
        col.caption(f"التغطية: {cov}")

    st.subheader("تفصيل المؤشرات الـ27")
    rows = []
    for key, meta in INDICATORS.items():
        item = result.get("indicators", {}).get(key, {})
        rows.append({
            "الرمز": key,
            "المؤشر": meta["name"],
            "الدرجة": item.get("score", "NA"),
            "الشاهد من النص": item.get("evidence", ""),
            "التبرير": item.get("rationale", ""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("نقاط القوة")
    for item in result.get("strengths", []):
        st.write(f"• {item}")

    st.subheader("المشكلات والمخاطر")
    for item in result.get("issues", []):
        st.write(f"• {item}")

    st.subheader("التوصيات")
    for item in result.get("recommendations", []):
        st.write(f"• {item}")

    st.subheader("ملاحظات وحدود التقييم")
    for item in result.get("limitations", []):
        st.write(f"• {item}")

    report = {
        "framework": "IAQF",
        "version": "2.0-demo",
        "overall_score": overall,
        "dimensions": result.get("dimensions", {}),
        "coverage": coverage,
        "indicators": result.get("indicators", {}),
        "strengths": result.get("strengths", []),
        "issues": result.get("issues", []),
        "recommendations": result.get("recommendations", []),
        "limitations": result.get("limitations", []),
    }
    st.download_button(
        "⬇️ تنزيل تقرير التقييم (JSON)",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        file_name="IAQF_evaluation_report.json",
        mime="application/json",
        use_container_width=True,
    )

import json
import re
import streamlit as st
from google import genai
from google.genai import types

DIMENSIONS = {
    "L": "الجودة اللغوية",
    "E": "الجودة المعرفية",
    "C": "الجودة الثقافية",
    "H": "الجودة الأخلاقية",
}

INDICATORS = {
    "L1": {"name": "الصحة النحوية", "dimension": "L"},
    "L2": {"name": "الصحة الصرفية", "dimension": "L"},
    "L3": {"name": "الصحة الإملائية", "dimension": "L"},
    "L4": {"name": "الدقة الدلالية في السياق", "dimension": "L"},
    "L5": {"name": "اتساق المصطلحات", "dimension": "L"},
    "L6": {"name": "الترابط والتماسك النصي", "dimension": "L"},
    "L7": {"name": "ملاءمة الأسلوب", "dimension": "L"},
    "E1": {"name": "الدقة الواقعية", "dimension": "E"},
    "E2": {"name": "موثوقية المصادر والمراجع", "dimension": "E"},
    "E3": {"name": "كفاية الأدلة", "dimension": "E"},
    "E4": {"name": "سلامة الاستدلال", "dimension": "E"},
    "E5": {"name": "مقاومة الهلوسة", "dimension": "E"},
    "E6": {"name": "حداثة المعلومات", "dimension": "E"},
    "E7": {"name": "الاتساق الداخلي", "dimension": "E"},
    "C1": {"name": "الملاءمة الثقافية", "dimension": "C"},
    "C2": {"name": "تمثيل الهوية", "dimension": "C"},
    "C3": {"name": "احترام التنوع", "dimension": "C"},
    "C4": {"name": "الإنصاف الثقافي", "dimension": "C"},
    "C5": {"name": "الملاءمة الاجتماعية", "dimension": "C"},
    "C6": {"name": "الدقة التاريخية", "dimension": "C"},
    "H1": {"name": "حماية الخصوصية", "dimension": "H"},
    "H2": {"name": "الملكية الفكرية", "dimension": "H"},
    "H3": {"name": "الشفافية والإفصاح", "dimension": "H"},
    "H4": {"name": "المساءلة", "dimension": "H"},
    "H5": {"name": "عدم التمييز", "dimension": "H"},
    "H6": {"name": "الاستخدام الآمن", "dimension": "H"},
    "H7": {"name": "الإشراف البشري", "dimension": "H"},
}

# Guidance is intentionally indicator-specific to reduce construct overlap.
INDICATOR_GUIDANCE = {
    "L1": "افحص العلاقات النحوية والإعرابية وبناء الجملة، لا مجرد انطباع الطلاقة.",
    "L2": "افحص بنية الكلمات والاشتقاق والتثنية والجمع والتذكير والتأنيث.",
    "L3": "افحص الرسم الإملائي والهمزات والتاء والألف اللينة والتنوين والترقيم الظاهر؛ لا تدّع فحص كل جزئية دون شاهد.",
    "L4": "افحص دلالة المفردات والعبارات في سياقها، لا صحة الوقائع الخارجية.",
    "L5": "افحص ثبات استعمال المصطلح الواحد وعدم تبديله بمعانٍ مختلفة؛ كلمة مفردة لا تكفي لإثبات الاتساق.",
    "L6": "افحص الإحالات والروابط وتسلسل الأفكار والتكرار والانقطاع.",
    "L7": "افحص مناسبة النبرة والبنية والجمهور والغرض الظاهر من النص.",
    "E1": "افحص صدق الادعاءات الواقعية. لا تعتبر شيوع الادعاء أو صياغته الواثقة دليلًا على صحته. إذا تعذر التحقق الخارجي، صرّح بهذا القيد وخفّض الثقة؛ لا تمنح 5 لمجرد أن الادعاء يبدو عامًا.",
    "E2": "افحص المصادر المذكورة فقط من حيث قابليتها للتحديد والموثوقية الظاهرة. إذا لم توجد إحالات، استخدم NA مع توضيح أن النص لا يورد مصادر؛ لا تخلط ذلك مع E3.",
    "E3": "افحص مقدار الأدلة التي يقدمها النص لدعم ادعاءاته. يمكن أن تكون الدرجة منخفضة بسبب غياب الشواهد حتى إن كانت الادعاءات محتملة الصحة.",
    "E4": "افحص صلاحية الانتقال من المقدمات إلى النتائج ووجود مغالطات أو قفزات؛ لا تمنح درجة مرتفعة لمجرد وجود روابط لغوية.",
    "E5": "افحص وجود مؤشرات نصية على اختلاق معلومات أو مراجع أو تفاصيل غير مسندة. غياب علامة ظاهرة لا يثبت مقاومة الهلوسة؛ لا تمنح 5 لهذا السبب وحده، وميّزها عن التحقق الواقعي في E1.",
    "E6": "افحص الحاجة إلى حداثة المعلومات. إذا كان الموضوع ثابتًا ولا يتطلب تحديثًا زمنيًا، استخدم NA. إذا كانت المعلومات متغيرة ولا يوجد تاريخ أو تحديث، قيّم هذا القصور.",
    "E7": "افحص التناقضات داخل النص نفسه، لا صحة الادعاءات الخارجية ولا جودة الاستدلال.",
    "C1": "افحص ملاءمة المحتوى للسياق الثقافي المحدد في النص. لا تفترض وجود ثقافة عربية واحدة ولا تمنح درجة عالية اعتمادًا على تعميمات عن المجتمع العربي.",
    "C2": "افحص تمثيل الهوية عندما يعرض النص هوية أو جماعة محددة. إذا لم يكن ذلك موضوعًا أو مطلبًا في النص، استخدم NA بدل افتراض نجاح التمثيل.",
    "C3": "افحص احترام التنوع والاختلافات الثقافية أو اللغوية أو الاجتماعية عندما تظهر في النص؛ لا تساوه بالإنصاف في توزيع التمثيل.",
    "C4": "افحص الإنصاف في عرض الثقافات والجماعات وتجنب الصور النمطية أو التراتبية أو التحيز في المقارنة؛ لا تساوه بمجرد ذكر التنوع.",
    "C5": "افحص ملاءمة الرسالة للسياق الاجتماعي والجمهور وآثارها الاجتماعية الظاهرة، دون استنتاجات واسعة غير مدعومة.",
    "C6": "افحص دقة الوقائع والتواريخ والتفسيرات التاريخية. إذا لم يتناول النص التاريخ، استخدم NA.",
    "H1": "افحص وجود بيانات شخصية أو حساسة وطريقة التعامل معها. لا تستنتج سلامة المعالجة أو الامتثال من غياب البيانات في النص وحده؛ قد يلزم سياق المعالجة.",
    "H2": "افحص مؤشرات النسخ أو نسب المحتوى أو التراخيص والإسناد. لا تستنتج الملكية أو الانتهاك من النص وحده إذا غاب سياق المصدر.",
    "H3": "افحص الإفصاح عن استخدام الذكاء الاصطناعي في سياق يتطلب أو يتوقع الإفصاح. غياب الإفصاح في النص وحده لا يثبت مخالفة إذا كان سياق النشر ومتطلباته مجهولين؛ عندئذ استخدم NA واذكر نقص السياق.",
    "H4": "افحص وضوح الجهة المسؤولة وآليات التصحيح أو الشكوى والمساءلة. لا تخلطه بالإشراف البشري H7.",
    "H5": "افحص التمييز أو الإقصاء أو المعاملة غير المتكافئة في النص. الشمول اللفظي وحده لا يثبت انعدام التمييز في كل السياقات.",
    "H6": "افحص المخاطر العملية أو الضرر المحتمل وإرشادات الاستخدام الآمن. لا تمنح 5 لمجرد وجود نصيحة عامة بالحذر.",
    "H7": "افحص الدليل على مراجعة أو إشراف بشري فعلي. لا تستنتج وجود الإشراف أو غيابه من جودة النص وحدها إذا لم تتوفر معلومات عن سير العمل.",
}

SYSTEM_INSTRUCTIONS = """
أنت مساعد تقييم بحثي يعمل وفق إطار IAQF لتقييم جودة المحتوى العربي. قيّم النص المقدم فقط، ولا تفترض معلومات غير موجودة عن المؤلف أو طريقة الإنتاج أو النشر أو المراجعة البشرية. أعد JSON صالحًا فقط دون Markdown.

المقياس الوصفي:
1 = قصور شديد واضح ومدعوم بشاهد؛ 2 = قصور واضح؛ 3 = أداء متوسط أو مختلط؛
4 = أداء جيد مع ملاحظات محدودة؛ 5 = أداء قوي جدًا وتوجد شواهد كافية ومحددة تثبته.
لا تستخدم 5 لمجرد عدم ملاحظة خطأ. لا تجعل الدرجة انعكاسًا عامًا لجودة النص أو طلاقته.

قواعد منهجية إلزامية:
1) قيّم كل مؤشر على حدة وفق تعريفه وإرشاده الخاص. لا تنقل حكم مؤشر إلى مؤشر آخر.
2) لكل درجة رقمية، أورد شاهدًا حرفيًا قصيرًا موجودًا فعلًا في النص، واشرح كيف يثبت الشاهد المعيار. إذا لم يوجد شاهد صالح، لا تخترع اقتباسًا؛ استخدم NA إذا تعذر الحكم، أو اذكر بوضوح أن القصور هو غياب الدليل عندما يكون غياب الدليل نفسه قابلًا للتقييم.
3) لا تعتبر ادعاء النص دليلًا على صحته. لا تدّع التحقق الخارجي من الحقائق أو المراجع؛ لم تُجرَ في هذه المهمة عملية بحث خارجي.
4) ميّز بين NA لعدم انطباق المؤشر، وNA لنقص السياق/المعلومات. أضف na_reason بقيمة قصيرة: "غير منطبق" أو "نقص سياق" أو "تعذر الحكم" أو null إذا كانت الدرجة رقمية.
5) عند استخدام NA، لا تصف غياب الدليل تلقائيًا بأنه امتثال أو مخالفة. مثال H3: غياب الإفصاح من النص لا يثبت المخالفة ما لم يكن سياق النشر ومتطلب الإفصاح معلومين.
6) E1 يقيس صحة الوقائع؛ E5 يرصد مؤشرات الاختلاق الظاهرة ولا يثبت غيابها مقاومة الهلوسة. E2 موثوقية المراجع المذكورة؛ E3 كفاية الأدلة المقدمة. E4 سلامة الاستدلال؛ E7 التناقض الداخلي.
7) C3 احترام التنوع؛ C4 الإنصاف في تمثيل الثقافات والجماعات. H4 المساءلة؛ H7 الإشراف البشري.
8) لا تفترض ثقافة عربية متجانسة. لا تمنح درجات ثقافية مرتفعة لمجرد أن الرسالة تبدو إيجابية.
9) H1 وH2 وH3 وH4 وH7 قد تتطلب معلومات إنتاج أو نشر أو بيانات وصفية؛ استخدم NA عند غياب السياق اللازم، مع بيان ذلك.
10) لا تكرر المشكلة نفسها في أكثر من مؤشر إلا إذا شرحت وجه الاختلاف في كل مؤشر.
11) أضف confidence لكل مؤشر: "مرتفع" أو "متوسط" أو "منخفض". هذا تقدير وصفي لمدى استناد الحكم إلى النص، وليس احتمالًا إحصائيًا أو مقياسًا مثبت الصلاحية. خفّضه عند غياب التحقق الخارجي أو نقص السياق.
12) strengths وissues وrecommendations وlimitations قوائم عربية موجزة ومحددة بالنص. لا تضف ادعاءات لم تُفحص.
13) لا تحسب أي متوسطات أو درجات أبعاد أو نتيجة إجمالية؛ سيحسبها التطبيق آليًا.
"""


def _extract_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("لم يُرجع النموذج كائن JSON صالحًا.")
    return json.loads(text[start:end + 1])


def _validate_and_calculate(data, source_text):
    indicators = data.get("indicators", {}) if isinstance(data, dict) else {}
    normalized = {}
    assessable = 0
    na_count = 0
    dim_values = {key: [] for key in DIMENSIONS}

    for code, meta in INDICATORS.items():
        item = indicators.get(code, {})
        if not isinstance(item, dict):
            item = {}
        score = item.get("score")
        if score is not None:
            if isinstance(score, bool) or not isinstance(score, (int, float)) or int(score) != score or not 1 <= int(score) <= 5:
                score = None
            else:
                score = int(score)

        evidence = str(item.get("evidence", "")).strip()
        rationale = str(item.get("rationale", "لم يقدم النموذج تبريرًا محددًا.")).strip()
        na_reason = item.get("na_reason")
        confidence = item.get("confidence", "منخفض")
        if confidence not in ("مرتفع", "متوسط", "منخفض"):
            confidence = "منخفض"

        # A scored item must cite a literal excerpt from the submitted text.
        # If it does not, fail safely to NA rather than displaying fabricated evidence.
        if score is not None and (not evidence or evidence not in source_text):
            score = None
            evidence = "لم يُقدَّم شاهد حرفي قابل للتحقق داخل النص."
            rationale = "حُوّلت النتيجة إلى NA لأن الشاهد المقدم لا يطابق النص المدخل حرفيًا؛ يلزم إعادة التقييم أو المراجعة البشرية."
            na_reason = "تعذر الحكم"
            confidence = "منخفض"

        if score is None:
            na_count += 1
            if na_reason not in ("غير منطبق", "نقص سياق", "تعذر الحكم"):
                na_reason = "تعذر الحكم"
        else:
            assessable += 1
            na_reason = None
            dim_values[meta["dimension"]].append(score)
            if not evidence:
                # Defensive fallback; normally caught by literal-evidence validation above.
                score = None
                assessable -= 1
                na_count += 1
                dim_values[meta["dimension"]].pop()
                na_reason = "تعذر الحكم"

        normalized[code] = {
            "score": score,
            "evidence": evidence or "لا يوجد شاهد نصي كافٍ",
            "rationale": rationale or "لم يقدم النموذج تبريرًا محددًا.",
            "confidence": confidence,
            "na_reason": na_reason,
        }

    dimensions = {}
    valid_scores = []
    for key, label in DIMENSIONS.items():
        denom = 6 if key == "C" else 7
        vals = dim_values[key]
        coverage_pct = round(len(vals) / denom * 100, 1)
        score = round(sum(vals) / len(vals), 2) if len(vals) >= (denom * 0.5) else None
        if score is not None:
            valid_scores.append(score)
        dimensions[key] = {
            "label": label,
            "score": score,
            "coverage": f"{len(vals)}/{denom} ({coverage_pct}%)",
            "assessable": len(vals),
            "total": denom,
        }

    overall = round(sum(valid_scores) / 4, 2) if len(valid_scores) == 4 else None
    note = None if overall is not None else "لم تُحسب النتيجة الإجمالية لأن واحدًا أو أكثر من الأبعاد لم يحقق الحد الأدنى للتغطية (50%)."

    def clean_list(value):
        if not isinstance(value, list):
            return []
        return [str(x).strip() for x in value if str(x).strip()][:10]

    return {
        "framework": "IAQF",
        "version": "2.1-demo",
        "indicators": normalized,
        "dimensions": dimensions,
        "overall_score": overall,
        "overall_note": note,
        "coverage": {"assessable": assessable, "not_applicable": na_count, "total": 27},
        "strengths": clean_list(data.get("strengths", [])),
        "issues": clean_list(data.get("issues", [])),
        "recommendations": clean_list(data.get("recommendations", [])),
        "limitations": clean_list(data.get("limitations", [])),
    }


def evaluate_text(content: str):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        raise RuntimeError("لم يتم إعداد GEMINI_API_KEY في إعدادات Secrets الخاصة بتطبيق Streamlit.")

    model = st.secrets.get("GEMINI_MODEL", "gemini-3.8-flash")
    client = genai.Client(api_key=api_key)
    indicator_spec = {
        code: {
            "name": meta["name"],
            "dimension": meta["dimension"],
            "evaluation_guidance": INDICATOR_GUIDANCE[code],
        }
        for code, meta in INDICATORS.items()
    }
    output_schema = {
        "indicators": {
            "L1": {
                "score": "integer 1..5 or null",
                "evidence": "verbatim short quote from input, or explanation if NA",
                "rationale": "specific indicator-based explanation",
                "confidence": "مرتفع أو متوسط أو منخفض",
                "na_reason": "غير منطبق أو نقص سياق أو تعذر الحكم أو null",
            }
        },
        "strengths": ["..."],
        "issues": ["..."],
        "recommendations": ["..."],
        "limitations": ["..."],
    }
    prompt = (
        SYSTEM_INSTRUCTIONS
        + "\nالمؤشرات وتعريفاتها التشغيلية:\n"
        + json.dumps(indicator_spec, ensure_ascii=False)
        + "\n\nشكل JSON المطلوب (كرّر بنية المؤشر لكل الرموز الـ27):\n"
        + json.dumps(output_schema, ensure_ascii=False)
        + "\n\nالنص المراد تقييمه حرفيًا بين العلامتين:\n<<<TEXT>>>\n"
        + content
        + "\n<<<END TEXT>>>"
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    data = _extract_json(response.text or "")
    return _validate_and_calculate(data, content)

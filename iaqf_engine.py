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
    "E2": "افحص قابلية تحديد المصادر وملاءمتها الظاهرة. لا تصف المصدر بأنه موثوق بعد تحقق مستقل ما لم تُفحص الوثيقة الأصلية؛ سجّل أن التحقق الخارجي لم يُجرَ في هذا التطبيق.",
    "E3": "افحص مقدار الأدلة التي يقدمها النص لدعم ادعاءاته. يمكن أن تكون الدرجة منخفضة بسبب غياب الشواهد حتى إن كانت الادعاءات محتملة الصحة.",
    "E4": "افحص صلاحية الانتقال من المقدمات إلى النتائج ووجود مغالطات أو قفزات؛ لا تمنح درجة مرتفعة لمجرد وجود روابط لغوية.",
    "E5": "افحص مؤشرات الاختلاق الظاهرة فقط. لا تستنتج مقاومة الهلوسة من غياب علامات ظاهرة؛ إثبات المقاومة يحتاج تحققًا مستقلًا أو مقارنة بمصادر/نماذج، وهو غير متاح في هذا التطبيق.",
    "E6": "افصل بين معاصرة الموضوع وحداثة المعلومة. ذكر الذكاء الاصطناعي أو التكنولوجيا لا يثبت الحداثة؛ يتطلب الحكم على المعلومات المتغيرة تاريخًا أو مصدرًا حديثًا يمكن التحقق منه.",
    "E7": "افحص التناقضات داخل النص نفسه، لا صحة الادعاءات الخارجية ولا جودة الاستدلال.",
    "C1": "افحص ملاءمة المحتوى للسياق الثقافي المحدد في النص. لا تفترض وجود ثقافة عربية واحدة ولا تمنح درجة عالية اعتمادًا على تعميمات عن المجتمع العربي.",
    "C2": "افحص تمثيل الهوية عندما يعرض النص هوية أو جماعة محددة. إذا لم يكن ذلك موضوعًا أو مطلبًا في النص، استخدم NA بدل افتراض نجاح التمثيل.",
    "C3": "افحص وجود معالجة فعلية للاختلافات أو دليل على احترامها. اللغة الشاملة أو المحايدة وحدها لا تثبت احترام التنوع؛ إذا لم يعالج النص التنوع ولم يكن مطلوبًا، ففكر في NA.",
    "C4": "افحص الإنصاف في عرض الثقافات والجماعات وتجنب الصور النمطية أو التراتبية أو التحيز في المقارنة؛ لا تساوه بمجرد ذكر التنوع.",
    "C5": "افحص ملاءمة الرسالة للسياق الاجتماعي والجمهور وآثارها الاجتماعية الظاهرة، دون استنتاجات واسعة غير مدعومة.",
    "C6": "افحص دقة الوقائع والتواريخ والتفسيرات التاريخية. إذا لم يتناول النص التاريخ، استخدم NA.",
    "H1": "افحص وجود بيانات شخصية أو حساسة وطريقة التعامل معها. فرّق بين تصريح النص بأنه لم يستخدم بيانات وبين التحقق الفعلي من مسار المعالجة؛ صِف التصريح بأنه معلومة سياقية مقدمة لا حقيقة متحققة.",
    "H2": "افحص الإسناد والتراخيص وسياق المصدر. لا تعتبر وصف النص بأنه أصلي إثباتًا للأصالة؛ ذلك يتطلب فحصًا مستقلًا للتشابه والمصادر.",
    "H3": "افحص الإفصاح عن استخدام الذكاء الاصطناعي في سياق يتطلب أو يتوقع الإفصاح. غياب الإفصاح في النص وحده لا يثبت مخالفة إذا كان سياق النشر ومتطلباته مجهولين؛ عندئذ استخدم NA واذكر نقص السياق.",
    "H4": "افحص وضوح الجهة المسؤولة وآليات التصحيح أو الشكوى والمساءلة. لا تخلطه بالإشراف البشري H7.",
    "H5": "افحص التمييز أو الإقصاء أو المعاملة غير المتكافئة في النص. الشمول اللفظي وحده لا يثبت انعدام التمييز في كل السياقات.",
    "H6": "افحص المخاطر العملية أو الضرر المحتمل وإرشادات الاستخدام الآمن. لا تمنح 5 لمجرد وجود نصيحة عامة بالحذر.",
    "H7": "افحص الدليل على مراجعة أو إشراف بشري فعلي. إذا كان الدليل مجرد تصريح داخل سيناريو النص، صنّفه إقرارًا سياقيًا غير متحقق منه خارجيًا.",
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
11) أضف confidence لكل مؤشر: "مرتفع" أو "متوسط" أو "منخفض". هذا تقدير وصفي لمدى استناد الحكم إلى النص، وليس احتمالًا إحصائيًا أو مقياسًا مثبت الصلاحية. لا تستخدم "مرتفع" لمجرد أن الإجابة تبدو واثقة؛ استخدمه فقط عندما يكون الشاهد مباشرًا وواضحًا والمعيار قابلًا للحكم من النص. استخدم "متوسط" للأحكام التفسيرية أو الجزئية، و"منخفض" عند نقص السياق أو غياب التحقق الخارجي أو وجود غموض.
14) يجب أن يكون كل شاهد رقمي اقتباسًا حرفيًا متصلًا من النص المدخل، دون حذف بعلامة الحذف أو إعادة صياغة أو إضافة علامات ترقيم غير موجودة. اختر أقصر مقطع يثبت المعيار. إذا تعذر العثور على شاهد حرفي، حاول مرة أخرى بمقطع آخر من النص قبل تقرير تعذر الحكم.
15) لا تحول المؤشر إلى NA لمجرد أن الشاهد الأول غير صالح؛ أعد البحث داخل النص عن شاهد بديل. استخدم NA فقط إذا كان المعيار غير منطبق فعلًا أو أن المعلومات اللازمة للحكم غير متاحة أو تعذر الحكم بعد محاولة استخراج شاهد صالح.
12) strengths وissues وrecommendations وlimitations قوائم عربية موجزة ومحددة بالنص. لا تضف ادعاءات لم تُفحص.
13) لا تحسب أي متوسطات أو درجات أبعاد أو نتيجة إجمالية؛ سيحسبها التطبيق آليًا.
أ) أضف لكل مؤشر الحقول التالية:
   - evidence_basis: واحدة من "شاهد من النص" أو "بيانات سياقية مقدمة" أو "تحليل استدلالي" أو "يتطلب تحققًا خارجيًا" أو "غير متاح".
   - external_verification: اجعلها دائمًا false؛ هذا التطبيق لا يجري بحثًا خارجيًا ولا يفحص قواعد بيانات أو مصادر أصلية.
   - verification_note: جملة موجزة توضّح ما الذي لم يتم التحقق منه عند الحاجة.
ب) لا تصف المراجع أو الوقائع أو أصالة النص أو المراجعة البشرية بأنها متحققة خارجيًا. الإقرار الوارد في النص/سيناريو الاختبار دليل على أن الإقرار موجود، وليس دليلًا مستقلًا على صحة مضمونه.
ج) E2: ميّز بين وجود مرجع قابل للتحديد وبين التحقق من موثوقيته ومطابقته للادعاء. E5: غياب علامة اختلاق ظاهرة لا يثبت مقاومة الهلوسة. E6: معاصرة الموضوع لا تثبت حداثة البيانات. C3: الشمول اللفظي وحده لا يثبت احترام التنوع. H1/H2/H7: التصريحات السياقية لا تعد تحققًا مستقلًا.
د) إذا كان الحكم يعتمد على إقرار سياقي أو ادعاء أصالة أو وصف مراجعة بشرية، فاجعل الثقة متوسطة أو منخفضة ما لم يوجد تحقق مستقل؛ لا تستخدم "مرتفع" لمجرد أن العبارة صريحة.
"""


def _extract_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("لم يُرجع النموذج كائن JSON صالحًا.")
    return json.loads(text[start:end + 1])



def _normalized_quote(value):
    """Normalize whitespace only; do not alter words or punctuation."""
    return " ".join(str(value or "").split())


def _quote_is_verbatim(evidence, source_text):
    quote = _normalized_quote(evidence)
    source = _normalized_quote(source_text)
    return bool(quote) and quote in source


def _repair_invalid_evidence(client, model, source_text, data):
    """Ask the model once to repair only evidence quotes that are not verbatim.

    This is a bounded repair pass, not independent verification of the score.
    """
    indicators = data.get("indicators", {}) if isinstance(data, dict) else {}
    invalid = []
    for code, item in indicators.items():
        if code in INDICATORS and isinstance(item, dict) and item.get("score") is not None:
            if not _quote_is_verbatim(item.get("evidence", ""), source_text):
                invalid.append(code)
    if not invalid:
        return data, []

    repair_prompt = (
        "أصلح حقول الشاهد فقط للمؤشرات التالية، ولا تغيّر الدرجة أو المبرر أو الثقة أو سبب NA. "
        "لكل مؤشر أعد اقتباسًا حرفيًا متصلًا موجودًا في النص أدناه كما هو تمامًا، "
        "من دون حذف أو إعادة صياغة أو علامات حذف. إذا لم يوجد شاهد مناسب، اجعل score=null، "
        "واكتب سببًا واضحًا في rationale وna_reason='تعذر الحكم'. "
        "أعد JSON فقط بالشكل {\"indicators\":{...}}.\n"
        "المؤشرات المطلوب إصلاحها: " + json.dumps(invalid, ensure_ascii=False) + "\n"
        "النص الأصلي بين العلامتين:\n<<<TEXT>>>\n" + source_text + "\n<<<END TEXT>>>\n"
        "النتائج الحالية لهذه المؤشرات:\n" + json.dumps({k: indicators.get(k) for k in invalid}, ensure_ascii=False)
    )
    try:
        response = client.models.generate_content(
            model=model,
            contents=repair_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        repaired = _extract_json(response.text or "")
        repaired_items = repaired.get("indicators", {}) if isinstance(repaired, dict) else {}
        for code in invalid:
            if isinstance(repaired_items.get(code), dict):
                indicators[code] = repaired_items[code]
        data["indicators"] = indicators
        return data, invalid
    except Exception:
        # Keep the original data; strict validation below will safely mark invalid quotes.
        return data, invalid


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
        if score is not None and not _quote_is_verbatim(evidence, source_text):
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

        evidence_basis = item.get("evidence_basis", "شاهد من النص" if score is not None else "غير متاح")
        allowed_bases = ("شاهد من النص", "بيانات سياقية مقدمة", "تحليل استدلالي", "يتطلب تحققًا خارجيًا", "غير متاح")
        if evidence_basis not in allowed_bases:
            evidence_basis = "شاهد من النص" if score is not None else "غير متاح"
        verification_note = str(item.get("verification_note", "")).strip()
        # This app version does not perform web/source verification. Never accept a model claim that it did.
        normalized[code] = {
            "score": score,
            "evidence": evidence or "لا يوجد شاهد نصي كافٍ",
            "rationale": rationale or "لم يقدم النموذج تبريرًا محددًا.",
            "confidence": confidence,
            "na_reason": na_reason,
            "evidence_status": "مطابق للنص" if score is not None else "لا يوجد شاهد رقمي معتمد",
            "evidence_basis": evidence_basis,
            "external_verification": False,
            "verification_note": verification_note or "لم يُجرَ تحقق خارجي مستقل في هذا الإصدار.",
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
        "version": "2.3-demo",
        "indicators": normalized,
        "dimensions": dimensions,
        "overall_score": overall,
        "overall_note": note,
        "coverage": {"assessable": assessable, "not_applicable": na_count, "total": 27},
        "external_verification_performed": False,
        "verification_scope": "تحليل النص والشواهد المقدمة فقط؛ لا يتضمن بحثًا خارجيًا أو فحصًا للمصادر الأصلية أو كشفًا مستقلًا للانتحال.",
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
                "evidence_basis": "إحدى الفئات الخمس المحددة في التعليمات",
                "external_verification": "false",
                "verification_note": "ما لم يتم التحقق منه خارجيًا",
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
    data, repaired_codes = _repair_invalid_evidence(client, model, content, data)
    result = _validate_and_calculate(data, content)
    result["version"] = "2.3-demo"
    result["external_verification_performed"] = False
    result["verification_scope"] = "تحليل النص والشواهد المقدمة فقط؛ لا يتضمن بحثًا خارجيًا أو فحصًا للمصادر الأصلية أو كشفًا مستقلًا للانتحال."
    result["evidence_repair_attempted"] = repaired_codes
    result["evidence_validation_note"] = (
        "أُجريت محاولة واحدة لإصلاح الشواهد غير المطابقة قبل اعتماد النتائج. "
        "مطابقة الاقتباس للنص لا تثبت وحدها صحة الدرجة أو كفاية الدليل العلمي."
    )
    return result

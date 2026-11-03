import json
import re
import time
import random
import streamlit as st
from google import genai
from google.genai import types


TRANSIENT_API_CODES = {"429", "500", "502", "503", "504"}


def _api_error_code(exc):
    """Extract a status code from Google GenAI exceptions without depending on SDK internals."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code is not None:
        return str(code)
    match = re.search(r"(?<!\d)(429|500|502|503|504)(?!\d)", str(exc))
    return match.group(1) if match else ""


def _generate_content_resilient(client, model, contents, config, trace=None, stage="generation"):
    """
    Retry transient Gemini service failures with bounded exponential backoff.
    An optional fallback model is used only when explicitly configured in Secrets,
    so research runs never silently change model.
    """
    candidates = [model]
    try:
        fallback = str(st.secrets.get("GEMINI_FALLBACK_MODEL", "") or "").strip()
    except Exception:
        fallback = ""
    if fallback and fallback != model:
        candidates.append(fallback)

    attempts_log = []
    last_error = None
    for candidate_index, candidate in enumerate(candidates):
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=candidate,
                    contents=contents,
                    config=config,
                )
                attempts_log.append({
                    "stage": stage,
                    "model": candidate,
                    "attempts": attempt,
                    "status": "success",
                })
                if trace is not None:
                    trace.extend(attempts_log)
                return response, candidate
            except Exception as exc:
                last_error = exc
                code = _api_error_code(exc)
                attempts_log.append({
                    "stage": stage,
                    "model": candidate,
                    "attempt": attempt,
                    "error_code": code or "unknown",
                    "status": "retrying" if code in TRANSIENT_API_CODES and attempt < 3 else "failed",
                })
                if code not in TRANSIENT_API_CODES:
                    if trace is not None:
                        trace.extend(attempts_log)
                    raise
                if attempt < 3:
                    time.sleep((2 ** (attempt - 1)) + random.uniform(0, 0.35))
                    continue
                if candidate_index < len(candidates) - 1:
                    break
                if trace is not None:
                    trace.extend(attempts_log)
                raise RuntimeError(
                    f"تعذر الاتصال بنموذج Gemini بعد 3 محاولات (HTTP {code or 'غير محدد'}). "
                    "قد يكون السبب ازدحامًا مؤقتًا أو حدود الخدمة. أعد المحاولة لاحقًا، "
                    "أو أضف GEMINI_FALLBACK_MODEL إلى Secrets لتفعيل نموذج احتياطي."
                ) from exc

    if trace is not None:
        trace.extend(attempts_log)
    raise RuntimeError(f"فشل الاتصال بخدمة Gemini: {last_error}") from last_error


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


def _repair_invalid_evidence(client, model, source_text, data, api_trace=None):
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
        response, used_model = _generate_content_resilient(
            client, model, repair_prompt,
            types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
            trace=api_trace, stage="evidence_repair",
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


def _audit_evidence_quality(client, model, source_text, data, api_trace=None):
    """Second-pass model audit of evidence relevance, sufficiency and score consistency.

    Literal matching is checked deterministically elsewhere. This audit is an
    automated review aid, not independent human or external verification.
    """
    indicators = data.get("indicators", {}) if isinstance(data, dict) else {}
    candidates = {}
    for code, item in indicators.items():
        if code in INDICATORS and isinstance(item, dict) and item.get("score") is not None:
            candidates[code] = {
                "indicator": INDICATORS[code]["name"],
                "guidance": INDICATOR_GUIDANCE[code],
                "score": item.get("score"),
                "evidence": item.get("evidence", ""),
                "rationale": item.get("rationale", ""),
                "confidence": item.get("confidence", "منخفض"),
            }
    if not candidates:
        return {}, {"attempted": False, "status": "لا توجد مؤشرات رقمية للمراجعة"}

    audit_prompt = (
        "أنت مدقق جودة أدلة مستقل عن مرحلة التقييم الأولية. افحص كل مؤشر مرقم أدناه "
        "من حيث: (1) صلة الاقتباس بالمؤشر تحديدًا، (2) كفاية الاقتباس والتبرير لدعم الدرجة "
        "الممنوحة، (3) اتساق الدرجة مع الاقتباس والتبرير. لا تتحقق من صحة الوقائع خارجيًا. "
        "لا تعتبر مجرد تطابق الاقتباس مع النص دليلًا على صلته أو كفايته. "
        "استخدم verdict واحدة فقط: 'قوي' أو 'جزئي' أو 'غير مرتبط' أو 'متناقض'. "
        "'جزئي' يعني أن الاقتباس ذو صلة لكنه لا يبرر تمامًا مستوى الدرجة. "
        "'غير مرتبط' يعني أنه لا يدعم المؤشر. 'متناقض' يعني أن الدليل أو التبرير يناقض الدرجة. "
        "لكل مؤشر أعد calibrated_score كعدد صحيح من 1 إلى 5 أو null، وcalibration_reason يشرح القرار. "
        "لا يجوز أن تتجاوز calibrated_score الدرجة الأصلية مطلقًا. إذا كان verdict='جزئي' فلا تتجاوز 4، "
        "واختر الدرجة التي يبررها الشاهد فعلًا. إذا كان verdict='قوي' يجوز إبقاء الدرجة أو خفضها فقط. "
        "إذا كان verdict='غير مرتبط' أو 'متناقض' فاجعل calibrated_score=null. "
        "أعد JSON فقط بهذا الشكل: {\"audits\":{\"L1\":{\"verdict\":\"قوي\","
        "\"calibrated_score\":4,\"calibration_reason\":\"...\","
        "\"relevance\":\"...\",\"sufficiency\":\"...\",\"consistency\":\"...\"}}}. "
        "لا تخترع شواهد ولا ترفع أي درجة.\n\n"
        "تعريفات المؤشرات:\n" + json.dumps(INDICATOR_GUIDANCE, ensure_ascii=False)
        + "\n\nالمؤشرات المراد تدقيقها:\n" + json.dumps(candidates, ensure_ascii=False)
        + "\n\nالنص الأصلي:\n<<<TEXT>>>\n" + source_text + "\n<<<END TEXT>>>"
    )
    try:
        response, used_model = _generate_content_resilient(
            client, model, audit_prompt,
            types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
            trace=api_trace, stage="evidence_audit",
        )
        parsed = _extract_json(response.text or "")
        audits = parsed.get("audits", {}) if isinstance(parsed, dict) else {}
        cleaned = {}
        allowed = ("قوي", "جزئي", "غير مرتبط", "متناقض")
        for code in candidates:
            item = audits.get(code, {})
            if not isinstance(item, dict):
                item = {}
            verdict = item.get("verdict")
            if verdict not in allowed:
                verdict = "تعذر التدقيق"
            cleaned[code] = {
                "verdict": verdict,
                "relevance": str(item.get("relevance", "")).strip(),
                "sufficiency": str(item.get("sufficiency", "")).strip(),
                "consistency": str(item.get("consistency", "")).strip(),
                "recommended_action": str(item.get("recommended_action", "")).strip(),
                "calibrated_score": item.get("calibrated_score"),
                "calibration_reason": str(item.get("calibration_reason", "")).strip(),
            }
        missing = [code for code, audit in cleaned.items() if audit["verdict"] == "تعذر التدقيق"]
        status = "اكتمل التدقيق الآلي للأدلة" if not missing else "اكتمل جزئيًا؛ بعض المؤشرات لم تُدقّق"
        return cleaned, {"attempted": True, "status": status, "und_audited": missing}
    except Exception as exc:
        return {}, {
            "attempted": True,
            "status": "تعذر إكمال التدقيق الآلي للأدلة",
            "error": str(exc)[:300],
        }


def _validate_and_calculate(data, source_text, evidence_audits=None):
    indicators = data.get("indicators", {}) if isinstance(data, dict) else {}
    evidence_audits = evidence_audits or {}
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
        audit = evidence_audits.get(code, {})
        verdict = audit.get("verdict", "لم يُدقّق") if isinstance(audit, dict) else "لم يُدقّق"

        # Calibrate only when the second-pass audit actually returned a valid verdict.
        original_score = score
        calibrated_score = None
        calibration_reason = "لم تُجرَ المعايرة؛ احتُفظ بالدرجة الأولية دون اعتمادها كدرجة معايرة."
        score_adjusted = False
        if score is not None and verdict in ("غير مرتبط", "متناقض"):
            calibrated_score = None
            calibration_reason = audit.get("calibration_reason") or (
                "لم يُعتمد الحكم الرقمي لأن الشاهد غير مرتبط بالمؤشر أو متناقض مع الدرجة."
            )
            na_count += 1
            assessable -= 1
            if dim_values[meta["dimension"]]:
                dim_values[meta["dimension"]].pop()
            na_reason = "تعذر الحكم"
            confidence = "منخفض"
            rationale = calibration_reason
            score = None
            score_adjusted = True
        elif score is not None and verdict in ("قوي", "جزئي"):
            proposed = audit.get("calibrated_score")
            if isinstance(proposed, bool) or not isinstance(proposed, int) or not 1 <= proposed <= 5:
                proposed = original_score
            # Hard safety caps: calibration can never raise a score; partial evidence is capped at 4.
            calibrated_score = min(original_score, proposed)
            if verdict == "جزئي":
                calibrated_score = min(calibrated_score, 4)
                if confidence == "مرتفع":
                    confidence = "متوسط"
            calibration_reason = audit.get("calibration_reason") or (
                "الدرجة أُبقيت بعد مراجعة الدليل." if calibrated_score == original_score
                else "خُفّضت الدرجة لتتناسب مع قوة الشاهد والتبرير."
            )
            score = calibrated_score
            score_adjusted = score != original_score
            # Replace the original value already included in the dimension accumulator.
            if dim_values[meta["dimension"]]:
                dim_values[meta["dimension"]][-1] = score
        elif score is not None:
            calibrated_score = None
            calibration_reason = "تعذر التدقيق؛ عُرضت الدرجة الأولية للشفافية، ولم تُعتمد ضمن النتائج المعايرة."
            # Fail safely: keep the raw score visible, but exclude it from calibrated
            # dimension and overall averages until the evidence audit succeeds.
            if dim_values[meta["dimension"]]:
                dim_values[meta["dimension"]].pop()
            assessable -= 1
            na_count += 1
            na_reason = "تعذر الحكم"
            score = None
            confidence = "منخفض"

        normalized[code] = {
            "score": score,
            "original_score": original_score,
            "calibrated_score": calibrated_score,
            "score_adjusted": score_adjusted,
            "calibration_reason": calibration_reason,
            "calibration_status": (
                "اكتملت" if verdict in ("قوي", "جزئي", "غير مرتبط", "متناقض")
                else ("لم تُعايَر" if original_score is not None else "غير منطبق")
            ),
            "evidence": evidence or "لا يوجد شاهد نصي كافٍ",
            "rationale": rationale or "لم يقدم النموذج تبريرًا محددًا.",
            "confidence": confidence,
            "na_reason": na_reason,
            "evidence_status": "مطابق حرفيًا" if _quote_is_verbatim(evidence, source_text) else "غير مطابق",
            "evidence_relevance": audit.get("relevance", "") if isinstance(audit, dict) else "",
            "evidence_sufficiency": audit.get("sufficiency", "") if isinstance(audit, dict) else "",
            "score_consistency": audit.get("consistency", "") if isinstance(audit, dict) else "",
            "evidence_quality_verdict": verdict,
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
        "version": "2.4.1.1-demo",
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

    api_trace = []
    response, primary_model_used = _generate_content_resilient(
        client, model, prompt,
        types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
        trace=api_trace, stage="initial_evaluation",
    )
    data = _extract_json(response.text or "")
    data, repair_attempted = _repair_invalid_evidence(
        client, primary_model_used, content, data, api_trace=api_trace
    )

    indicators_after_repair = data.get("indicators", {}) if isinstance(data, dict) else {}
    repair_succeeded = [
        code for code in repair_attempted
        if isinstance(indicators_after_repair.get(code), dict)
        and _quote_is_verbatim(indicators_after_repair[code].get("evidence", ""), content)
    ]
    repair_failed = [code for code in repair_attempted if code not in repair_succeeded]

    evidence_audits, audit_meta = _audit_evidence_quality(client, primary_model_used, content, data, api_trace=api_trace)
    result = _validate_and_calculate(data, content, evidence_audits)
    result["version"] = "2.5.1"
    result["api_diagnostics"] = api_trace
    result["model_used"] = primary_model_used
    result["external_verification_performed"] = False
    result["verification_scope"] = (
        "تحليل النص والشواهد المقدمة ومراجعة آلية داخلية لصلتها وكفايتها واتساقها؛ "
        "لا يتضمن بحثًا خارجيًا أو فحصًا للمصادر الأصلية أو كشفًا مستقلًا للانتحال."
    )
    result["evidence_repair"] = {
        "attempted": repair_attempted,
        "succeeded": repair_succeeded,
        "failed": repair_failed,
    }
    result["evidence_repair_attempted"] = repair_attempted
    result["evidence_audit"] = audit_meta
    calibrated_items = [x for x in result.get("indicators", {}).values() if x.get("original_score") is not None]
    result["score_calibration"] = {
        "status": "اكتملت المعايرة" if audit_meta.get("status") == "اكتمل التدقيق الآلي للأدلة" and not audit_meta.get("error") else "لم تكتمل المعايرة بالكامل",
        "audited": sum(1 for x in calibrated_items if x.get("calibration_status") == "اكتملت"),
        "not_calibrated": sum(1 for x in calibrated_items if x.get("calibration_status") == "لم تُعايَر"),
        "adjusted": sum(1 for x in calibrated_items if x.get("score_adjusted") and x.get("calibrated_score") is not None),
        "reduced": sum(1 for x in calibrated_items if x.get("score_adjusted") and x.get("calibrated_score") is not None and x.get("calibrated_score") < x.get("original_score")),
        "converted_to_NA": sum(1 for x in result.get("indicators", {}).values() if x.get("original_score") is not None and x.get("score") is None),
        "not_a_human_or_external_validation": True,
    }
    result["evidence_validation_note"] = (
        "تُفحص مطابقة الاقتباس حرفيًا برمجيًا، ثم تُراجع صلته بالمؤشر وكفايته واتساقه مع الدرجة "
        "بمراجعة آلية ثانية. هذه المراجعة ليست تحققًا بشريًا أو خارجيًا، وقد تخطئ؛ راجع الحالات "
        "الجزئية أو غير المدققة قبل اعتماد النتائج."
    )
    return result

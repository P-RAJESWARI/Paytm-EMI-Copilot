"""The weekly message's sentences in English and Tamil, from M5 `body` and M8 `title`/`p1`-`p3`.

Plan Q9 corrections: "Most who left did so after seeing the plans" became "The biggest drop was
after ..." (37 of 76 is not most), and the action names the computed monthly figures instead of
"near ₹3,000". Plain words, no urgency, nothing called "best". Every Tamil string is a draft for
a native speaker to review; mockup Tamil is reused where the sentence did not change.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from emi_copilot.domain.funnel import FunnelStage


class MessageLanguage(StrEnum):
    """A language the weekly message is written in (the M5 and M8 EN / தமிழ் toggle)."""

    ENGLISH = "en"
    TAMIL = "ta"


@dataclass(frozen=True, slots=True)
class WeeklyMessageWording:
    """One language's sentence templates; {placeholders} take already formatted values."""

    title_within_one_month: str
    title_across_two_months: str
    no_sales_yet: str
    bought_on_emi: str
    biggest_drop_after_stage: Mapping[FunnelStage, str]
    missed_sales: str
    money_due: str
    longer_no_cost_action: str
    cheaper_model_action: str
    alternatives_joiner: str
    title_month_names: tuple[str, ...]
    due_date_month_names: tuple[str, ...]


ENGLISH_MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)  # fmt: skip

ENGLISH_WORDING = WeeklyMessageWording(
    title_within_one_month="Your EMI sales, {first_day} to {last_day} {last_month}",
    title_across_two_months=(
        "Your EMI sales, {first_day} {first_month} to {last_day} {last_month}"
    ),
    no_sales_yet="No EMI sales this week yet.",
    bought_on_emi="{paid_count} of {started_count} customers bought on EMI.",
    biggest_drop_after_stage=MappingProxyType(
        {
            FunnelStage.STARTED: "The biggest drop was before customers told a budget.",
            FunnelStage.BUDGET_TOLD: "The biggest drop was after customers told a budget.",
            FunnelStage.PLANS_VIEWED: "The biggest drop was after seeing the plans.",
            FunnelStage.AGREED: "The biggest drop was after agreeing to a plan, before paying.",
        }
    ),
    missed_sales=(
        "{missed_count} customers wanted under {budget_ceiling} a month with nothing extra, "
        "and no plan fit."
    ),
    money_due="{total_due} is due from brands, first payment around {next_date}.",
    longer_no_cost_action=(
        "One thing to do: ask the brand for a {tenures}-month no-cost plan on {product_name}. "
        "That would be {monthly_amounts} a month."
    ),
    cheaper_model_action=(
        "One thing to do: keep {product_name} ready for budget buyers. At {list_price} it is "
        "{monthly_amount} a month for {tenure} months with nothing extra."
    ),
    alternatives_joiner=" or ",
    title_month_names=ENGLISH_MONTH_NAMES,
    due_date_month_names=tuple(month_name[:3] for month_name in ENGLISH_MONTH_NAMES),
)

# draft: needs native review (every Tamil month name)
TAMIL_MONTH_NAMES = (
    "ஜனவரி", "பிப்ரவரி", "மார்ச்", "ஏப்ரல்", "மே", "ஜூன்",
    "ஜூலை", "ஆகஸ்ட்", "செப்டம்பர்", "அக்டோபர்", "நவம்பர்", "டிசம்பர்",
)  # fmt: skip

TAMIL_WORDING = WeeklyMessageWording(
    # draft: needs native review
    title_within_one_month="உங்கள் EMI விற்பனை, {first_day} முதல் {last_day} {last_month}",
    # draft: needs native review
    title_across_two_months=(
        "உங்கள் EMI விற்பனை, {first_day} {first_month} முதல் {last_day} {last_month}"
    ),
    # draft: needs native review
    no_sales_yet="இந்த வாரம் இன்னும் EMI விற்பனை இல்லை.",
    # draft: needs native review
    bought_on_emi="{started_count} வாடிக்கையாளர்களில் {paid_count} பேர் EMI-யில் வாங்கினர்.",
    biggest_drop_after_stage=MappingProxyType(
        {
            # draft: needs native review
            FunnelStage.STARTED: "மாதத் தொகையைச் சொல்லும் முன்பே அதிகம் பேர் விலகினர்.",
            # draft: needs native review
            FunnelStage.BUDGET_TOLD: "மாதத் தொகையைச் சொன்ன பின் அதிகம் பேர் விலகினர்.",
            # draft: needs native review
            FunnelStage.PLANS_VIEWED: "திட்டங்களைப் பார்த்த பின் அதிகம் பேர் விலகினர்.",
            # draft: needs native review
            FunnelStage.AGREED: ("திட்டத்துக்கு ஒப்புக்கொண்ட பின், பணம் செலுத்தும் முன் அதிகம் பேர் விலகினர்."),
        }
    ),
    # draft: needs native review
    missed_sales=(
        "{missed_count} பேர் கூடுதல் இல்லாமல் மாதம் {budget_ceiling}-க்குள் "
        "விரும்பினர், எந்தத் திட்டமும் பொருந்தவில்லை."
    ),
    # draft: needs native review
    money_due=("பிராண்டுகளிடமிருந்து {total_due} வர வேண்டும், முதல் தொகை சுமார் {next_date}."),
    # draft: needs native review
    longer_no_cost_action=(
        "செய்ய வேண்டியது: {product_name}-க்கு {tenures} மாத கட்டணமில்லா "
        "திட்டத்தை பிராண்டிடம் கேளுங்கள். அது மாதம் {monthly_amounts} ஆகும்."
    ),
    # draft: needs native review
    cheaper_model_action=(
        "செய்ய வேண்டியது: குறைந்த பட்ஜெட் வாடிக்கையாளர்களுக்காக "
        "{product_name}-ஐ தயாராக வைத்திருங்கள். {list_price} விலையில் அது "
        "கூடுதல் இல்லாமல் {tenure} மாதங்களுக்கு மாதம் {monthly_amount}."
    ),
    # draft: needs native review
    alternatives_joiner=" அல்லது ",
    title_month_names=TAMIL_MONTH_NAMES,
    due_date_month_names=TAMIL_MONTH_NAMES,
)

WORDING_BY_LANGUAGE: Mapping[MessageLanguage, WeeklyMessageWording] = MappingProxyType(
    {MessageLanguage.ENGLISH: ENGLISH_WORDING, MessageLanguage.TAMIL: TAMIL_WORDING}
)

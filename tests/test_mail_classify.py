from __future__ import annotations

from integrations.mail_classify import (
    KIND_APPLICATION_ACK,
    KIND_IGNORE,
    KIND_REJECTED_HR,
    KIND_REPLIED,
    KIND_SCREENING,
    classify_from_headers,
)


def test_classify_welltech_ack() -> None:
    event = classify_from_headers(
        message_id="<1@welltech.com>",
        subject="Thanks for Applying to Welltech!",
        from_header="Welltech Recruitment Team <recruiting@welltech.com>",
        body_text="Dear Max,\n\nThanks for applying to Welltech! We received your application.\n",
    )
    assert event.kind == KIND_APPLICATION_ACK
    assert event.company == "Welltech"


def test_classify_welltech_via_ashby_ses() -> None:
    event = classify_from_headers(
        message_id="<0100019fadd13d4f-b8c430b5@email.amazonses.com>",
        subject="Thanks for Applying to Welltech!",
        from_header="Welltech <jobs@ashbyhq.com>",
        body_text="Dear Max,\n\nThanks for applying to Welltech!\n",
    )
    assert event.kind == KIND_APPLICATION_ACK
    assert event.company == "Welltech"


def test_classify_nix_ack() -> None:
    event = classify_from_headers(
        message_id="<2@n-ix.com>",
        subject="Thank you for your application!",
        from_header="Recruitment Team <recruitmentteam@n-ix.com>",
        body_text=(
            "Dear Max,\nThank you for your interest in N-iX!\n"
            "APPLICATION RECEIVED for the Senior Mobile/Web Engineer position.\n"
        ),
    )
    assert event.kind == KIND_APPLICATION_ACK
    assert event.company == "N-iX"
    assert "Mobile" in event.role_hint or "Engineer" in event.role_hint


def test_classify_nix_solutions_ack_ignores_unsubscribe_footer() -> None:
    event = classify_from_headers(
        message_id="<ack@nixsolutions.com>",
        subject="From NIX",
        from_header="NIX <hr@nixsolutions.com>",
        body_text=(
            "Hi, Max!\n"
            "Ми отримали ваше резюме на vacancy Middle iOS Developer.\n"
            "Резюме буде розглянуте експертами NIX найближчим часом.\n"
            "Ми зв'яжемося з вами як тільки отримаємо їх рішення.\n"
            "Дякуємо, що зацікавились NIX та заповнили резюме.\n"
            "Відмовитися від повідомлень можна, натиснувши тут"
        ),
    )

    assert event.kind == KIND_APPLICATION_ACK
    assert event.company == "NIX"
    assert event.role_hint == "Middle iOS Developer"


def test_classify_distinguishes_nix_companies_by_sender_domain() -> None:
    n_ix = classify_from_headers(
        message_id="<ack@n-ix.com>",
        subject="From NIX",
        from_header="Recruitment Team <recruitmentteam@n-ix.com>",
        body_text="Thank you for your application!",
    )
    nix = classify_from_headers(
        message_id="<ack@nixsolutions.com>",
        subject="From N-iX",
        from_header="NIX <hr@nixsolutions.com>",
        body_text="Ми отримали ваше резюме.",
    )

    assert n_ix.company == "N-iX"
    assert nix.company == "NIX"


def test_classify_reject() -> None:
    event = classify_from_headers(
        message_id="<3@acme.com>",
        subject="Update on your application",
        from_header="HR <jobs@acme.io>",
        body_text=(
            "Unfortunately we will not be moving forward with other candidates "
            "at this time."
        ),
    )
    assert event.kind == KIND_REJECTED_HR


def test_classify_screening() -> None:
    event = classify_from_headers(
        message_id="<4@softserve.com>",
        subject="Interview invitation — SoftServe",
        from_header="Anna Recruiter <anna@softserve.com>",
        body_text="Hi Max, can we schedule a call for a screening interview next week?",
    )
    assert event.kind == KIND_SCREENING
    assert event.company == "SoftServe"
    assert event.recruiter.startswith("Anna")


def test_classify_recruiter_reply() -> None:
    event = classify_from_headers(
        message_id="<5@lineup.software>",
        subject="Your LineUp application",
        from_header="HR Team <careers@lineup.software>",
        body_text="Hi Max, thanks for reaching out — we reviewed your CV and have a few questions.",
    )
    assert event.kind == KIND_REPLIED
    assert event.company == "LineUp"


def test_classify_noise_newsletter() -> None:
    event = classify_from_headers(
        message_id="<6@linkedin.com>",
        subject="Jobs you may like",
        from_header="LinkedIn <jobs-noreply@linkedin.com>",
        body_text="Here are new jobs based on your preferences.",
    )
    assert event.kind == KIND_IGNORE


def test_classify_ignores_indeed_job_digest_with_known_company() -> None:
    event = classify_from_headers(
        message_id="<digest@indeed.com>",
        subject="iOS: Senior IOS AI-Enabled Developer у TangoMe і ще 14 нових вакансій",
        from_header="Indeed <jobalerts-noreply@indeed.com>",
        body_text=(
            "Нові вакансії для вас. Senior iOS Engineer у Ciklum та інші "
            "рекомендовані вакансії."
        ),
    )
    assert event.kind == KIND_IGNORE

    subdomain_event = classify_from_headers(
        message_id="<digest@alerts.indeed.com>",
        subject="Senior iOS Engineer та інші нові вакансії",
        from_header="Indeed <jobalerts@alerts.indeed.com>",
        body_text="Рекомендовані вакансії: Senior iOS Engineer у Ciklum.",
    )
    assert subdomain_event.kind == KIND_IGNORE


def test_classify_ignores_uber_two_step_auth() -> None:
    event = classify_from_headers(
        message_id="<33a9a92e-0d33-42fe-9c72-a3647cff8c69@mail.uber.com>",
        subject="Максим, вы включили двухэтапную аутентификацию",
        from_header="Uber <uber@mail.uber.com>",
        body_text=(
            "Максим, вы включили двухэтапную аутентификацию в аккаунте Uber. "
            "Если это были не вы, свяжитесь с нами. "
            "More: https://www.uber.com/us/en/careers/recruiting/"
        ),
    )
    assert event.kind == KIND_IGNORE
    assert event.company == "Uber"


def test_classify_ignores_english_two_factor_security_mail() -> None:
    event = classify_from_headers(
        message_id="<tf@accounts.example.com>",
        subject="Two-factor authentication turned on",
        from_header="Example Security <security@example.com>",
        body_text="You turned on two-factor authentication for your account.",
    )
    assert event.kind == KIND_IGNORE


def test_classify_ignores_osbb_receipt() -> None:
    event = classify_from_headers(
        message_id="<osbb@s2.example>",
        subject="Квитанція на оплату ОСББ «О.ПЧІЛКИ 5»",
        from_header="S2 <noreply@s2.example>",
        body_text="На жаль, термін оплати добігає кінця. Квитанція у вкладенні.",
    )
    assert event.kind == KIND_IGNORE


def test_classify_ignores_pumb_credit_docs() -> None:
    event = classify_from_headers(
        message_id="<fop@pumb.ua>",
        subject="Кредит «всеБІЗНЕС» від ПУМБ - завантаження документів",
        from_header="FOP_CREDIT <fop_credit@pumb.ua>",
        body_text="Завантаження документів для кредиту всеБІЗНЕС.",
    )
    assert event.kind == KIND_IGNORE


def test_classify_ignores_djinni_digest() -> None:
    event = classify_from_headers(
        message_id="<digest@djinni.co>",
        subject="Топ-найми липня",
        from_header="Djinni <digest@djinni.co>",
        body_text="Senior Front-End Developer interview opportunities this month.",
    )
    assert event.kind == KIND_IGNORE


def test_classify_reject_requires_application_signal() -> None:
    event = classify_from_headers(
        message_id="<bank@example.com>",
        subject="Account update",
        from_header="Bank <alerts@example.com>",
        body_text="Unfortunately we cannot proceed with your request at this time.",
    )
    assert event.kind == KIND_IGNORE


def test_classify_reject_with_application_words() -> None:
    event = classify_from_headers(
        message_id="<hr@acme.io>",
        subject="Update on your application",
        from_header="People Team <people@acme.io>",
        body_text="Unfortunately we will not be moving forward with your application.",
    )
    assert event.kind == KIND_REJECTED_HR


def test_classify_ukrainian_reject_with_vidhuk() -> None:
    event = classify_from_headers(
        message_id="<hr@softco.ua>",
        subject="Щодо вашого відгуку",
        from_header="HR SoftCo <hr@softco.ua>",
        body_text="Дякуємо за відгук. На жаль, ми не будемо продовжувати процес.",
    )
    assert event.kind == KIND_REJECTED_HR
    assert event.company


def test_classify_ignores_unfortunately_without_application_words() -> None:
    event = classify_from_headers(
        message_id="<ops@vendor.com>",
        subject="Service notice",
        from_header="Vendor Ops <ops@vendor.com>",
        body_text="На жаль, сервіс тимчасово недоступний. К сожалению, есть задержка.",
    )
    assert event.kind == KIND_IGNORE


def test_classify_ignores_ciklum_ats_otp() -> None:
    event = classify_from_headers(
        message_id="<otp@ciklum.com>",
        subject="Quick step — verify and you’re in",
        from_header="Ciklum Career <no-reply-ciklumcareer@ciklum.com>",
        body_text=(
            "Hi Max, You're almost there! Please use this one-time code to "
            "confirm your identity: 741747 Note: This code will expire in 10 minutes."
        ),
    )
    assert event.kind == KIND_IGNORE


def test_classify_ciklum_apply_ack_stays_ack() -> None:
    event = classify_from_headers(
        message_id="<ack@ciklum.com>",
        subject="Thanks for applying — we’ve got it",
        from_header="Ciklum Career <no-reply-ciklumcareer@ciklum.com>",
        body_text=(
            "Hi Max, We received your application for iOS Engineer - 3982. "
            "If your experience aligns with our current needs, one of our "
            "recruiters will reach out to you soon."
        ),
    )
    assert event.kind == KIND_APPLICATION_ACK
    assert event.company == "Ciklum"

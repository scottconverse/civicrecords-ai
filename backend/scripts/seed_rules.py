"""Seed exemption rules for pilot states: CO, TX, CA, NY, FL."""
import asyncio
import uuid
from app.database import async_session_maker
from app.models.exemption import ExemptionRule, RuleType
from app.models.user import User
from sqlalchemy import select

COLORADO_CORA_RULES = [
    {"category": "CORA - Trade Secrets", "rule_type": "keyword", "definition": "trade secret,proprietary,confidential business,competitive advantage"},
    {"category": "CORA - Personnel Records", "rule_type": "keyword", "definition": "personnel file,employee evaluation,disciplinary action,performance review,termination"},
    {"category": "CORA - Law Enforcement", "rule_type": "keyword", "definition": "investigation,informant,undercover,surveillance,criminal intelligence"},
    {"category": "CORA - Attorney-Client", "rule_type": "keyword", "definition": "attorney-client,legal privilege,work product,litigation hold,legal opinion"},
    {"category": "CORA - Deliberative Process", "rule_type": "keyword", "definition": "draft recommendation,preliminary analysis,internal deliberation,policy discussion"},
    {"category": "CORA - Medical Records", "rule_type": "keyword", "definition": "medical record,patient,diagnosis,treatment plan,HIPAA,health information"},
    {"category": "CORA - Student Records", "rule_type": "keyword", "definition": "student record,FERPA,academic record,enrollment,grade,transcript"},
    {"category": "CORA - Real Estate Appraisal", "rule_type": "keyword", "definition": "appraisal,property valuation,assessed value,market analysis"},
]

# Texas Public Information Act (TPIA) — Tex. Gov't Code Ch. 552
TEXAS_TPIA_RULES = [
    {
        "category": "TPIA - Personnel Records",
        "rule_type": "keyword",
        "definition": "personnel file,employee evaluation,disciplinary action,performance review,termination,home address,social security",
        "description": "Texas TPIA exemption: Personnel Records (Tex. Gov't Code § 552.102)",
    },
    {
        "category": "TPIA - Law Enforcement",
        "rule_type": "keyword",
        "definition": "investigation,informant,undercover,surveillance,criminal intelligence,law enforcement sensitive,offense report",
        "description": "Texas TPIA exemption: Law Enforcement Records (Tex. Gov't Code § 552.108)",
    },
    {
        "category": "TPIA - Litigation Privilege",
        "rule_type": "keyword",
        "definition": "pending litigation,lawsuit,legal claim,settlement negotiation,litigation hold,judicial proceeding",
        "description": "Texas TPIA exemption: Litigation Privilege (Tex. Gov't Code § 552.103)",
    },
    {
        "category": "TPIA - Trade Secrets",
        "rule_type": "keyword",
        "definition": "trade secret,proprietary,confidential business,competitive advantage,commercial information",
        "description": "Texas TPIA exemption: Trade Secrets and Commercial Information (Tex. Gov't Code § 552.110)",
    },
    {
        "category": "TPIA - Student Records",
        "rule_type": "keyword",
        "definition": "student record,FERPA,academic record,enrollment,grade,transcript,educational record",
        "description": "Texas TPIA exemption: Student Records (Tex. Gov't Code § 552.114)",
    },
    {
        "category": "TPIA - Deliberative Process",
        "rule_type": "keyword",
        "definition": "draft recommendation,preliminary analysis,internal deliberation,policy discussion,predecisional,interagency memo",
        "description": "Texas TPIA exemption: Deliberative Process (Tex. Gov't Code § 552.111)",
    },
    {
        "category": "TPIA - Attorney-Client",
        "rule_type": "keyword",
        "definition": "attorney-client,legal privilege,work product,legal opinion,attorney advice,privileged communication",
        "description": "Texas TPIA exemption: Attorney-Client Privilege (Tex. Gov't Code § 552.107)",
    },
    {
        "category": "TPIA - Personal Privacy",
        "rule_type": "keyword",
        "definition": "personal family information,highly intimate,private information,unwarranted invasion of privacy",
        "description": "Texas TPIA exemption: Personal Privacy (Tex. Gov't Code § 552.101)",
    },
]

# California Public Records Act (CPRA) — Cal. Gov't Code § 7920 et seq.
CALIFORNIA_CPRA_RULES = [
    {
        "category": "CPRA - Personnel Records",
        "rule_type": "keyword",
        "definition": "personnel file,employee evaluation,disciplinary action,performance review,termination,personnel record",
        "description": "California CPRA exemption: Personnel Records (Cal. Gov't Code § 7928.200)",
    },
    {
        "category": "CPRA - Law Enforcement Investigation",
        "rule_type": "keyword",
        "definition": "investigation,informant,undercover,surveillance,criminal intelligence,active investigation,peace officer",
        "description": "California CPRA exemption: Law Enforcement Investigation (Cal. Gov't Code § 7923.600)",
    },
    {
        "category": "CPRA - Attorney-Client",
        "rule_type": "keyword",
        "definition": "attorney-client,legal privilege,work product,litigation hold,legal opinion,attorney advice",
        "description": "California CPRA exemption: Attorney-Client Privilege (Cal. Evid. Code § 954; Cal. Gov't Code § 7927.705)",
    },
    {
        "category": "CPRA - Trade Secrets",
        "rule_type": "keyword",
        "definition": "trade secret,proprietary,confidential business,competitive advantage,commercial information",
        "description": "California CPRA exemption: Trade Secrets (Cal. Gov't Code § 7927.705)",
    },
    {
        "category": "CPRA - Medical and Mental Health",
        "rule_type": "keyword",
        "definition": "medical record,patient,diagnosis,treatment plan,HIPAA,mental health,psychiatric,health information",
        "description": "California CPRA exemption: Medical/Mental Health Records (Cal. Gov't Code § 7928.000)",
    },
    {
        "category": "CPRA - Deliberative Process",
        "rule_type": "keyword",
        "definition": "draft recommendation,preliminary analysis,internal deliberation,policy discussion,predecisional,staff analysis",
        "description": "California CPRA exemption: Deliberative Process / Pre-decisional (Cal. Gov't Code § 7927.705)",
    },
    {
        "category": "CPRA - Personal Information",
        "rule_type": "keyword",
        "definition": "home address,telephone number,personal information,unwarranted invasion of privacy,financial information",
        "description": "California CPRA exemption: Personal Information / Privacy (Cal. Gov't Code § 7922.000)",
    },
]

# New York Freedom of Information Law (FOIL) — N.Y. Pub. Off. Law § 84 et seq.
NEW_YORK_FOIL_RULES = [
    {
        "category": "FOIL - Law Enforcement Investigation",
        "rule_type": "keyword",
        "definition": "investigation,informant,undercover,surveillance,criminal intelligence,law enforcement record,active investigation",
        "description": "New York FOIL exemption: Law Enforcement Investigation (N.Y. Pub. Off. Law § 87(2)(e))",
    },
    {
        "category": "FOIL - Trade Secrets",
        "rule_type": "keyword",
        "definition": "trade secret,proprietary,confidential business,competitive advantage,commercial information,business secrets",
        "description": "New York FOIL exemption: Trade Secrets (N.Y. Pub. Off. Law § 87(2)(d))",
    },
    {
        "category": "FOIL - Personnel Records",
        "rule_type": "keyword",
        "definition": "personnel file,employee evaluation,disciplinary action,performance review,termination,employment record",
        "description": "New York FOIL exemption: Personnel Records (N.Y. Pub. Off. Law § 87(2)(b); Civil Service Law § 50-a)",
    },
    {
        "category": "FOIL - Attorney-Client",
        "rule_type": "keyword",
        "definition": "attorney-client,legal privilege,work product,legal opinion,attorney advice,privileged communication",
        "description": "New York FOIL exemption: Attorney-Client Privilege (N.Y. Pub. Off. Law § 87(2)(a); CPLR § 4503)",
    },
    {
        "category": "FOIL - Medical Records",
        "rule_type": "keyword",
        "definition": "medical record,patient,diagnosis,treatment plan,HIPAA,health information,medical history",
        "description": "New York FOIL exemption: Medical Records (N.Y. Pub. Off. Law § 87(2)(b))",
    },
    {
        "category": "FOIL - Inter-Agency Communications",
        "rule_type": "keyword",
        "definition": "inter-agency,intra-agency,internal memo,predecisional,deliberative,policy discussion,draft recommendation",
        "description": "New York FOIL exemption: Inter/Intra-Agency Communications (N.Y. Pub. Off. Law § 87(2)(g))",
    },
    {
        "category": "FOIL - Personal Privacy",
        "rule_type": "keyword",
        "definition": "unwarranted invasion of privacy,personal information,home address,financial record,private information",
        "description": "New York FOIL exemption: Personal Privacy (N.Y. Pub. Off. Law § 87(2)(b))",
    },
]

# Florida Sunshine Law / Public Records Act — Fla. Stat. Ch. 119
FLORIDA_PRA_RULES = [
    {
        "category": "FL PRA - Law Enforcement Active Investigation",
        "rule_type": "keyword",
        "definition": "active investigation,criminal investigation,informant,undercover,surveillance,law enforcement sensitive,criminal intelligence",
        "description": "Florida Public Records Act exemption: Active Criminal Investigation (Fla. Stat. § 119.071(2)(c))",
    },
    {
        "category": "FL PRA - Trade Secrets",
        "rule_type": "keyword",
        "definition": "trade secret,proprietary,confidential business,competitive advantage,commercial information,business secrets",
        "description": "Florida Public Records Act exemption: Trade Secrets (Fla. Stat. § 119.071(1)(f))",
    },
    {
        "category": "FL PRA - Personnel Records",
        "rule_type": "keyword",
        "definition": "personnel file,employee evaluation,disciplinary action,performance review,termination,employment record",
        "description": "Florida Public Records Act exemption: Personnel Records (Fla. Stat. § 119.071(4)(d))",
    },
    {
        "category": "FL PRA - Social Security Numbers",
        "rule_type": "keyword",
        "definition": "social security number,SSN,tax identification,federal identification number",
        "description": "Florida Public Records Act exemption: Social Security Numbers (Fla. Stat. § 119.071(5)(a))",
    },
    {
        "category": "FL PRA - Medical Records",
        "rule_type": "keyword",
        "definition": "medical record,patient,diagnosis,treatment plan,HIPAA,health information,medical history,mental health",
        "description": "Florida Public Records Act exemption: Medical Records (Fla. Stat. § 119.071(4)(a))",
    },
    {
        "category": "FL PRA - Attorney Work Product",
        "rule_type": "keyword",
        "definition": "attorney work product,legal privilege,attorney-client,litigation hold,legal opinion,attorney advice,work product doctrine",
        "description": "Florida Public Records Act exemption: Attorney Work Product / Client Privilege (Fla. Stat. § 119.071(1)(d))",
    },
    {
        "category": "FL PRA - Home Addresses and Personal Safety",
        "rule_type": "keyword",
        "definition": "home address,personal address,residential address,location information,address confidentiality",
        "description": "Florida Public Records Act exemption: Home Addresses / Personal Safety (Fla. Stat. § 119.071(4)(d)2)",
    },
]

# Registry mapping state code -> (rules list, law name, display name)
STATE_RULES_REGISTRY = [
    ("CO", COLORADO_CORA_RULES, "CORA", "Colorado"),
    ("TX", TEXAS_TPIA_RULES, "TPIA", "Texas"),
    ("CA", CALIFORNIA_CPRA_RULES, "CPRA", "California"),
    ("NY", NEW_YORK_FOIL_RULES, "FOIL", "New York"),
    ("FL", FLORIDA_PRA_RULES, "FL PRA", "Florida"),
]


async def seed_state(session, user, state_code: str, rules: list, law_name: str, state_name: str):
    created = 0
    skipped = 0
    for rule_data in rules:
        existing = await session.execute(
            select(ExemptionRule).where(
                ExemptionRule.category == rule_data["category"],
                ExemptionRule.state_code == state_code,
            )
        )
        if existing.scalar_one_or_none():
            print(f"  Skipped (exists): {rule_data['category']}")
            skipped += 1
            continue

        description = rule_data.get(
            "description",
            f"{state_name} {law_name} exemption: {rule_data['category'].replace(f'{law_name} - ', '')}",
        )
        rule = ExemptionRule(
            state_code=state_code,
            category=rule_data["category"],
            rule_type=RuleType.KEYWORD,
            rule_definition=rule_data["definition"],
            description=description,
            enabled=True,
            created_by=user.id,
        )
        session.add(rule)
        print(f"  Created: {rule_data['category']}")
        created += 1

    return created, skipped


async def seed():
    async with async_session_maker() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No users in database. Run the application first.")
            return

        total_created = 0
        for state_code, rules, law_name, state_name in STATE_RULES_REGISTRY:
            print(f"\n--- {state_name} ({state_code}) {law_name} ---")
            created, skipped = await seed_state(session, user, state_code, rules, law_name, state_name)
            total_created += created
            print(f"  {created} created, {skipped} skipped")

        await session.commit()
        print(f"\nTotal rules seeded: {total_created}")


if __name__ == "__main__":
    asyncio.run(seed())

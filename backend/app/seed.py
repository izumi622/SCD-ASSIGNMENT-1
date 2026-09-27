import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.db import ComplaintDB
from app.models.enums import Category, Priority, Status

logger = logging.getLogger("civicpulse.seed")

# >= 30 realistic complaints in Urdu-influenced English across categories
SEED_COMPLAINTS = [
    {
        "text": "Main water supply pipe burst near Street 12 since fajr, paani entering ground floors and basements. Urgent repair required!",
        "location": "Sector G-9/2, Street 12, Islamabad",
        "category": Category.water.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-300-1122334",
        "ai_summary": "Urgent: Burst water main flooding ground floor residences since fajr",
        "triaged_by": "rules",
    },
    {
        "text": "Bijli transformer sparking violently after barish near corner shop, live wires hanging down dangerously.",
        "location": "Main Bazar, Dhoke Khabba, Rawalpindi",
        "category": Category.electricity.value,
        "priority": Priority.high.value,
        "status": Status.in_progress.value,
        "reporter_contact": "+92-321-5544332",
        "ai_summary": "Emergency: Sparking transformer and hazardous fallen wires after rain",
        "triaged_by": "llm:groq",
    },
    {
        "text": "Kachra kundi overflowing near community park for 4 days. Bad smell and stray dogs creating nuisance.",
        "location": "Block C, Satellite Town, Gujranwala",
        "category": Category.sanitation.value,
        "priority": Priority.normal.value,
        "status": Status.open.value,
        "reporter_contact": None,
        "ai_summary": "Sanitation issue: Overflowing garbage dumpster near public park",
        "triaged_by": "rules",
    },
    {
        "text": "Huge pothole (bara khadda) on main double road causing bike slips and traffic jam every evening.",
        "location": "Peshawar Road near Chairing Cross, Rawalpindi",
        "category": Category.roads.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-333-9876543",
        "ai_summary": "Road hazard: Severe pothole on double road causing motorcycle accidents",
        "triaged_by": "rules",
    },
    {
        "text": "Streetlight pole fused and flickering for past two weeks, complete andhera at night outside school.",
        "location": "Lane 4, Gulshan-e-Iqbal Block 13-D, Karachi",
        "category": Category.streetlights.value,
        "priority": Priority.normal.value,
        "status": Status.resolved.value,
        "reporter_contact": "resident.association@gmail.com",
        "ai_summary": "Broken streetlight outside school creating nighttime darkness",
        "triaged_by": "rules",
    },
    {
        "text": "Sewer line chocked completely, ganda paani spilling over road and entering shops near Jamia Masjid.",
        "location": "Circular Road near Bhati Gate, Lahore",
        "category": Category.water.value,
        "priority": Priority.high.value,
        "status": Status.in_progress.value,
        "reporter_contact": "+92-345-6677889",
        "ai_summary": "Sewerage overflow spilling dirty water into market shops",
        "triaged_by": "rules",
    },
    {
        "text": "Frequent load shedding and severe voltage fluctuation, several home appliances got burnt today.",
        "location": "Allama Iqbal Town, Ravi Block, Lahore",
        "category": Category.electricity.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "iqbal_resident@yahoo.com",
        "ai_summary": "High voltage fluctuations causing appliance damage across locality",
        "triaged_by": "llm:groq",
    },
    {
        "text": "Dead animal lying beside primary school boundary wall. Flies and intolerable badboo.",
        "location": "Sector F-11/3, Street 48, Islamabad",
        "category": Category.sanitation.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": None,
        "ai_summary": "Sanitation emergency: Dead animal carcass adjacent to school boundary",
        "triaged_by": "rules",
    },
    {
        "text": "Speed breaker requested in front of Government Girls College. Vehicles speeding recklessly.",
        "location": "College Road, Civil Lines, Faisalabad",
        "category": Category.roads.value,
        "priority": Priority.low.value,
        "status": Status.open.value,
        "reporter_contact": "+92-301-4455667",
        "ai_summary": "Request for speed breaker installation near girls college",
        "triaged_by": "rules",
    },
    {
        "text": "Underground drinking water line contaminated with sewage gutter water. Muddy tap water with bad smell.",
        "location": "Mohallah Waris Pura, Faisalabad",
        "category": Category.water.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-312-3322114",
        "ai_summary": "Critical: Drinking water contamination with sewage infiltration",
        "triaged_by": "rules",
    },
    {
        "text": "Electric meter box open without cover on footpath, children play nearby, risk of shock.",
        "location": "Model Town Link Road, Block M, Lahore",
        "category": Category.electricity.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-322-8877665",
        "ai_summary": "Electrical hazard: Uncovered live meter box accessible to children",
        "triaged_by": "rules",
    },
    {
        "text": "Construction malba and heavy debris left blocking half of the road by private builder.",
        "location": "DHA Phase 5, Sector C, Lahore",
        "category": Category.roads.value,
        "priority": Priority.normal.value,
        "status": Status.open.value,
        "reporter_contact": None,
        "ai_summary": "Road obstruction: Construction debris blocking active traffic lane",
        "triaged_by": "rules",
    },
    {
        "text": "Five consecutive street lights not turning on between Pole 14 and 19 on main boulevard.",
        "location": "Korang Road, Sector I-9/4, Islamabad",
        "category": Category.streetlights.value,
        "priority": Priority.normal.value,
        "status": Status.in_progress.value,
        "reporter_contact": "transport.union@org.pk",
        "ai_summary": "Series of consecutive streetlight failures on arterial boulevard",
        "triaged_by": "rules",
    },
    {
        "text": "No water supply since three days in entire street. Tube well operator says pump motor burned.",
        "location": "Street 9, Muslim Town, Rawalpindi",
        "category": Category.water.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-300-5566778",
        "ai_summary": "Total water outage across street due to burned tube well pump motor",
        "triaged_by": "rules",
    },
    {
        "text": "Sanitation sweepers haven't visited our gali for a whole week. Litter accumulating everywhere.",
        "location": "Gali 7, Rehman Pura, Lahore",
        "category": Category.sanitation.value,
        "priority": Priority.normal.value,
        "status": Status.open.value,
        "reporter_contact": "+92-334-1122990",
        "ai_summary": "Absence of municipal sweepers for 7 days causing trash buildup",
        "triaged_by": "rules",
    },
    {
        "text": "Open manhole cover missing on footpath right in front of baker's shop. Major accident risk.",
        "location": "Tariq Road near Liberty Market, Karachi",
        "category": Category.roads.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-321-8899001",
        "ai_summary": "Emergency: Missing manhole cover on busy pedestrian sidewalk",
        "triaged_by": "rules",
    },
    {
        "text": "Request to repaint zebra crossings and lane markers near government hospital entrance.",
        "location": "DHQ Hospital Road, Sargodha",
        "category": Category.roads.value,
        "priority": Priority.low.value,
        "status": Status.resolved.value,
        "reporter_contact": "hospital.admin@punjab.gov.pk",
        "ai_summary": "Routine maintenance: Repainting faded pedestrian zebra crossings",
        "triaged_by": "rules",
    },
    {
        "text": "Streetlight pole tilted at 45 degree angle after delivery truck hit it in the morning.",
        "location": "Auto Market, Badami Bagh, Lahore",
        "category": Category.streetlights.value,
        "priority": Priority.high.value,
        "status": Status.in_progress.value,
        "reporter_contact": "+92-302-3344556",
        "ai_summary": "Hazard: Collapsing tilted streetlight pole after vehicular collision",
        "triaged_by": "rules",
    },
    {
        "text": "Water tanker mafia selling government subsidized water at exorbitant black market rates.",
        "location": "Clifton Block 2, Karachi",
        "category": Category.other.value,
        "priority": Priority.normal.value,
        "status": Status.rejected.value,
        "reporter_contact": "clifton.citizen@hotmail.com",
        "ai_summary": "Complaint regarding commercial water tanker price gouging",
        "triaged_by": "rules",
    },
    {
        "text": "Stormwater nullah choked with plastic waste, rainwater about to enter houses if nullah isn't desilted.",
        "location": "Near Leh Nullah bridge, Dhoke Naju, Rawalpindi",
        "category": Category.water.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-331-5544778",
        "ai_summary": "High flood hazard: Choked stormwater drain threatening residential inundation",
        "triaged_by": "rules",
    },
    {
        "text": "Public park benches vandalized and lights broken by miscreants during late hours.",
        "location": "Jinnah Park, Sector F-8/2, Islamabad",
        "category": Category.other.value,
        "priority": Priority.low.value,
        "status": Status.open.value,
        "reporter_contact": None,
        "ai_summary": "Vandalism of park infrastructure and broken recreational fixtures",
        "triaged_by": "rules",
    },
    {
        "text": "Heavy commercial generator placed illegally on public road making unbearable noise all night.",
        "location": "Saddar Bazaar, Saddar, Rawalpindi",
        "category": Category.other.value,
        "priority": Priority.low.value,
        "status": Status.open.value,
        "reporter_contact": "+92-313-9988776",
        "ai_summary": "Noise nuisance: Commercial generator operating on public roadway",
        "triaged_by": "rules",
    },
    {
        "text": "Hospital medical waste disposed directly into public garbage bin behind laboratory.",
        "location": "Khyber Teaching Hospital Road, Peshawar",
        "category": Category.sanitation.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "dr.khan@kth.edu.pk",
        "ai_summary": "Severe biohazard: Hazardous medical waste dumped in public municipal bin",
        "triaged_by": "rules",
    },
    {
        "text": "Tree branches heavily entangled in 11kV high tension electricity wires, smoking and arcing.",
        "location": "Mall Road near Governor House, Lahore",
        "category": Category.electricity.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-300-4433221",
        "ai_summary": "Immediate danger: Tree branches touching high tension electric wires",
        "triaged_by": "rules",
    },
    {
        "text": "Low water pressure in municipal line, barely a trickle comes even after turning on motor.",
        "location": "Hayatabad Phase 4, Peshawar",
        "category": Category.water.value,
        "priority": Priority.normal.value,
        "status": Status.open.value,
        "reporter_contact": "+92-343-7788990",
        "ai_summary": "Low water pressure preventing domestic supply in Phase 4",
        "triaged_by": "rules",
    },
    {
        "text": "Streetlight pole wiring shorted, entire metallic pole is giving electric shock when touched.",
        "location": "Bara Market, Raja Bazaar, Rawalpindi",
        "category": Category.electricity.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-332-1144778",
        "ai_summary": "Critical electrocution risk: Live current passing into metal streetlight pole",
        "triaged_by": "rules",
    },
    {
        "text": "Unfinished road trench dug up for gas line left open without safety cones or warning tape.",
        "location": "Gulberg III, Near Ghalib Market, Lahore",
        "category": Category.roads.value,
        "priority": Priority.high.value,
        "status": Status.open.value,
        "reporter_contact": "+92-300-8844221",
        "ai_summary": "Road excavation left without safety markings or barricades",
        "triaged_by": "rules",
    },
    {
        "text": "Stagnant rainwater accumulation creating dengue mosquito breeding pool on vacant plot.",
        "location": "Sector I-10/2, Islamabad",
        "category": Category.sanitation.value,
        "priority": Priority.normal.value,
        "status": Status.open.value,
        "reporter_contact": "resident_i10@gmail.com",
        "ai_summary": "Sanitation/health risk: Stagnant water pool posing dengue hazard",
        "triaged_by": "rules",
    },
    {
        "text": "Solar streetlight battery stolen from pole during night time, light no longer operational.",
        "location": "Korang Town, Expressway, Islamabad",
        "category": Category.streetlights.value,
        "priority": Priority.low.value,
        "status": Status.open.value,
        "reporter_contact": None,
        "ai_summary": "Theft of solar streetlight battery rendering unit non-functional",
        "triaged_by": "rules",
    },
    {
        "text": "Illegal speed breaker constructed of rough concrete rocks damaged car suspension.",
        "location": "Street 14, Sector G-13/1, Islamabad",
        "category": Category.roads.value,
        "priority": Priority.low.value,
        "status": Status.resolved.value,
        "reporter_contact": "+92-315-9988112",
        "ai_summary": "Unauthorized rough speed breaker causing vehicular damage",
        "triaged_by": "rules",
    },
    {
        "text": "Commercial butchers throwing animal entrails and bones directly into open roadside gutter.",
        "location": "Meat Market, Liaquatabad No. 4, Karachi",
        "category": Category.sanitation.value,
        "priority": Priority.high.value,
        "status": Status.in_progress.value,
        "reporter_contact": "+92-322-9900112",
        "ai_summary": "Severe contamination: Butcher shop waste clogging open stormwater gutters",
        "triaged_by": "rules",
    },
    {
        "text": "Illegal cattle pen (bhains kotha) operating inside residential street with loud noise and dung.",
        "location": "Kot Lakhpat, Lahore",
        "category": Category.other.value,
        "priority": Priority.low.value,
        "status": Status.open.value,
        "reporter_contact": "+92-344-5566112",
        "ai_summary": "Unauthorized livestock operation in residential zone",
        "triaged_by": "rules",
    },
]


async def _seed_with_session(session: AsyncSession) -> int:
    inserted_count = 0
    for item in SEED_COMPLAINTS:
        seed_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{item['location']}:{item['text']}")
        stmt = select(ComplaintDB).where(
            (ComplaintDB.id == seed_uuid)
            | (
                (ComplaintDB.text == item["text"])
                & (ComplaintDB.location == item["location"])
            )
        )
        result = await session.execute(stmt)
        existing = result.scalars().first()

        if existing is None:
            complaint = ComplaintDB(
                id=seed_uuid,
                text=item["text"],
                location=item["location"],
                category=item["category"],
                priority=item["priority"],
                status=item["status"],
                reporter_contact=item["reporter_contact"],
                ai_summary=item["ai_summary"],
                triaged_by=item["triaged_by"],
                triage_latency_ms=120,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(complaint)
            inserted_count += 1

    if inserted_count > 0:
        await session.commit()
        print(f"Successfully inserted {inserted_count} new seed complaint records.")
    else:
        print("Database already contains all seed records. 0 rows inserted (idempotency preserved).")

    return inserted_count


async def seed_database(session: Optional[AsyncSession] = None) -> int:
    """Idempotently seeds database with >= 30 realistic complaints.
    Running this multiple times will never duplicate rows.
    """
    if session is not None:
        return await _seed_with_session(session)
    async with AsyncSessionLocal() as sess:
        return await _seed_with_session(sess)


if __name__ == "__main__":
    asyncio.run(seed_database())

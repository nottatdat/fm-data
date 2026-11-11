# E14 — Market value

**Method:** searched for a value inside each player's on-screen range (e.g. £26M–£39M) at
fixed offsets from every anchor (uid occurrences, person, header, ratings record,
contract), raw and scaled (×1000 u16/u32, ×10, ×100, float, euro rate).

**Result:** no offset holds an in-range value for more than 3 of 8 players; the partial
hits are other ids or byte noise.

**Correction (follow-up):** FM does store a value. mavarobli/FMSuperScout (FM26, memory)
reads a u32 "guide value" in GBP at player object +0x234 and the asking price at +0x238
(`core/Fields.cs`, `core/Dumper.cs:747`). Checked in the save: the memory offset shifted
like the attribute block (+0xB8) does not hold it, and no offset within ±3000 bytes of the
person record, header, ratings record or contract holds a number in a consistent ratio to
the on-screen range midpoint for all 8 players. So the value is serialised away from the
records decoded so far (or in a form not tried); finding it needs a link from its record
to the player, which is open.

**Verdict:** FAIL (time box), not "impossible". `value` stays blank; the requirement was removed from the
change after this result.

## Deeper search (option 1)

- The person record has an index 17 bytes before it (e.g. 160936) that other records use
  to point at the person (~90 references each). Values in range at a fixed offset from
  those references: up to 7/8 players, but at many unrelated offsets: noise, because ~90
  references × wide ranges make random in-range bytes likely.
- Whole-save scan for Omari (narrowest range, £11.5M–£12.5M): 953,591 unaligned u32
  positions hold an in-range number, so brute force cannot single out the value without
  knowing its record type. Next lead depends on documentation of that record (research).

## Found: stored base valuation (research lead)

fm-open-scout (MIT, FORMAT.md §4.2, `valuation_unverified`) reads a u32 £ right after the
54 attributes of the ratings record (our `RAT_VALUE = RAT_LEN`); 0xFFFFFFFF = none,
300,000,000 = cap. Against the 8 screenshots: Guéla Doué £1.31M (FM "£1.3M"), Désiré
Doué £38.6M (in "£26–39M"), Omari £11.2M ("£11.5–12.5M"), Mandanda £0.27M ("£0.28–0.43M"),
but Kalimuendo £20.5M ("£30–34M"), Mamardashvili £37.5M ("£49–69M"), Lambourde £13.2M
("£27–35M"). Right magnitude and order, not FM's displayed value: FM adjusts it when shown
(potential, form, interest). Football Save Scout fits FM's figure with a regression instead.

**Verdict (revised):** exported as `value`, **unverified** (user decision).

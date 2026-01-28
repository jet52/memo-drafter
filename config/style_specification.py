"""Style specification for ND Supreme Court bench memos."""

STYLE_SPEC = """
## BENCH MEMO STYLE SPECIFICATION

### Structure
1. **Header**: Case number, case name, date of oral argument, author
2. **Quick Reference**: 4-8 key documents with record citations
3. **Opening Paragraph [¶1]**: Summary of case, issues, and recommendation
4. **BACKGROUND**: Factual and procedural history with record citations
5. **Analysis Sections**: One per issue, each with:
   - Standard of review
   - Appellant's arguments
   - Appellee's arguments
   - Applicable precedent
   - Analysis and recommendation
6. **CONCLUSION**: Restate recommendation

### Formatting Rules
- Every paragraph is numbered: [¶1], [¶2], etc.
- Record citations use format: (R##), (R##:page), (R##:page:¶para)
- ND case citations: YYYY ND ###
- Reporter citations: ### N.W.2d ###
- Statute citations: N.D.C.C. § ##-##-##
- Rule citations: N.D.R.App.P. ##, N.D.R.Civ.P. ##, N.D.R.Ev. ##
- Use ¶ for paragraph references within cases
- Headings in ALL CAPS for major sections (BACKGROUND, CONCLUSION)
- Issue headings use Roman numerals (I., II., III.)

### Tone
- Neutral, analytical tone
- Present both sides fairly before offering assessment
- Recommendation should be clearly stated but appropriately hedged
- Use "the Court" when referring to the ND Supreme Court
- Use "the district court" for lower court
"""

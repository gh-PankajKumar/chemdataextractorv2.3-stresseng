"""
This ChemDataExtractor module provides tools for extracting mechanical properties from scientific text and tables.

It focuses on the following key properties:

- Yield Strength
- Ultimate Tensile Strength
- Fracture Strength
- Young's Modulus
- Ductility

This module incorporates the modifications made in the ChemDataExtractorStressEng [1] library, and integrates them into the ChemDataExtractor version 2.3 framework.

It defines custom models and parsers tailored to identify these specific properties in both text and tabular data.

Key Components:

- Chemical Named Entity Recognition (CNER): Integrates dictionary-based methods into CNER that are focused on materials common in engineering studies.
- Text Models: Extract mechanical properties from text.
- Table Models: Equivalent to text models but target tabulated data.

The models and parsers are designed to handle a wide range of variations in how these properties might be expressed in scientific literature.


References:
[1] Kumar, P., Kabra, S. & Cole, J.M. Auto-generating databases of Yield Strength and Grain Size using ChemDataExtractor. Sci Data 9, 292 (2022). https://doi.org/10.1038/s41597-022-01301-w
"""
from lxml.etree import strip_tags
import copy

from chemdataextractor.model.units import RatioModel, StressModel
from chemdataextractor.model.contextual_range import SectionRange, SentenceRange, ParagraphRange
from chemdataextractor.model import BaseModel, Compound, ModelType, StringType, ModelList, ListType
from chemdataextractor.parse.actions import join, flatten, merge
from chemdataextractor.parse.auto import AutoSentenceParser, AutoTableParser
from chemdataextractor.parse.quantity import magnitudes_dict, value_element, extract_value
from chemdataextractor.parse.cem_factory import _CemFactory
from chemdataextractor.parse.auto_dependency import AutoDependencyParser
from chemdataextractor.parse.elements import R, I, W, Optional, Not, Every, Group, SkipTo

# Chemical Named Entity Recognition (CNER) setup
joining_characters = R(r'^\@|\/|:|[-–‐‑‒–—―]$')
cem_factory = _CemFactory(joining_characters=joining_characters)
eng_trade_names = (W("AISI") + W("1020")
    ^ W("AISI") + W("1045")
    ^ W("AISI") + W("1060")
    ^ W("AISI") + W("201")
    ^ W("AISI") + W("202")
    ^ W("AISI") + W("301")
    ^ W("AISI") + W("302")
    ^ W("AISI") + W("304")
    ^ W("AISI") + W("304L")
    ^ W("AISI") + W("316")
    ^ W("AISI") + W("316L")
    ^ W("AISI") + W("405")
    ^ W("AISI") + W("410")
    ^ W("AISI") + W("430")
    ^ W("AISI") + W("446")
    ^ W("15-5PH")
    ^ W("15") + joining_characters + W("5PH")
    ^ W("17-4PH")
    ^ W("17") + joining_characters + W("4PH")
    ^ W("17-7PH")
    ^ W("17") + joining_characters + W("7PH")
    ^ W("A-286")
    ^ W("A") + joining_characters + I("286")
    ^ W("Alloy") + W("2205")
    ^ W("Ferrallium") + W("255")
    ^ I("ASTM") + I("A159")
    ^ I("ASTM") + I("A536")
    ^ I("Al") + I("2014")
    ^ I("Al") + I("2024")
    ^ I("Al") + I("5052")
    ^ I("Al") + I("5083")
    ^ I("Al") + I("6061")
    ^ I("Al") + I("7075")
    ^ I("Hastelloy")
    ^ I("C-276")
    ^ I("C") + joining_characters + I("276")
    ^ I("Inconel") + I("625")
    ^ I("Inconel") + I("686")
    ^ I("Inconel") + I("718")
    ^ I("Inconel") + I("725")
    ^ I("Monel") + I("400")
    ^ I("Monel") + I("K-500")
    ^ I("Monel") + I("K") + joining_characters + I("500")
    ^ I("70/30") + I("Copper-Nickel")
    ^ I("70") + "/" + I("30") + I("Copper") + joining_characters + I("Nickel")
    ^ I("90/10") + I("Copper-Nickel")
    ^ I("90") + "/" + I("10") + I("Copper") + joining_characters + I("Nickel")
    ^ I("Aluminum") + I("Bronze")
    ^ I("Beryllium") + I("Copper")
    ^ I("Nickel") + I("Aluminum")
    ^ I("Bronze") + I("632")
    ^ I("Steel") + (I("316") | I("304"))
    ^ I("316L") + I("austenitic") + Optional(I("stainless")) + I("steel")
    ^ I("AJ62")
    ^ R(r"AZ31")
    ^ I("AZ31B")
    ^ I("AZ31B-H24")
    ^ I("AZ31B") + joining_characters + I("H24")
    ^ I("AZ31-O")
    ^ I("AZ31") + joining_characters + I("O")
    ^ I("AZ91")
    ^ I("AZ91D")
    ^ I("AZ31C")
    ^ I("IN200")
    ^ I("Rene88DT")
    ^ Optional(I("FG") | I("CG")) + I("RR1000")
    ^ I("Udimet") + I("720")
    ^ I("Udimet720")
    ^ I("Waspaloy")
    ^ I("C263")
    ^ I("IN100")
    ^ I("NC") + I("-") + I("silver")
    ^ I("NC") + I("-") + I("aluminium")
    ^ I("AZ61")
    ^ I("Nimonic")
    ^ I("NiTinol")
    ^ I("P91") + I("Steel")
    ^ I("EUROFER") + I("Steel")
    ^ I("TZF6")
    ^ I("TZ74")
    ^ I("TZF8")
    ^ I("CP-Ti")
    ^ I("CP") + joining_characters + I("Ti")
    ^ I("AA7075-T651")
    ^ I("AA7075") + joining_characters + I("T651")
    ^ I("Q890D") + I("steel")
    ^ I("ZK60")
    ^ I("DP600")
    ^ I("DP") + I("600")
    ^ I("DP800")
    ^ I("DP") + I("800")
    ^ I("Ti5111")
    ^ I("Ti-5111")
    ^ I("Ti") + I("-") + I("5111")
    ^ I("GS16Mn5")
    ^ I("RZ5")
    ^ W("CADZ")
    ^ I("GW123")
)

cem = cem_factory.cem
other_solvent = cem_factory.other_solvent

chem_name = Every([(cem | eng_trade_names),Not(I('Hydrogen')), Not(W('H2')), Not(W('H+')), Not(W('STH')),
                  Not(I('Methanol')), Not(I('Glycerol')), Not(I('Ethanol')), Not(I('Oxygen')), Not(I('Water')), Not(W('O2')), Not(I('Acetaldehyde')),
                  Not(I('Xe')), Not(W('H2O2')),
    Not(I('Ni')),
    Not(I('YS')),
    Not(I('Mn')),
    Not(I('P')),
    Not(I('SSS'))])



class SimpleCompoundParser(AutoSentenceParser):
    root = Group(chem_name)


Compound.parsers = [SimpleCompoundParser()]

# --- Mechanical Property Specifiers ---

yield_strength_specifier = (
    I("σy")
        ^ R("[Yy]ield") + R("[Ss]trength(s?)")
        ^ I("ys")
        ^ R("[Yy]ield") + R("[Ss]tress(es?)")
        ^ I("TYS")
        ^ I("σTYS")
        ^ I("σYS")
        ).add_action(join)

tensile_strength_specifier = (
    R(r"[Uu]ltimate") + R(r"[Tt]ensile") + R(r"[Ss]trength(s?)")
        ^ I("UTS")
        ^ R(r"[Tt]ensile") + R("[Ss]trength(s?)")
        ^ I("σult")
        ^ I("σuts")
        ^ I("Ftu")
        ^ I("σts")
        ^ W("TS")
).add_action(join)

youngs_modulus_specifier = (
        (R(r"[Yy]oung")+R(r"'s")).add_action(merge)+R(r"[Mm]odulus")
        ^ W("E")
        ).add_action(join)

fracture_strength_specifier = (
        R(r"[Ff]racture") + R(r"[Ss]trength(s?)")
        ^ I("σF")
        ).add_action(join)

ductility_specifier = (
    I("Ductility")
    ^ W(r"\%AR")
    ^ W(r"\%EL")
)

# --- Models for Text and Table Parsing ---

merging_range = 4 * ParagraphRange()
class YieldStrength(StressModel):
    """ Model for yield strength text parsing"""
    compound = ModelType(Compound, contextual=True, required=True, contextual_range=merging_range)
    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=yield_strength_specifier, required=True)
    parsers = [AutoDependencyParser(primary_keypath="specifier")]

class UltimateTensileStrength(StressModel):
    """ Model for ultimate tensile strength text parsing"""
    compound = ModelType(Compound, contextual=True, required=True,contextual_range=merging_range)
    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=tensile_strength_specifier, required=True)
    parsers = [AutoDependencyParser(primary_keypath="specifier")]

class FractureStrength(StressModel):
    """ Model for fracture strength text parsing"""
    compound = ModelType(Compound, contextual=True, required=True,contextual_range=merging_range)
    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=fracture_strength_specifier, required=True)
    parsers = [AutoDependencyParser(primary_keypath="specifier")]

class YoungsModulus(StressModel):
    """ Model for young's modulus text parsing"""
    compound = ModelType(Compound, contextual=True, required=True,contextual_range=merging_range)
    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=youngs_modulus_specifier, required=True)
    parsers = [AutoDependencyParser(primary_keypath="specifier")]

class Ductility(RatioModel):
    """ Model for ductility text parsing"""
    compound = ModelType(Compound, contextual=True, required=True,contextual_range=merging_range)
    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=ductility_specifier, required=True)
    parsers = [AutoDependencyParser(primary_keypath="specifier")]


class TableYieldStrength(StressModel):
    """ Model for yield strength table parsing"""

    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=yield_strength_specifier, required=True)
    compound = ModelType(Compound, contextual=True, required=True)
    parsers = [AutoTableParser()]

class TableYoungsModulus(StressModel):
    """ Model for Young's Modulus table parsing"""

    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=youngs_modulus_specifier, required=True)
    compound = ModelType(Compound, contextual=True, required=True)
    parsers = [AutoTableParser()]

class TableUltimateTensileStrength(StressModel):
    """ Model for Ultimate Tensile Strength table parsing"""

    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=tensile_strength_specifier, required=True)
    compound = ModelType(Compound, contextual=True, required=True)
    parsers = [AutoTableParser()]

class TableFractureStrength(StressModel):
    """ Model for Fracture Strength table parsing"""

    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    specifier = StringType(parse_expression=fracture_strength_specifier, required=True)
    compound = ModelType(Compound, contextual=True, required=True)
    parsers = [AutoTableParser()]

class TableDuctility(RatioModel):
    """ Model for Ductility table parsing"""
    specifier = StringType(parse_expression=ductility_specifier, required=True)
    raw_value = StringType(required=True, contextual=False)
    raw_units = StringType(required=True, contextual=False)
    compound = ModelType(Compound, contextual=True, required=True)
    parsers = [AutoTableParser()]

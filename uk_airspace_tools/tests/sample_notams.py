SAMPLE_Q_LINE = "EGTT/QWELW/IV/BO/W/000/020/5120N00030W005"

SAMPLE_NOTAM = """
A1234/24 NOTAMN
Q) EGTT/QWELW/IV/BO/W/000/020/5120N00030W005
A) EGTT
B) 2406011200
C) 2606011200 EST
D) DAILY 1200-1600
E) LASER DISPLAY WI 5NM RADIUS OF 5120N 00030W
F) SFC
G) 2000FT AMSL
"""

TEXT_ONLY_NOTAM = """
B2345/24 NOTAMN
Q) EGTT/QXXXX/IV/BO/W/000/020/
A) EGTT
B) 2406011200
C) PERM
E) ACTIVITY WITH NO RELIABLE POSITION
"""

MALFORMED_NOTAM = "This is malformed but should remain parseable as raw text."

STRUCTURED_PIB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Pib>
  <FIRSection>
    <ICAO>EGTT</ICAO>
    <Name>LONDON FIR</Name>
    <ADSection>
      <Code>EGNL</Code>
      <Name>WALNEY</Name>
      <NotamList>
        <Notam OriginalMessage="false" PIBSection="AD">
          <NOF>EGGN</NOF>
          <Series>L</Series>
          <Number>2624</Number>
          <Year>26</Year>
          <Type>N</Type>
          <QLine>
            <FIR>EGTT</FIR>
            <Code23>IL</Code23>
            <Code45>XX</Code45>
            <Traffic>I</Traffic>
            <Purpose>NBO</Purpose>
            <Scope>A</Scope>
            <Lower>0</Lower>
            <Upper>999</Upper>
          </QLine>
          <Coordinates>5408N00316W</Coordinates>
          <Radius>5</Radius>
          <ItemA>EGNL</ItemA>
          <StartValidity>2605010815</StartValidity>
          <EndValidity>2606302359</EndValidity>
          <ItemE>ILS LOCALISER AND DME RWY 35 IDENT CODES ARE NOT SYNCHRONISED ON TRANSMITTOR 1</ItemE>
        </Notam>
      </NotamList>
    </ADSection>
  </FIRSection>
</Pib>
"""
